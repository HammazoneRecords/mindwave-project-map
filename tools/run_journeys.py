#!/usr/bin/env python3
"""Run MindWave Project Map journeys against a declarative Map.

The runner refuses to execute anything that has not passed the shared
validator first (audit D2). Validation reports all errors and never crashes.

Trace provenance (Phase 3, audit D7/D8): runId, UTC timestamp, toolVersion,
and the SHA-256 of the exact Map and Journey documents executed.

Phase 6: edge.requires enforced against roleCapabilities (A12), map-level
vocabulary (invariant 5), coverage metrics.

Phase 7 depth features:
- 7.1 assert_unreachable steps — Journeys become proofs of absence
- 7.2 adapter contract — observations compared to the Map, both in the Trace
- 7.3 data-driven matrix journeys — expansion output is a Journey, never a Map edit
- 7.5 conditional edges (`when.state`) — state mutations live in the Trace
"""
from __future__ import annotations
import argparse, json, sys, uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fsutils import atomic_write_text, guard_output_against_inputs  # noqa: E402
from vocabulary import ACTION_TO_RELATION as DEFAULT_RELATION  # noqa: E402
from vocabulary import effective_vocabulary  # noqa: E402

TOOL_VERSION = "1.2.0"

# findings that flip a journey to FAIL; everything else (missing_edge,
# advisory structural notes) is recorded as evidence without failing the run
FATAL_FINDING_KINDS = {"journey_expectation_mismatch", "assert_unreachable_violated"}

def load(path):
    return json.loads(Path(path).read_text())

def index_map(data):
    nodes = {n["id"]: n for n in data["nodes"]}
    edges = {(e["from"], e["to"]): e for e in data["edges"]}
    perms = {(p["subject"], p["relation"], p["object"]) for p in data.get("permissions", [])}
    return nodes, edges, perms

def allowed(role, relation, node, perms):
    return (f"role:{role}", relation, f"node:{node}") in perms

def expand_journeys(journeys: list, project_map: dict) -> tuple[list, dict]:
    """Phase 7.3: expand matrix journeys into concrete probe journeys.

    Each (role, target) pair of a matrix journey becomes one concrete
    Journey with a single permission-probe act step. The expansion output is
    a list of Journey objects — the Map is never touched. Returns
    (concrete_journeys, expanded_from) where expanded_from maps each
    concrete id back to its base journey id.
    """
    vocab = effective_vocabulary(project_map)
    concrete: list = []
    expanded_from: dict = {}
    for journey in journeys:
        matrix = journey.get("matrix")
        if not matrix:
            concrete.append(journey)
            continue
        roles = matrix.get("roles", [])
        targets = matrix.get("targets", [])
        action = matrix.get("action", "view")
        for role in roles:
            for target in targets:
                cid = f"{journey['id']}__{role}__{target}"
                concrete.append({
                    "schemaVersion": journey.get("schemaVersion", "1.0.0"),
                    "id": cid,
                    "title": f"{journey.get('title', journey['id'])} [{role} x {target}]",
                    "map": journey["map"],
                    "initial": {"role": role, "node": journey["initial"]["node"]},
                    "steps": [{"type": "act", "action": action, "target": target}],
                })
                expanded_from[cid] = journey["id"]
    return concrete, expanded_from

def _traversable(edge, role, state, role_caps, perms):
    """All conditions for walking one edge as this role, right now."""
    target = edge["to"]
    if not allowed(role, "viewer", target, perms):
        return False, "no permission"
    missing_caps = [c for c in edge.get("requires", []) if c not in role_caps.get(role, [])]
    if missing_caps:
        return False, f"missing capability: {', '.join(missing_caps)}"
    guard = (edge.get("when") or {}).get("state")
    if guard and state.get(guard) is not True:
        return False, f"state guard '{guard}' not satisfied"
    return True, ""

