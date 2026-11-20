#!/usr/bin/env python3
"""Run MindWave Project Map journeys against a declarative Map.

The runner refuses to execute anything that has not passed the shared
validator first (audit D2: "the validator gates execution" was only true
on the builder path). Validation reports all errors and never crashes.

Trace provenance (Phase 3, audit D7/D8): every trace names the tool version,
the exact content hashes of the Map and Journey documents it executed, a
runId, and a UTC timestamp — so two Map revisions with the same id can never
be confused in a Finding.

Phase 6: edge.requires is enforced against roleCapabilities (A12), a Map may
declare its own action vocabulary (invariant 5), and every run reports
coverage — what the Journeys did and did not test.
"""
from __future__ import annotations
import argparse, json, sys, uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fsutils import atomic_write_text, guard_output_against_inputs  # noqa: E402
from vocabulary import ACTION_TO_RELATION as DEFAULT_RELATION  # noqa: E402
from vocabulary import effective_vocabulary  # noqa: E402

TOOL_VERSION = "1.1.0"

# findings that flip a journey to FAIL; everything else (missing_edge,
# advisory structural notes) is recorded as evidence without failing the run
FATAL_FINDING_KINDS = {"journey_expectation_mismatch", "assert_unreachable_violated"}

def load(path):
    return json.loads(Path(path).read_text())

# module-level load is kept for backward compatibility; the CLI path uses
# validate_project_map.load which reports JSON syntax errors with line/column.

def index_map(data):
    nodes = {n["id"]: n for n in data["nodes"]}
    edges = {(e["from"], e["to"]): e for e in data["edges"]}
    perms = {(p["subject"], p["relation"], p["object"]) for p in data.get("permissions", [])}
    return nodes, edges, perms

def allowed(role, relation, node, perms):
    return (f"role:{role}", relation, f"node:{node}") in perms

def run_journey(journey, nodes, edges, perms, vocab=None, role_caps=None):
    vocab = vocab or DEFAULT_RELATION
    role_caps = role_caps or {}
    role = journey["initial"]["role"]
    current = journey["initial"]["node"]
    events, findings = [], []
    def event(step, outcome, detail, node=None, **extra):
        entry = {"step": step, "outcome": outcome, "detail": detail}
        if node is not None:
            entry["node"] = node  # exact reference for links.json (audit D5)
        entry.update(extra)
        events.append(entry)
    for i, step in enumerate(journey["steps"], 1):
        typ = step["type"]
        if typ == "move":
            target = step["to"]
            from_node = current
            perm_ok = allowed(role, "viewer", target, perms)
            edge = edges.get((current, target))
            edge_ok = edge is not None
            requires_ok = True
            missing_caps: list = []
            if edge_ok and edge.get("requires"):
                missing_caps = [c for c in edge["requires"] if c not in role_caps.get(role, [])]
                requires_ok = not missing_caps
            actual = "allowed" if perm_ok and edge_ok and requires_ok else "denied"
            expected = step.get("expect")
            passed = actual == expected
            event(i, "pass" if passed else "fail", f"move {from_node} -> {target}: {actual}",
                  node=target, fromNode=from_node)
            if passed:
                if actual == "allowed":
                    current = target
                elif not edge_ok and perm_ok:
                    # A17 repair: permission granted but no declared edge —
                    # the denial held for a structural reason the author
                    # should know about. This was dead code in the audit.
                    findings.append({"kind": "missing_edge", "step": i, "from": from_node, "to": target})
            else:
                if not edge_ok and not perm_ok:
                    reason = "no edge and no permission"
                elif not edge_ok:
                    reason = "no edge"
                elif not perm_ok:
                    reason = "no permission"
                else:
                    reason = f"missing capability: {', '.join(missing_caps)}"
                findings.append({"kind": "journey_expectation_mismatch", "step": i, "expected": expected, "actual": actual, "target": target, "reason": reason})
                if expected == "allowed" and perm_ok and not edge_ok:
                    # the mismatch is caused by a missing edge, not the permission
                    findings.append({"kind": "missing_edge", "step": i, "from": from_node, "to": target})
        elif typ == "act":
            target = step["target"]
            relation = vocab.get(step["action"], step["action"])
            actual = "allowed" if allowed(role, relation, target, perms) else "denied"
            expected = step.get("expect")
            passed = actual == expected
            event(i, "pass" if passed else "fail", f"act {step['action']} on {target}: {actual}", node=target)
            if not passed:
                findings.append({"kind": "journey_expectation_mismatch", "step": i, "expected": expected, "actual": actual, "target": target})
        elif typ == "checkpoint":
            event(i, "pass", f"checkpoint: {step['label']}", node=current)
        elif typ == "comment":
            event(i, "pass", f"comment: {step.get('label', '')}")
        else:
            event(i, "pass", f"unhandled declarative step: {typ}")
    return {"journeyId": journey["id"], "role": role, "start": journey["initial"]["node"], "end": current, "passed": not any(f["kind"] in FATAL_FINDING_KINDS for f in findings) and all(e["outcome"] == "pass" for e in events), "events": events, "findings": findings}

