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
from vocabulary import effective_vocabulary  # noqa: E402

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"

STEP_REQUIREMENTS = {
    "move": ["to"],
    "act": ["action", "target"],
    "checkpoint": ["label"],
    "comment": [],
    "assert_unreachable": ["target"],
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

    roles = set(data["roles"])
    capabilities = set(data.get("capabilities") or [])

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
        for cap in e.get("requires", []):
            if cap not in capabilities:
                errors.append(
                    f"{p}: edge requires capability '{cap}' which the Map does not declare; "
                    "no role could ever be granted it"
                )

    role_caps = data.get("roleCapabilities") or {}
    for role, caps in role_caps.items():
        if role not in roles:
            errors.append(f"{path}:roleCapabilities: unknown role '{role}'")
        if not isinstance(caps, list):
            errors.append(f"{path}:roleCapabilities.{role}: expected a list of capability names")
            continue
        for cap in caps:
            if cap not in capabilities:
                errors.append(
                    f"{path}:roleCapabilities.{role}: grants capability '{cap}' which the Map "
                    "does not declare"
                )
    if "requires" in json.dumps(data.get("edges", [])) and not role_caps:
        warnings.append(
            f"{path}: edges declare 'requires' but no roleCapabilities mapping exists; "
            "as declared, no role can traverse those edges"
        )

    entry = data.get("entry")
    if entry is not None:
        default_nodes = entry.get("default", [])
        role_entries = entry.get("roles", {})
        for nid in default_nodes:
            if nid not in node_ids:
                errors.append(f"{path}:entry.default: unknown node '{nid}'")
        for role, nodes in role_entries.items():
            if role not in roles:
                errors.append(f"{path}:entry.roles: unknown role '{role}'")
            for nid in nodes or []:
                if nid not in node_ids:
                    errors.append(f"{path}:entry.roles.{role}: unknown node '{nid}'")
    else:
        warnings.append(
            f"{path}: no entry nodes declared; journey start positions are unchecked "
            "(declare 'entry' to enforce start semantics)"
        )

    guarded_states: set = set()
    for i, e in enumerate(data["edges"]):
        when = e.get("when")
        if when and isinstance(when, dict) and when.get("state"):
            guarded_states.add(when["state"])

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

    # unused-capability warning maps capability names through the Map's
    # effective vocabulary (Phase 6.4): capability 'brew' grants relation
    # 'brewer' when vocabulary says brew->brewer; 'view' grants 'viewer' by default
    vocab = effective_vocabulary(data)
    for cap_name in sorted(capabilities):
        relation = vocab.get(cap_name)
        if relation and relation not in used_relations:
            warnings.append(
                f"{path}: capability '{cap_name}' is declared but no permission uses its "
                f"relation '{relation}'; it is dead weight unless something grants it"
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
    action_vocab = set(effective_vocabulary(map_data))  # the Map's own vocabulary wins (Phase 6.4)

    entry = map_data.get("entry")
    if entry is not None:
        default_nodes = set(entry.get("default", []))
        role_entries = entry.get("roles", {})

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
        elif entry is not None:
            # A04, enforced (Phase 6.2): a journey may only start where its
            # role is allowed to enter (role-specific list, else the default)
            allowed_starts = set(role_entries.get(j["initial"]["role"], default_nodes))
            if j["initial"]["node"] not in allowed_starts:
                errors.append(
                    f"{p}.initial: node '{j['initial']['node']}' is not a legal entry for role "
                    f"'{j['initial']['role']}' (entry allows: {sorted(allowed_starts) or '(none)'})"
                )

        matrix = j.get("matrix")
        if matrix is not None:
            # Phase 7.3: matrix fields are validated here; the runner's
            # expansion output is Journeys only — never a Map edit
            m_roles = matrix.get("roles", [])
            m_targets = matrix.get("targets", [])
            m_action = matrix.get("action", "view")
            if not m_roles or not m_targets:
                errors.append(f"{p}.matrix: both 'roles' and 'targets' must be non-empty lists")
            for r in m_roles:
                if r not in roles:
                    errors.append(f"{p}.matrix: unknown role '{r}'")
            for t in m_targets:
                if t not in node_ids:
                    errors.append(f"{p}.matrix: unknown target node '{t}'")
            if m_action not in action_vocab:
                errors.append(f"{p}.matrix: unknown probe action '{m_action}'")
            else:
                expanded = [f"{jid}__{r}__{t}" for r in m_roles for t in m_targets]
                for cid in expanded:
                    if cid in seen_journey_ids:
                        errors.append(
                            f"{p}.matrix: expansion id collision '{cid}' (also at {seen_journey_ids[cid]})"
                        )
                    else:
                        seen_journey_ids[cid] = f"{p}.matrix expansion"
        elif "steps" not in j:
            errors.append(f"{p}: journey has no steps (a plain journey needs steps; a matrix journey uses 'matrix')")

        for k, s in enumerate(j.get("steps", [])):
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
            if styp == "assert_unreachable" and s.get("target") not in node_ids:
                errors.append(f"{sp}: unknown target node '{s.get('target')}' for absence claim")

    # Phase 7.5: a conditional edge whose state key no journey ever sets is a dead guard
    guarded = set()
    for e in map_data["edges"]:
        when = e.get("when")
        if when and isinstance(when, dict) and when.get("state"):
            guarded.add(when["state"])
    set_keys = set()
    for j in data:
        for s in j.get("steps", []):
            if isinstance(s.get("set"), dict):
                set_keys.update(s["set"].keys())
    for key in sorted(guarded - set_keys):
        warnings.append(
            f"{path}: edge guard on state '{key}' but no journey step ever sets it; "
            "that edge is untraversable as declared"
        )

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
