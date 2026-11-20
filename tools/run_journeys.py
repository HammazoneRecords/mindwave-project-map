#!/usr/bin/env python3
"""Run MindWave Project Map journeys against a declarative Map.

The runner refuses to execute anything that has not passed the shared
validator first (audit D2: "the validator gates execution" was only true
on the builder path). Validation reports all errors and never crashes.

Trace provenance (Phase 3, audit D7/D8): every trace names the tool version,
the exact content hashes of the Map and Journey documents it executed, a
runId, and a UTC timestamp — so two Map revisions with the same id can never
be confused in a Finding.
"""
from __future__ import annotations
import argparse, json, sys, uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fsutils import atomic_write_text, guard_output_against_inputs  # noqa: E402
from vocabulary import ACTION_TO_RELATION as RELATION  # noqa: E402

TOOL_VERSION = "1.0.0"

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

def run_journey(journey, nodes, edges, perms):
    role = journey["initial"]["role"]
    current = journey["initial"]["node"]
    events, findings = [], []
    def event(step, outcome, detail, node=None):
        entry = {"step": step, "outcome": outcome, "detail": detail}
        if node is not None:
            entry["node"] = node  # exact reference for links.json (audit D5)
        events.append(entry)
    for i, step in enumerate(journey["steps"], 1):
        typ = step["type"]
        if typ == "move":
            target = step["to"]
            perm_ok = allowed(role, "viewer", target, perms)
            edge_ok = (current, target) in edges
            actual = "allowed" if perm_ok and edge_ok else "denied"
            expected = step.get("expect")
            passed = actual == expected
            event(i, "pass" if passed else "fail", f"move {current} -> {target}: {actual}", node=target)
            if passed:
                if actual == "allowed":
                    current = target
                elif not edge_ok and perm_ok:
                    # A17 repair: permission granted but no declared edge —
                    # the denial held for a structural reason the author
                    # should know about. This was dead code in the audit.
                    findings.append({"kind": "missing_edge", "step": i, "from": current, "to": target})
            else:
                findings.append({"kind": "journey_expectation_mismatch", "step": i, "expected": expected, "actual": actual, "target": target})
                if expected == "allowed" and perm_ok and not edge_ok:
                    # the mismatch is caused by a missing edge, not the permission
                    findings.append({"kind": "missing_edge", "step": i, "from": current, "to": target})
        elif typ == "act":
            target = step["target"]
            relation = RELATION.get(step["action"], step["action"])
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
    return {"journeyId": journey["id"], "role": role, "start": journey["initial"]["node"], "end": current, "passed": not findings and all(e["outcome"] == "pass" for e in events), "events": events, "findings": findings}

def build_trace(project_map: dict, journeys: list, results: list, map_path=None, journeys_path=None) -> dict:
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
    return trace

def write_trace(trace: dict, path) -> None:
    atomic_write_text(path, json.dumps(trace, indent=2) + "\n")

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
    nodes, edges, perms = index_map(project_map)
    results = [run_journey(j, nodes, edges, perms) for j in journeys]
    trace = build_trace(project_map, journeys, results, map_path=args.map, journeys_path=args.journeys)
    write_trace(trace, args.trace)
    for result in results:
        print(f"{'PASS' if result['passed'] else 'FAIL'} {result['journeyId']} ({len(result['events'])} events)")
        for finding in result["findings"]: print(f"  FINDING {finding}")
    print(f"TRACE {args.trace}")
    return 0 if all(r["passed"] for r in results) else 1

if __name__ == "__main__": sys.exit(main())