def compute_coverage(project_map: dict, results: list) -> dict:
    """What did the Journeys test — and what did they leave untouched (Phase 6.3)."""
    node_ids = [n["id"] for n in project_map["nodes"]]
    edges = [(e["from"], e["to"]) for e in project_map["edges"]]
    declared_perms = [
        (p["subject"], p["relation"], p["object"])
        for p in project_map.get("permissions", [])
    ]

    touched_nodes: set = set()
    used_edges: set = set()
    exercised_perms: set = set()
    for result in results:
        role = result["role"]
        for event in result["events"]:
            node = event.get("node")
            if node is not None:
                touched_nodes.add(node)
            if event["detail"].startswith("move ") and event["detail"].endswith(": allowed"):
                src = event.get("fromNode")
                if src is not None and node is not None:
                    used_edges.add((src, node))
                    exercised_perms.add((f"role:{role}", "viewer", f"node:{node}"))
            elif event["detail"].startswith("act ") and event["detail"].endswith(": allowed"):
                if node is not None:
                    action = event["detail"].split()[1]
                    relation = effective_vocabulary(project_map).get(action, action)
                    exercised_perms.add((f"role:{role}", relation, f"node:{node}"))

    perms_by_role: dict[str, set] = {}
    for subject, relation, obj in declared_perms:
        if subject.startswith("role:") and obj.startswith("node:") and relation == "viewer":
            perms_by_role.setdefault(subject[5:], set()).add(obj[5:])

    edge_sets = set(edges)
    role_coverage = {}
    for role in project_map["roles"]:
        viewable = perms_by_role.get(role, set())
        reachable: set = set()
        frontier = [n for n in viewable if n in set(node_ids)]
        reachable.update(frontier)
        while frontier:
            current = frontier.pop()
            for (frm, to) in edge_sets:
                if frm == current and to in viewable and to not in reachable:
                    reachable.add(to)
                    frontier.append(to)
        role_coverage[role] = {
            "viewableNodes": sorted(viewable & set(node_ids)),
            "reachableNodes": sorted(reachable),
            "unreachableByMovement": sorted(set(node_ids) - reachable),
        }

    return {
        "nodes": {
            "total": len(node_ids),
            "touched": sorted(touched_nodes & set(node_ids)),
            "untouched": sorted(set(node_ids) - touched_nodes),
        },
        "edges": {
            "total": len(edges),
            "used": sorted(used_edges & edge_sets),
            "unused": sorted(edge_sets - used_edges),
        },
        "permissions": {
            "declared": len(declared_perms),
            "exercised": sorted(f"{s}|{r}|{o}" for s, r, o in exercised_perms if (s, r, o) in set(declared_perms)),
            "unexercised": sorted(f"{s}|{r}|{o}" for s, r, o in set(declared_perms) - exercised_perms),
        },
        "roles": role_coverage,
    }

def build_trace(project_map: dict, journeys: list, results: list, map_path=None, journeys_path=None, coverage=None) -> dict:
    """Assemble the trace with its provenance header (Phase 3.1/3.2)."""
    trace = {
        "schemaVersion": project_map["schemaVersion"],
        "mapId": project_map["id"],
        "runId": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "toolVersion": TOOL_VERSION,
        "journeys": results,
    }
    if project_map.get("version") is not None:
        trace["mapVersion"] = str(project_map["version"])
    if map_path is not None:
        from findings import sha256_file
        trace["mapSha256"] = sha256_file(map_path)
    if journeys_path is not None:
        from findings import sha256_file
        trace["journeysSha256"] = sha256_file(journeys_path)
    if coverage is not None:
        trace["coverage"] = coverage
    return trace

def write_trace(trace: dict, path) -> None:
    atomic_write_text(path, json.dumps(trace, indent=2) + "\n")

def execute(project_map: dict, journeys: list):
    """Validate-free execution core shared by the runner and builder:
    index, run, compute coverage. Callers must validate first."""
    nodes, edges, perms = index_map(project_map)
    vocab = effective_vocabulary(project_map)
    role_caps = project_map.get("roleCapabilities") or {}
    results = [run_journey(j, nodes, edges, perms, vocab=vocab, role_caps=role_caps) for j in journeys]
    coverage = compute_coverage(project_map, results)
    return results, coverage

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--journeys", required=True)
    ap.add_argument("--trace", default="trace.json")
    args = ap.parse_args()
    # Invariant 1: a Trace must never overwrite a Map or Journey (audit A23).
    try:
        guard_output_against_inputs(args.trace, [args.map, args.journeys])
    except ValueError as e:
        print(str(e))
        return 2
    # Gate: nothing runs unless the shared validator passes (audit D1/D2).
    from validate_project_map import load, validate_all
    try:
        project_map = load(Path(args.map))
        journeys = load(Path(args.journeys))
        errors, warnings = validate_all(project_map, journeys, args.map, args.journeys)
    except (OSError, ValueError) as e:
        print(f"MAP INVALID\nERROR: {e}")
        return 2
    except Exception as e:  # never crash on malformed input
        print(f"MAP INVALID\nERROR: {type(e).__name__}: {e}")
        return 2
    if errors:
        print("MAP INVALID")
        for e in errors:
            print(f"ERROR: {e}")
        return 2
    for w in warnings:
        print(f"WARNING: {w}")
    results, coverage = execute(project_map, journeys)
    trace = build_trace(project_map, journeys, results, map_path=args.map, journeys_path=args.journeys, coverage=coverage)
    write_trace(trace, args.trace)
    for result in results:
        print(f"{'PASS' if result['passed'] else 'FAIL'} {result['journeyId']} ({len(result['events'])} events)")
        for finding in result["findings"]: print(f"  FINDING {finding}")
    untouched = coverage["nodes"]["untouched"]
    if untouched:
        print(f"COVERAGE untouched nodes: {', '.join(untouched)}")
    print(f"TRACE {args.trace}")
    return 0 if all(r["passed"] for r in results) else 1

if __name__ == "__main__": sys.exit(main())
