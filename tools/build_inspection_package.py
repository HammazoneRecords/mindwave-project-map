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
from run_journeys import index_map, run_journey  # noqa: E402
from validate_project_map import load, validate_journeys, validate_map  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def findings_from_trace(trace: dict) -> list[dict]:
    findings = []
    for result in trace["journeys"]:
        for finding in result["findings"]:
            details = ", ".join(
                f"{key}={value}" for key, value in finding.items() if key not in {"kind", "step"}
            )
            findings.append(
                {
                    "kind": finding["kind"],
                    "severity": "medium",
                    "status": "open",
                    "message": details or finding["kind"],
                    "source": {
                        "mapId": trace["mapId"],
                        "journeyId": result["journeyId"],
                        "step": finding["step"],
                    },
                }
            )
    return findings


def build_package(map_path: Path, journeys_path: Path, output: Path) -> tuple[dict, list[dict]]:
    project_map = load(map_path)
    journeys = load(journeys_path)
    validate_map(project_map, str(map_path))
    validate_journeys(journeys, project_map, str(journeys_path))

    nodes, edges, permissions = index_map(project_map)
    results = [run_journey(journey, nodes, edges, permissions) for journey in journeys]
    trace = {
        "schemaVersion": project_map["schemaVersion"],
        "mapId": project_map["id"],
        "journeys": results,
    }
    findings = findings_from_trace(trace)

    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "map.json", project_map)
    write_json(output / "journeys.json", journeys)
    write_json(output / "trace.json", trace)
    write_json(output / "findings.json", findings)
    (output / "flowchart.mmd").write_text(MERMAID.rstrip() + "\n", encoding="utf-8")
    (output / "pseudocode.txt").write_text(PSEUDOCODE.rstrip() + "\n", encoding="utf-8")
    return trace, findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--journeys", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="inspection package directory")
    args = parser.parse_args()
    try:
        trace, findings = build_package(args.map, args.journeys, args.output)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 2

    passed = sum(result["passed"] for result in trace["journeys"])
    total = len(trace["journeys"])
    print(f"PACKAGE {args.output}")
    print(f"JOURNEYS {passed}/{total} passed")
    print(f"FINDINGS {len(findings)}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