def _reachable_from(start, role, nodes, edges, state, role_caps, perms, limit=None):
    """BFS over traversable edges; returns the set of reachable node ids."""
    seen = {start}
    frontier = [start]
    while frontier:
        current = frontier.pop()
        for (frm, to), edge in edges.items():
            if frm != current or to in seen:
                continue
            ok, _ = _traversable(edge, role, state, role_caps, perms)
            if ok:
                seen.add(to)
                frontier.append(to)
                if limit is not None and to == limit:
                    return seen
    return seen

def run_journey(journey, nodes, edges, perms, vocab=None, role_caps=None, adapter=None):
    vocab = vocab or DEFAULT_RELATION
    role_caps = role_caps or {}
    role = journey["initial"]["role"]
    current = journey["initial"]["node"]
    state: dict = {}  # Phase 7.5: mutations live here (and in the Trace), never the Map
    events, findings = [], []
    def event(step, outcome, detail, node=None, **extra):
        entry = {"step": step, "outcome": outcome, "detail": detail}
        if node is not None:
            entry["node"] = node
        entry.update(extra)
        events.append(entry)
    for i, step in enumerate(journey["steps"], 1):
        typ = step["type"]
        if step.get("set"):
            state.update(step["set"])  # invariant 2/7.5: recorded in the event below
        if typ == "move":
            target = step["to"]
            from_node = current
            perm_ok = allowed(role, "viewer", target, perms)
            edge = edges.get((current, target))
            edge_ok = edge is not None
            if edge_ok:
                # permission + capability requires + conditional state guard
                state_ok, state_reason = _traversable(edge, role, state, role_caps, perms)
            else:
                state_ok, state_reason = True, ""
            actual = "allowed" if perm_ok and edge_ok and state_ok else "denied"
            expected = step.get("expect")
            # no expectation declared = observational step: record the outcome, never assert
            passed = expected is None or actual == expected
            observation = None
            if adapter is not None:
                observation = adapter.probe(role, target)
                if observation["reachable"] != perm_ok:
                    findings.append({
                        "kind": "adapter_disagreement", "step": i, "stepType": "move",
                        "mapDecision": "allowed" if perm_ok else "denied",
                        "adapter": observation,
                    })
            event(i, "pass" if passed else "fail", f"move {from_node} -> {target}: {actual}",
                  node=target, fromNode=from_node, adapter=observation)
            if actual == "allowed" and edge_ok and state_ok:
                current = target  # observational or asserted, the move still happened
            if expected is None:
                continue
            if passed:
                if not edge_ok and perm_ok:
                    findings.append({"kind": "missing_edge", "step": i, "from": from_node, "to": target})
            else:
                if not edge_ok and not perm_ok:
                    reason = "no edge and no permission"
                elif not edge_ok:
                    reason = "no edge"
                elif not perm_ok:
                    reason = "no permission"
                elif not state_ok:
                    reason = state_reason or "edge condition not met"
                else:
                    reason = "edge condition not met"
                findings.append({"kind": "journey_expectation_mismatch", "step": i, "expected": expected, "actual": actual, "target": target, "reason": reason})
                if expected == "allowed" and perm_ok and not edge_ok:
                    findings.append({"kind": "missing_edge", "step": i, "from": from_node, "to": target})
        elif typ == "act":
            target = step["target"]
            relation = vocab.get(step["action"], step["action"])
            actual = "allowed" if allowed(role, relation, target, perms) else "denied"
            expected = step.get("expect")
            passed = expected is None or actual == expected  # observational when no expectation
            observation = None
            if adapter is not None:
                observation = adapter.act(role, step["action"], target)
                if observation["allowed"] != (actual == "allowed"):
                    findings.append({
                        "kind": "adapter_disagreement", "step": i, "stepType": "act",
                        "mapDecision": actual, "adapter": observation,
                    })
            event(i, "pass" if passed else "fail", f"act {step['action']} on {target}: {actual}", node=target, adapter=observation)
            if not passed:
                findings.append({"kind": "journey_expectation_mismatch", "step": i, "expected": expected, "actual": actual, "target": target})
        elif typ == "assert_unreachable":
            # Phase 7.1: a proof of absence. The target must NOT be reachable
            # from the current position as this role via traversable edges.
            target = step["target"]
            if target == current:
                # re-audit L2: a self-referential claim proves nothing — record
                # it honestly instead of fabricating "confirmed unreachable"
                event(i, "pass", f"assert_unreachable {target}: vacuous claim (the journey stands on the target)", node=target)
                findings.append({"kind": "assert_unreachable_vacuous", "step": i, "target": target})
            else:
                reachable = _reachable_from(current, role, nodes, edges, state, role_caps, perms)
                violated = target in reachable
                event(i, "fail" if violated else "pass",
                      f"assert_unreachable {target}: {'REACHABLE (violated)' if violated else 'confirmed unreachable'}"
                      + f" [explored {len(reachable)} nodes]",
                      node=target)
                if violated:
                    findings.append({"kind": "assert_unreachable_violated", "step": i, "from": current, "target": target})
        elif typ == "checkpoint":
            event(i, "pass", f"checkpoint: {step['label']}", node=current)
        elif typ == "comment":
            event(i, "pass", f"comment: {step.get('label', '')}")
        else:
            event(i, "pass", f"unhandled declarative step: {typ}")
        if step.get("set"):
            events[-1]["setState"] = dict(step["set"])
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
    role_caps = project_map.get("roleCapabilities") or {}
    role_coverage = {}
    for role in project_map["roles"]:
        viewable = perms_by_role.get(role, set())
        reachable: set = set()
        frontier = [n for n in viewable if n in set(node_ids)]
        reachable.update(frontier)
        while frontier:
            current = frontier.pop()
            for edge in project_map["edges"]:
                if edge["from"] != current or edge["to"] in reachable:
                    continue
                # static reachability mirrors the runner: permission + requires,
                # conditional (when.state) edges count as closed until a journey sets the state
                if edge["to"] not in viewable:
                    continue
                if any(c not in role_caps.get(role, []) for c in edge.get("requires", [])):
                    continue
                if (edge.get("when") or {}).get("state"):
                    continue
                reachable.add(edge["to"])
                frontier.append(edge["to"])
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

