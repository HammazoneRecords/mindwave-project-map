#!/usr/bin/env python3
"""Generate the inspection package's flowchart and pseudocode FROM the Map.

Audit D6: `flowchart.mmd` and `pseudocode.txt` used to be static constants
describing the Project Map pipeline itself, not the supplied Map. The
package must describe the document the author actually gave us.

`project_map_flow.py` keeps exporting the pipeline description (clearly
labeled as such); this module derives the same two artifacts from a Map.
"""
from __future__ import annotations

import json


def _node_label(node: dict) -> str:
    title = node.get("title") or node["id"]
    return f"{title} [{node['type']}]" if node.get("type") else title


def mermaid_from_map(project_map: dict) -> str:
    """Mermaid flowchart of the Map's own nodes and edges."""
    lines = [f"flowchart TD", f"  %% generated from map '{project_map['id']}' — derived content, not the tool pipeline"]
    for node in project_map["nodes"]:
        lines.append(f"  {node['id']}[\"{_node_label(node)}\"]")
    for edge in project_map["edges"]:
        label = f"|{edge['type']}|" if edge.get("type") else ""
        lines.append(f"  {edge['from']} -->{label} {edge['to']}")
    return "\n".join(lines) + "\n"


def pseudocode_from_map(project_map: dict) -> str:
    """Executable-shape pseudocode of what the runner will do with this Map."""
    perms_by_role: dict[str, list[str]] = {}
    for p in project_map.get("permissions", []):
        role = p["subject"].removeprefix("role:")
        perms_by_role.setdefault(role, []).append(
            f"{p['relation']}({p['object'].removeprefix('node:')})"
        )
    out = [
        f"# generated from map '{project_map['id']}'"
        + (f" version '{project_map['version']}'" if project_map.get("version") else "")
        + " — derived content, not the tool pipeline",
        "",
        "roles: " + ", ".join(project_map["roles"]),
    ]
    if project_map.get("capabilities"):
        out.append("capabilities: " + ", ".join(project_map["capabilities"]))
    out.append("")
    out.append("declared edges:")
    for e in project_map["edges"]:
        req = f"  requires {e['requires']}" if e.get("requires") else ""
        out.append(f"  {e['from']} -> {e['to']} [{e.get('type', 'edge')}]{req}")
    out.append("")
    out.append("declared permissions per role:")
    for role in project_map["roles"]:
        grants = perms_by_role.get(role, [])
        out.append(f"  {role}: {', '.join(grants) if grants else '(none)'}")
    out.append("")
    out.append("function run(map, journey):")
    out.append("    position = journey.initial.node")
    out.append("    for step in journey.steps:")
    out.append("        move:   allowed = edge(position, step.to) AND viewer(step.to, role)")
    out.append("                deny reason: missing permission, or missing edge")
    out.append("        act:    allowed = permission(role, relation(step.action), step.target)")
    out.append("        checkpoint: record position; no state change")
    out.append("        position advances only on an allowed move")
    out.append("    every expectation mismatch becomes a Finding")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", required=True)
    ap.add_argument("--format", choices=("mermaid", "pseudocode"), default="mermaid")
    args = ap.parse_args()
    data = json.loads(__import__("pathlib").Path(args.map).read_text())
    print(mermaid_from_map(data) if args.format == "mermaid" else pseudocode_from_map(data))
