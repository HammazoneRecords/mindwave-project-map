#!/usr/bin/env python3
"""Build a portable inspection package from a Map and its Journeys.

Phase 4 (audit D5/D6/D9): every exported file now tells the truth.

- links.json is computed from exact step targets and the trace events'
  structured node references — no substring matching, no default-to-start
  node, and duplicate journey ids are already rejected upstream (Phase 1).
- flowchart.mmd and pseudocode.txt are derived from the supplied Map
  (tools/map_derived.py); the pipeline description stays in
  project_map_flow.py, clearly labeled.
- the Variable Matrix (when supplied) is verified reference by reference
  (tools/verify_variables.py); stale or dangling references become findings
  instead of riding along silently.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reuse the existing validators, runner, and derived exporters.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fsutils import atomic_write_text, guard_output_against_inputs  # noqa: E402
from map_derived import mermaid_from_map, pseudocode_from_map  # noqa: E402
from verify_variables import verify_variables  # noqa: E402
from run_journeys import build_trace, execute, write_trace  # noqa: E402
from validate_project_map import load, validate_all  # noqa: E402


def write_json(path: Path, value: object) -> None:
    atomic_write_text(path, json.dumps(value, indent=2) + "\n")


def findings_from_trace(trace: dict) -> list[dict]:
    """Findings with the rule-based taxonomy (Phase 3): category, severity,
    and confidence are derived per finding kind — the audit's hardcoded
    "medium" is gone (D8) — and every Finding pins the Map content that
    produced it (D7)."""
    findings = []
    for result in trace["journeys"]:
        for finding in result["findings"]:
            from findings import finding_from_raw
            findings.append(finding_from_raw(finding, result["journeyId"], trace))
    return findings


def findings_from_variables(variables_findings: list[dict], trace: dict) -> list[dict]:
    """Variable-matrix findings, one source block per stale reference."""
    from findings import finding_from_raw
    out = []
    for raw in variables_findings:
        # journeyId 'variable-matrix' marks these as document-level drift;
        # step is the variable's index in the matrix
        out.append(finding_from_raw(raw, "variable-matrix", trace))
    return out


def build_links(project_map: dict, journeys: list[dict], trace: dict) -> dict:
    """Exact node -> journey-step -> trace-event links (audit D5, Phase 4.1).

    A journey step references a node when its own `to`/`target` names that
    node, OR when the trace resolved that step to the node (checkpoints run
    at the current position — event index == step index, so the trace gives
    the exact step->node mapping). Trace events reference a node only through
    the runner's structured `event.node` field — never by substring matching.
    """
    # step index (1-based) -> node, per journey, as resolved by the runner
    resolved_step_nodes: dict[str, dict[int, str]] = {}
    for result in trace["journeys"]:
        mapping = {}
        for index, event in enumerate(result["events"], 1):
            if event.get("node") is not None:
                mapping[index] = event["node"]
        resolved_step_nodes[result["journeyId"]] = mapping

    links = []
    for node in project_map["nodes"]:
        node_id = node["id"]
        journey_steps = []
        trace_events = []
        for journey in journeys:
            for index, step in enumerate(journey["steps"], 1):
                target = step.get("to") or step.get("target")
                if target == node_id or resolved_step_nodes.get(journey["id"], {}).get(index) == node_id:
                    journey_steps.append({"journeyId": journey["id"], "step": index})
        for result in trace["journeys"]:
            for index, event in enumerate(result["events"], 1):
                if event.get("node") == node_id:
                    trace_events.append({"journeyId": result["journeyId"], "event": index})
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

    results, coverage = execute(project_map, journeys)
    trace = build_trace(project_map, journeys, results, map_path=map_path, journeys_path=journeys_path, coverage=coverage)
    findings = findings_from_trace(trace)

    variables_findings: list[dict] = []
    if variables_path is not None:
        variables = load(variables_path)
        if variables.get("mapId") != project_map["id"]:
            raise ValueError(f"{variables_path}: mapId does not match {project_map['id']}")
        variables_findings = verify_variables(variables, project_map, journeys)
        findings.extend(findings_from_variables(variables_findings, trace))

    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "map.json", project_map)
    write_json(output / "journeys.json", journeys)
    write_trace(trace, output / "trace.json")
    write_json(output / "findings.json", findings)
    write_json(output / "coverage.json", trace.get("coverage"))
    write_json(output / "links.json", build_links(project_map, journeys, trace))
    atomic_write_text(output / "source-reference.md", source_reference(project_map, map_path, journeys_path))
    if variables_path is not None:
        write_json(output / "variables.json", variables)
    # D6: derived from the supplied Map — not the tool pipeline
    atomic_write_text(output / "flowchart.mmd", mermaid_from_map(project_map))
    atomic_write_text(output / "pseudocode.txt", pseudocode_from_map(project_map))
    return trace, findings, warnings + [f"VARIABLE DRIFT: {f['kind']} in {f.get('variable', '?')} ({f.get('reference', f.get('node', ''))})" for f in variables_findings]


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