def build_trace(project_map: dict, journeys: list, results: list, map_path=None, journeys_path=None, coverage=None, expanded_from=None) -> dict:
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
    if expanded_from:
        trace["expandedJourneys"] = expanded_from
    return trace

def write_trace(trace: dict, path) -> None:
    atomic_write_text(path, json.dumps(trace, indent=2) + "\n")

def execute(project_map: dict, journeys: list, adapter_name: str = "declarative"):
    """Validation-free execution core shared by the runner and builder:
    expand matrix journeys, run, compute coverage. Callers must validate the
    RAW journeys first; matrix fields are validated there."""
    adapter = None
    if adapter_name == "declarative":
        from adapters import DeclarativeMapAdapter
        adapter = DeclarativeMapAdapter(project_map)
    concrete, expanded_from = expand_journeys(journeys, project_map)
    nodes, edges, perms = index_map(project_map)
    vocab = effective_vocabulary(project_map)
    role_caps = project_map.get("roleCapabilities") or {}
    results = [run_journey(j, nodes, edges, perms, vocab=vocab, role_caps=role_caps, adapter=adapter) for j in concrete]
    coverage = compute_coverage(project_map, results)
    return results, coverage, expanded_from

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--journeys", required=True)
    ap.add_argument("--trace", default="trace.json")
    ap.add_argument("--adapter", choices=("declarative", "none"), default="declarative",
                    help="adapter consulted for every move/act; observations land in the Trace (Phase 7.2)")
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
    results, coverage, expanded_from = execute(project_map, journeys, adapter_name=args.adapter)
    trace = build_trace(project_map, journeys, results, map_path=args.map, journeys_path=args.journeys,
                        coverage=coverage, expanded_from=expanded_from or None)
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
