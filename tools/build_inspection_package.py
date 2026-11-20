#!/usr/bin/env python3
"""Build a portable inspection package from a Map and its Journeys."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reuse the existing validators, runner, and flow exports.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_map_flow import MERMAID, PSEUDOCODE  # noqa: E402
from fsutils import atomic_write_text, guard_output_against_inputs  # noqa: E402
from findings import finding_from_raw  # noqa: E402
from run_journeys import build_trace, index_map, run_journey, write_trace  # noqa: E402
from validate_project_map import load, validate_all  # noqa: E402


def write_json(path: Path, value: object) -> None:
    atomic_write_text(path, json.dumps(value, indent=2) + "\n")


def findings_from_trace(trace: dict) -> list[dict]:
    """Findings with the rule-based taxonomy (Phase 3): category, severity,
    and confidence are derived per finding kind — the audit's hardcoded
    \"medium\" is gone (D8) — and every Finding pins the Map content that
    produced it (D7)."""
    findings = []
    for result in trace["journeys"]:
        for finding in result["findings"]:
            findings.append(finding_from_raw(finding, result["journeyId"], trace))
    return findings


def build_links(project_map: dict, journeys: list[dict], trace: dict) -> dict:
    links = []
    for node in project_map["nodes"]:
        node_id = node["id"]
        journey_steps = []
        trace_events = []
        for journey in journeys:
            for index, step in enumerate(journey["steps"], 1):
                target = step.get("to") or step.get("target") or journey["initial"]["node"]
                if target == node_id:
                    journey_steps.append({"journeyId": journey["id"], "step": index})
            result = next((r for r in trace["journeys"] if r["journeyId"] == journey["id"]), None)
            if result:
                for index, event in enumerate(result["events"], 1):
                    if node_id in event.get("detail", ""):
                        trace_events.append({"journeyId": journey["id"], "event": index})
        links.append({"mapNodeId": node_id, "journeySteps": journey_steps, "traceEvents": trace_events})
    return {"schemaVersion": project_map["schemaVersion"], "mapId": project_map["id"], "links": links}


def source_reference(project_map: dict, map_path: Path, journeys_path: Path) -> str:
    source = project_map.get("source", {})
    lines = ["# Source Reference", "", f"- Map: `{map_path}`", f"- Journeys: `{journeys_path}`"]
    if source:
        lines += [f"- Repository: `{source.get('repository', 'not specified')}`", f"- Branch: `{source.get('branch', 'not specified')}`", f"- Capture purpose: `{source.get('purpose', 'not specified')}`"]
    lines += ["", "This package is a generated inspection snapshot. It is not a live connection to the target project.", ""]
    return "\n".join(lines)


def build_package(map_path: Path, journeys_path: Path, output: Path, variables_path: Path | None = None) -> tuple[dict, list[dict], list[str]]:
    # Invariant 1: the package must never overwrite its own inputs (audit A23).
    inputs = [map_path, journeys_path] + ([variables_path] if variables_path else [])
    guard_output_against_inputs(output, inputs)
    project_map = load(map_path)
    journeys = load(journeys_path)
    errors, warnings = validate_all(project_map, journeys, str(map_path), str(journeys_path))
    if errors:
        raise ValueError("\n".join(f"ERROR: {e}" for e in errors))

    nodes, edges, permissions = index_map(project_map)
    results = [run_journey(journey, nodes, edges, permissions) for journey in journeys]
    trace = build_trace(project_map, journeys, results, map_path=map_path, journeys_path=journeys_path)
    findings = findings_from_trace(trace)

    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "map.json", project_map)
    write_json(output / "journeys.json", journeys)
    write_trace(trace, output / "trace.json")
    write_json(output / "findings.json", findings)
    write_json(output / "links.json", build_links(project_map, journeys, trace))
    atomic_write_text(output / "source-reference.md", source_reference(project_map, map_path, journeys_path))
    if variables_path is not None:
        variables = load(variables_path)
        if variables.get("mapId") != project_map["id"]:
            raise ValueError(f"{variables_path}: mapId does not match {project_map['id']}")
        write_json(output / "variables.json", variables)
    atomic_write_text(output / "flowchart.mmd", MERMAID.rstrip() + "\n")
    atomic_write_text(output / "pseudocode.txt", PSEUDOCODE.rstrip() + "\n")
    return trace, findings, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--journeys", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="inspection package directory")
    parser.add_argument("--variables", type=Path, help="optional Variable Matrix JSON")
    args = parser.parse_args()
    try:
        trace, findings, warnings = build_package(args.map, args.journeys, args.output, args.variables)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 2
    for w in warnings:
        print(f"WARNING: {w}")

    passed = sum(result["passed"] for result in trace["journeys"])
    total = len(trace["journeys"])
    print(f"PACKAGE {args.output}")
    print(f"JOURNEYS {passed}/{total} passed")
    print(f"FINDINGS {len(findings)}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
