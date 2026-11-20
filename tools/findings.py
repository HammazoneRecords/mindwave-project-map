#!/usr/bin/env python3
"""Finding taxonomy and provenance helpers (Phase 3 of REMEDIATION_PLAN.md).

Kills audit D8 ("hardcoded severity, one kind") and D7 ("no Map version/hash
in Findings"): every Finding now carries a rule-based category, severity, and
confidence, plus provenance that pins it to the exact Map content that
produced it.

Categories (audit plan 3.3):

- under_permission: a Journey expected access the Map does not grant.
- over_permission:  the Map grants access a Journey (or the author's own
                    expectation) says must not exist. Security-relevant.
- missing_edge:     a permission exists but no declared edge carries it —
                    the Map is structurally incomplete.
- spec_drift:       a secondary document (Variable Matrix, links, adapter
                    observation) disagrees with the Map or the source.
- unreachable:      an explicit absence claim (assert_unreachable) failed,
                    or analysis proved a dead region.

Severity and confidence are derived from rules, never hardcoded per call.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

CATEGORIES = ("under_permission", "over_permission", "missing_edge", "spec_drift", "unreachable")
SEVERITIES = ("info", "low", "medium", "high", "critical")
CONFIDENCE_LEVELS = ("high", "medium", "low")

# kind + (expected, actual) -> (category, severity, confidence)
_RULES: dict[tuple, tuple] = {
    # expected access that the Map denies
    ("journey_expectation_mismatch", "allowed", "denied"): ("under_permission", "medium", "high"),
    # the Map allows what the author explicitly expected to be denied
    ("journey_expectation_mismatch", "denied", "allowed"): ("over_permission", "high", "high"),
    # permission exists but the graph has no edge for it
    ("missing_edge", None, None): ("missing_edge", "low", "high"),
    # an explicit absence claim failed: the role CAN reach the node
    ("assert_unreachable_violated", None, None): ("unreachable", "high", "high"),
    # adapter observation disagrees with the Map's declared expectation
    ("adapter_disagreement", None, None): ("spec_drift", "medium", "medium"),
}

# kinds produced by Variable Matrix / links verification (Phase 4)
_SPEC_DRIFT_KINDS = {
    "variable_matrix_dangling_reference",
    "variable_matrix_symbol_not_found",
    "variable_matrix_file_missing",
    "variable_matrix_line_out_of_range",
    "variable_matrix_unknown_map_node",
    "variable_matrix_unknown_journey_step",
}


def classify(raw: dict) -> tuple[str, str, str]:
    """Return (category, severity, confidence) for a raw runner/verifier finding."""
    kind = raw.get("kind", "")
    if kind in _SPEC_DRIFT_KINDS:
        return ("spec_drift", "medium", "high")
    expected = raw.get("expected")
    actual = raw.get("actual")
    key = (kind, expected, actual)
    if key in _RULES:
        return _RULES[key]
    if kind in _RULES:  # match without the expected/actual dimension
        return _RULES[(kind, None, None)]
    # unknown kind: be conservative, never invent a category silently
    return ("spec_drift", "medium", "low")


def finding_from_raw(raw: dict, journey_id: str, trace: dict) -> dict:
    """Build a finding.schema.json-conformant Finding from a raw finding."""
    category, severity, confidence = classify(raw)
    details = ", ".join(
        f"{key}={value}" for key, value in raw.items() if key not in {"kind", "step"}
    )
    source = {
        "mapId": trace.get("mapId"),
        "journeyId": journey_id,
        "step": raw.get("step"),
    }
    for provenance_key in ("mapSha256", "journeysSha256", "runId"):
        if trace.get(provenance_key) is not None:
            source[provenance_key] = trace[provenance_key]
    if trace.get("mapVersion") is not None:
        source["mapVersion"] = trace["mapVersion"]
    finding = {
        "kind": raw.get("kind", "unknown"),
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "status": "open",
        "message": details or raw.get("kind", "unspecified finding"),
        "source": source,
    }
    return finding


def sha256_file(path: Path | str) -> str:
    """Content hash of a document — the provenance anchor for Findings (D7)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
