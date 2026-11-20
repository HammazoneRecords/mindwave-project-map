#!/usr/bin/env python3
"""Validate Project Map documents: JSON-Schema gate + semantic checks.

Design rules (from the 2026-11-17 independent audit, REMEDIATION_PLAN.md):

- Collect ALL errors — never stop at the first one.
- Never crash — any unexpected exception is converted into a structured
  INVALID report (the old validator raised TypeError on malformed roles).
- Schema first: both documents must pass their JSON Schema (spec/*.schema.json)
  via the vendored subset validator (tools/schema_lite.py). If the structure
  is broken, semantic checks would only cascade, so they are skipped.
- Then semantic checks that a schema cannot express: journey roles, act
  targets and actions, checkpoint labels, duplicate journeys/edges, permission
  subject prefixes, unused capabilities, and ignored edge requirements.

Exit codes: 0 valid, 1 invalid (warnings only exit 0 unless --strict).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema_lite import validate as schema_validate  # noqa: E402
from vocabulary import ACTION_TO_RELATION, CAPABILITY_RELATIONS  # noqa: E402

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"

STEP_REQUIREMENTS = {
    "move": ["to"],
    "act": ["action", "target"],
    "checkpoint": ["label"],
    "comment": [],
}


def load(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: JSON line {e.lineno}, column {e.colno}: {e.msg}")


def _schema_gate(data: object, schema_file: str, path: str) -> list[str]:
    schema = json.loads((SPEC_DIR / schema_file).read_text())
    return schema_validate(data, schema, path=path)


def validate_map(data, path):
    """Return (errors, warnings) for a Map document."""
    errors: list[str] = []
    warnings: list[str] = []

    schema_errors = _schema_gate(data, "map.schema.json", path)
    if schema_errors:
        return schema_errors, ["semantic checks skipped: schema errors present"]

    node_ids: dict = {}
    for i, n in enumerate(data["nodes"]):
        p = f"{path}:nodes[{i}]"
        if n["id"] in node_ids:
            errors.append(f"{p}: duplicate node id '{n['id']}'")
        node_ids[n["id"]] = p

    seen_pairs: dict = {}
    for i, e in enumerate(data["edges"]):
        p = f"{path}:edges[{i}]"
        if e["from"] not in node_ids:
            errors.append(f"{p}: unknown from node '{e['from']}'")
        if e["to"] not in node_ids:
            errors.append(f"{p}: unknown to node '{e['to']}'")
        pair = (e["from"], e["to"])
        if pair in seen_pairs:
            errors.append(
                f"{p}: duplicate edge {e['from']} -> {e['to']} (also defined at {seen_pairs[pair]}); "
                "the runner indexes edges by node pair, the second would silently overwrite the first"
            )
        else:
            seen_pairs[pair] = p
        if e.get("requires"):
            warnings.append(
                f"{p}: edge requires {e['requires']} but 'edge.requires' is not enforced yet "
                "(REMEDIATION_PLAN.md Phase 6.1); the runner will allow this move regardless"
            )

    roles = set(data["roles"])
    used_relations: set = set()
    for i, pmt in enumerate(data["permissions"]):
        p = f"{path}:permissions[{i}]"
        subject = pmt["subject"]
        if not subject.startswith("role:"):
            errors.append(
                f"{p}: permission subject '{subject}' is missing the required 'role:' prefix; "
                "the runner would deny everything for it silently"
            )
            continue
        role = subject[len("role:"):]
        if role not in roles:
            errors.append(f"{p}: unknown role '{role}'")
        obj = pmt["object"]
        if not obj.startswith("node:"):
            errors.append(
                f"{p}: permission object '{obj}' is missing the required 'node:' prefix"
            )
            continue
        node = obj[len("node:"):]
        if node not in node_ids:
            errors.append(f"{p}: unknown object node '{node}'")
        used_relations.add(pmt["relation"])

    capabilities = data.get("capabilities") or []
    for cap in capabilities:
        relations = CAPABILITY_RELATIONS.get(cap, set())
        if relations and not (relations & used_relations):
            warnings.append(
                f"{path}: capability '{cap}' is declared but no permission uses any of its "
                f"relations ({sorted(relations)}); it is dead weight unless something grants it"
            )

    if "entry" not in data:
        warnings.append(
            f"{path}: no entry nodes declared; journey start positions are unchecked "
            "(interim — REMEDIATION_PLAN.md Phase 6 enforces entry semantics)"
        )

    return errors, warnings


def validate_journeys(data, map_data, path):
    """Return (errors, warnings) for a Journey file against a validated Map."""
    errors: list[str] = []
    warnings: list[str] = []

    schema_errors = _schema_gate(data, "journey.schema.json", path)
    if schema_errors:
        return schema_errors, ["semantic checks skipped: schema errors present"]

    if not data:
        warnings.append(f"{path}: journeys array is empty; the run would pass vacuously")

    node_ids = {n["id"] for n in map_data["nodes"]}
    roles = {r for r in map_data["roles"]}
    seen_journey_ids: dict = {}
    action_vocab = set(ACTION_TO_RELATION)

    for i, j in enumerate(data):
        p = f"{path}[{i}]"
        jid = j.get("id", f"<unnamed {i}>")
        if jid in seen_journey_ids:
            errors.append(
                f"{p}: duplicate journey id '{jid}' (also at {seen_journey_ids[jid]}); "
                "package links would merge both journeys' steps"
            )
        else:
            seen_journey_ids[jid] = p

        if j["map"] != map_data["id"]:
            errors.append(f"{p}: map '{j['map']}' does not match '{map_data['id']}'")
        if j["initial"]["node"] not in node_ids:
            errors.append(f"{p}.initial: unknown node '{j['initial']['node']}'")
        if j["initial"]["role"] not in roles:
            errors.append(
                f"{p}.initial: unknown role '{j['initial']['role']}' — the runner would execute "
                "the whole journey as a role that exists nowhere in the Map's permissions"
            )

        for k, s in enumerate(j["steps"]):
            sp = f"{p}.steps[{k}]"
            styp = s["type"]
            for field in STEP_REQUIREMENTS.get(styp, []):
                if field not in s or s[field] in (None, ""):
                    errors.append(f"{sp}: step type '{styp}' requires '{field}'")
            if styp == "move" and s.get("to") not in node_ids:
                errors.append(f"{sp}: unknown target node '{s.get('to')}'")
            if styp == "act":
                action = s.get("action")
                if action is not None and action not in action_vocab:
                    errors.append(
                        f"{sp}: unknown action '{action}' — an unknown action is always denied, "
                        "so 'expect: denied' would pass vacuously for a typo"
                    )
                target = s.get("target")
                if target is not None and target not in node_ids:
                    errors.append(f"{sp}: unknown target node '{target}'")

    return errors, warnings


def validate_all(map_data, journeys_data, map_path, journeys_path):
    """Validate both documents; return (errors, warnings) with all findings."""
    errors: list[str] = []
    warnings: list[str] = []
    map_errors, map_warnings = validate_map(map_data, str(map_path))
    errors.extend(map_errors)
    warnings.extend(map_warnings)
    if not map_errors:
        j_errors, j_warnings = validate_journeys(journeys_data, map_data, str(journeys_path))
        errors.extend(j_errors)
        warnings.extend(j_warnings)
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", required=True)
    ap.add_argument("--journeys", required=True)
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    map_data = None
    try:
        map_data = load(Path(args.map))
        journeys_data = load(Path(args.journeys))
        errors, warnings = validate_all(map_data, journeys_data, args.map, args.journeys)
    except (OSError, ValueError) as e:
        errors.append(str(e))
    except Exception as e:  # never crash on malformed input (audit A10)
        errors.append(f"{type(e).__name__}: {e}")

    for w in warnings:
        print(f"WARNING: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"INVALID: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    if args.strict and warnings:
        print(f"INVALID: {len(warnings)} warning(s) in --strict mode")
        return 1

    map_id = map_data.get("id", "?") if isinstance(map_data, dict) else "?"
    suffix = f" ({len(warnings)} warning(s))" if warnings else ""
    print(f"VALID: map={map_id} journeys={args.journeys}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
