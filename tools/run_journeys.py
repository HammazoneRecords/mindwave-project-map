#!/usr/bin/env python3
"""Run MindWave Project Map journeys against a declarative Map."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

RELATION = {"view":"viewer", "read":"viewer", "create":"creator", "ingest":"creator", "handoff":"creator", "edit":"editor", "delete":"deleter"}

def load(path):
    return json.loads(Path(path).read_text())

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
    def event(step, outcome, detail):
        events.append({"step": step, "outcome": outcome, "detail": detail})
    for i, step in enumerate(journey["steps"], 1):
        typ = step["type"]
        if typ == "move":
            target = step["to"]
            relation_ok = allowed(role, "viewer", target, perms)
            edge_ok = (current, target) in edges
            actual = "allowed" if relation_ok and edge_ok else "denied"
            expected = step.get("expect")
            passed = actual == expected
            event(i, "pass" if passed else "fail", f"move {current} -> {target}: {actual}")
            if passed and actual == "allowed": current = target
            if not passed:
                findings.append({"kind":"journey_expectation_mismatch","step":i,"expected":expected,"actual":actual,"target":target})
            elif expected == "allowed" and not edge_ok:
                findings.append({"kind":"missing_edge","step":i,"from":current,"to":target})
        elif typ == "act":
            target = step["target"]
            relation = RELATION.get(step["action"], step["action"])
            actual = "allowed" if allowed(role, relation, target, perms) else "denied"
            expected = step.get("expect")
            passed = actual == expected
            event(i, "pass" if passed else "fail", f"act {step['action']} on {target}: {actual}")
            if not passed:
                findings.append({"kind":"journey_expectation_mismatch","step":i,"expected":expected,"actual":actual,"target":target})
        elif typ == "checkpoint":
            event(i, "pass", f"checkpoint: {step['label']}")
        else:
            event(i, "pass", f"unhandled declarative step: {typ}")
    return {"journeyId": journey["id"], "role": role, "start": journey["initial"]["node"], "end": current, "passed": not findings and all(e["outcome"] == "pass" for e in events), "events": events, "findings": findings}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--journeys", required=True)
    ap.add_argument("--trace", default="trace.json")
    args = ap.parse_args()
    project_map = load(args.map); journeys = load(args.journeys)
    nodes, edges, perms = index_map(project_map)
    errors = []
    for edge in project_map["edges"]:
        if edge["from"] not in nodes or edge["to"] not in nodes: errors.append(f"edge references missing node: {edge}")
    for journey in journeys:
        if journey["map"] != project_map["id"]: errors.append(f"{journey['id']}: map id mismatch")
        if journey["initial"]["node"] not in nodes: errors.append(f"{journey['id']}: missing initial node")
    if errors:
        print("MAP INVALID")
        print("\n".join(errors))
        return 2
    results = [run_journey(j, nodes, edges, perms) for j in journeys]
    trace = {"schemaVersion": project_map["schemaVersion"], "mapId": project_map["id"], "journeys": results}
    Path(args.trace).write_text(json.dumps(trace, indent=2) + "\n")
    for result in results:
        print(f"{'PASS' if result['passed'] else 'FAIL'} {result['journeyId']} ({len(result['events'])} events)")
        for finding in result["findings"]: print(f"  FINDING {finding}")
    print(f"TRACE {args.trace}")
    return 0 if all(r["passed"] for r in results) else 1

if __name__ == "__main__": sys.exit(main())
