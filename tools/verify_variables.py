#!/usr/bin/env python3
"""Verify a Variable Matrix against the repository it claims to describe.

Audit D9: the builder used to check only `mapId`, so 4/5 `definedIn` lines
and 1/6 `usedBy` references could go stale with nobody noticing. This module
checks every reference and turns each stale one into a raw finding
(category spec_drift via tools/findings.py):

- definedIn.file / usedBy[].file must exist relative to the repo root
- the line must be within the file
- for function/object kinds, the signature's identifier must appear on or
  next to the referenced line (contract kinds only get file+line checks)
- every mapNodes entry must be a node in the Map
- every journeySteps entry must reference an existing journey id and a
  step index within that journey's step count
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SYMBOL_FREE_KINDS = {"contract"}  # signatures are file paths, not identifiers


def _identifier(signature: str) -> str | None:
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)", signature or "")
    return m.group(1) if m else None


def _check_file_line(file: str, line: int, symbol: str | None, kind: str, role: str, var_id: str, var_index: int) -> list[dict]:
    findings: list[dict] = []
    where = f"{var_id}.{role} {file}:{line}"
    path = REPO_ROOT / file
    if not path.is_file():
        findings.append({
            "kind": "variable_matrix_file_missing", "step": var_index,
            "variable": var_id, "reference": where,
        })
        return findings
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        findings.append({"kind": "variable_matrix_file_missing", "step": var_index, "variable": var_id, "reference": where})
        return findings
    if not (1 <= line <= len(lines)):
        findings.append({
            "kind": "variable_matrix_line_out_of_range", "step": var_index,
            "variable": var_id, "reference": where, "fileLines": len(lines),
        })
        return findings
    if symbol and kind not in _SYMBOL_FREE_KINDS:
        window = "\n".join(lines[max(0, line - 3): line + 2])  # line +-2, 1-based inclusive
        if symbol not in window:
            findings.append({
                "kind": "variable_matrix_symbol_not_found", "step": var_index,
                "variable": var_id, "reference": where, "symbol": symbol,
            })
    return findings


def verify_variables(variables: dict, project_map: dict, journeys: list) -> list[dict]:
    """Return raw findings for every stale or dangling matrix reference."""
    findings: list[dict] = []
    node_ids = {n["id"] for n in project_map["nodes"]}
    journey_by_id = {j["id"]: j for j in journeys}

    for index, var in enumerate(variables.get("variables", [])):
        var_id = var.get("id", f"<variable {index}>")
        kind = var.get("kind", "")
        symbol = _identifier(var.get("signature", ""))

        defined = var.get("definedIn", {})
        findings.extend(_check_file_line(
            defined.get("file", ""), defined.get("line", -1),
            symbol, kind, "definedIn", var_id, index,
        ))

        for ref in var.get("usedBy", []):
            findings.extend(_check_file_line(
                ref.get("file", ""), ref.get("line", -1),
                symbol, kind, "usedBy", var_id, index,
            ))

        for node_id in var.get("mapNodes", []):
            if node_id not in node_ids:
                findings.append({
                    "kind": "variable_matrix_unknown_map_node", "step": index,
                    "variable": var_id, "node": node_id,
                })

        for ref in var.get("journeySteps", []):
            jid = ref.get("journeyId", "")
            step = ref.get("step", -1)
            journey = journey_by_id.get(jid)
            if journey is None:
                findings.append({
                    "kind": "variable_matrix_unknown_journey_step", "step": index,
                    "variable": var_id, "journeyId": jid,
                })
            elif not (1 <= step <= len(journey.get("steps", []))):
                findings.append({
                    "kind": "variable_matrix_unknown_journey_step", "step": index,
                    "variable": var_id, "journeyId": jid, "requestedStep": step,
                    "journeySteps": len(journey.get("steps", [])),
                })

    return findings
