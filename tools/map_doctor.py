#!/usr/bin/env python3
"""map_doctor.py — health checks for an authored Map (and its companions).

Audit plan 5.4. The doctor inspects documents that are already valid (run
the validator first) and reports structural smells:

errors (exit 1):
  - duplicate edges on the same node pair (A13)
  - duplicate node ids
  - dangling variable references (--variables)
errors that duplicate the validator are skipped when --no-validate is given;
by default the doctor runs the shared validator first and refuses to doctor
an invalid document.

warnings (exit 0, listed):
  - orphan nodes: no incoming or outgoing edges (A14-adjacent)
  - unreachable-per-role: nodes no role can ever reach via traversable edges
  - unused capabilities: declared but no permission uses their relations (A01)
  - edges nobody can traverse: no role has viewer permission on the target
  - empty journeys array (--journeys) (A14)
  - no entry nodes declared (Phase 6 will enforce entry semantics)

Exit codes: 0 healthy (warnings allowed unless --strict), 1 errors, 2 invalid input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vocabulary import effective_vocabulary  # noqa: E402


def _load(path):
    return json.loads(Path(path).read_text())


def doctor(project_map: dict, journeys: list | None = None, variables: dict | None = None) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for an already-schema-valid Map."""
    errors: list[str] = []
    warnings: list[str] = []

    node_ids = [n["id"] for n in project_map["nodes"]]
    if len(node_ids) != len(set(node_ids)):
        seen: set = set()
        for nid in node_ids:
            if nid in seen:
                errors.append(f"duplicate node id '{nid}'")
            seen.add(nid)
    node_set = set(node_ids)

    roles = list(project_map["roles"])
    role_caps = project_map.get("roleCapabilities") or {}
    vocab = effective_vocabulary(project_map)

    def traversable_static(edge, role):
        """Mirror the runner's _traversable for static analysis: permission +
        requires + not when-guarded (guard state is journey-local, so a
        conditional edge is statically closed — reported separately)."""
        target = edge["to"]
        if (f"role:{role}", "viewer", f"node:{target}") not in {
            (p["subject"], p["relation"], p["object"]) for p in perms
        }:
            return False
        if any(c not in role_caps.get(role, []) for c in edge.get("requires", [])):
            return False
        if (edge.get("when") or {}).get("state"):
            return False
        return True
    edge_pairs: dict[tuple, int] = {}
    has_edge = {nid: False for nid in node_ids}
    for edge in project_map["edges"]:
        pair = (edge["from"], edge["to"])
        edge_pairs[pair] = edge_pairs.get(pair, 0) + 1
        has_edge[edge["from"]] = True
        has_edge[edge["to"]] = True
        if edge["from"] not in node_set:
            errors.append(f"edge references unknown node '{edge['from']}'")
        if edge["to"] not in node_set:
            errors.append(f"edge references unknown node '{edge['to']}'")
    for (frm, to), count in edge_pairs.items():
        if count > 1:
            errors.append(f"duplicate edge {frm} -> {to} x{count} (A13): the runner keeps only the last")

    for nid in node_ids:
        if not has_edge[nid]:
            warnings.append(f"orphan node '{nid}': no incoming or outgoing edges")

    perms = project_map.get("permissions", [])
    viewers: dict[str, set] = {}
    actionable: dict[str, set] = {}  # nodes a role can act on (non-viewer grants)
    for p in perms:
        if p["subject"].startswith("role:") and p["object"].startswith("node:"):
            role = p["subject"][len("role:"):]
            node = p["object"][len("node:"):]
            if p["relation"] == "viewer":
                viewers.setdefault(role, set()).add(node)
            else:
                actionable.setdefault(role, set()).add(node)

    for role in roles:
        reachable: set = set()
        frontier = [n for n in viewers.get(role, set()) if n in node_set]
        reachable.update(frontier)
        while frontier:
            current = frontier.pop()
            for edge in project_map["edges"]:
                if edge["from"] == current and edge["to"] not in reachable:
                    if traversable_static(edge, role):
                        reachable.add(edge["to"])
                        frontier.append(edge["to"])
        dead = sorted(
            node_set - reachable - actionable.get(role, set())
        )  # action-target nodes are invoked, not moved into — not movement gaps
        if dead:
            warnings.append(
                f"role '{role}' can never reach: {', '.join(dead)} "
                "(no viewer permission, missing capability for edge.requires, unmet conditional "
                "state guard, or no connecting edge)"
            )

    used_relations = {p["relation"] for p in perms}
    # capability warnings map through the Map's EFFECTIVE vocabulary
    # (re-audit M2/NA14: the default CRUD table lied about custom vocabularies)
    for cap_name in sorted(project_map.get("capabilities", [])):
        relation = vocab.get(cap_name)
        if relation and relation not in used_relations:
            warnings.append(
                f"capability '{cap_name}' is declared but no permission uses its "
                f"relation '{relation}' (A01): dead weight unless something grants it"
            )
    # a roleCapabilities grant nothing consumes is equally dead (NA4)
    required_caps = {c for e in project_map["edges"] for c in e.get("requires", [])}
    for role, caps in role_caps.items():
        for cap in caps:
            if cap not in required_caps:
                warnings.append(
                    f"roleCapabilities grants '{cap}' to '{role}' but no edge.requires "
                    "names it; the grant does nothing"
                )

    action_targets = set().union(*actionable.values()) if actionable else set()
    for edge in project_map["edges"]:
        if edge["to"] not in node_set:
            continue
        guard = (edge.get("when") or {}).get("state")
        if guard:
            warnings.append(
                f"edge {edge['from']} -> {edge['to']} is conditional on state '{guard}'; "
                "static reachability treats it as closed until a journey sets that state"
            )
            continue
        if not any(traversable_static(edge, role) for role in roles) and edge["to"] not in action_targets:
            warnings.append(
                f"edge {edge['from']} -> {edge['to']}: no role can traverse it "
                "(viewer permission missing, capability unmet, or no connecting edge)"
            )

    if "entry" not in project_map:
        warnings.append(
            "no entry nodes declared; journey start positions are unchecked "
            "(Phase 6 will enforce entry semantics)"
        )

    if journeys is not None:
        if not journeys:
            warnings.append("journeys array is empty (A14): the run would pass vacuously")
        seen_ids: set = set()
        for j in journeys:
            jid = j.get("id", "<unnamed>")
            if jid in seen_ids:
                errors.append(f"duplicate journey id '{jid}'")
            seen_ids.add(jid)

    if variables is not None:
        from verify_variables import verify_variables
        for raw in verify_variables(variables, project_map, journeys or []):
            errors.append(
                f"variable matrix: {raw['kind']} in {raw.get('variable', '?')} "
                f"({raw.get('reference', raw.get('node', raw.get('journeyId', '')))})"
            )

    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", required=True)
    ap.add_argument("--journeys")
    ap.add_argument("--variables")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--no-validate", action="store_true", help="doctor the document even if the validator would reject it")
    args = ap.parse_args()

    try:
        project_map = _load(args.map)
        journeys = _load(args.journeys) if args.journeys else None
        variables = _load(args.variables) if args.variables else None
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: unreadable input: {e}")
        return 2

    if not args.no_validate:
        from validate_project_map import load, validate_all
        j_path = args.journeys or ""
        m_errors, m_warnings = [], []
        try:
            journeys_data = _load(args.journeys) if args.journeys else []
            m_errors, m_warnings = validate_all(project_map, journeys_data, args.map, j_path)
        except Exception as e:  # never crash
            m_errors.append(f"{type(e).__name__}: {e}")
        if m_errors:
            print("MAP INVALID — run tools/validate_project_map.py first; doctor refuses to examine a broken Map.")
            for e in m_errors:
                print(f"ERROR: {e}")
            return 2

    errors, warnings = doctor(project_map, journeys, variables)
    for w in warnings:
        print(f"WARNING: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"UNHEALTHY: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    if args.strict and warnings:
        print(f"UNHEALTHY: {len(warnings)} warning(s) in --strict mode")
        return 1
    print(f"HEALTHY: {len(warnings)} warning(s)" if warnings else "HEALTHY: no findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
