#!/usr/bin/env python3
"""Shared action -> relation vocabulary for the Project Map tools.

Single source of truth for the DEFAULT action vocabulary, so the validator
and the runner can never drift apart (audit D2/D3).

Phase 6 (invariant 5): a Map may declare its own vocabulary via the optional
`vocabulary` field, mapping invented actions to invented relations — the
tools read the Map's vocabulary when present and fall back to the default.
`effective_vocabulary()` is the one lookup both tools use.
"""
from __future__ import annotations

# action name -> permission relation it requires
ACTION_TO_RELATION = {
    "view": "viewer",
    "read": "viewer",
    "create": "creator",
    "ingest": "creator",
    "handoff": "creator",
    "edit": "editor",
    "delete": "deleter",
}

# capability name -> relations it grants (inverse view of ACTION_TO_RELATION)
CAPABILITY_RELATIONS = {
    "view": {"viewer"},
    "read": {"viewer"},
    "create": {"creator"},
    "ingest": {"creator"},
    "handoff": {"creator"},
    "edit": {"editor"},
    "delete": {"deleter"},
}


def effective_vocabulary(map_data: dict) -> dict[str, str]:
    """The action->relation mapping in force for this Map.

    When the Map declares `vocabulary`, it replaces the default entirely
    (invariant 5: domain examples are replaceable); otherwise the default
    applies.
    """
    vocab = map_data.get("vocabulary")
    if isinstance(vocab, dict) and vocab and all(
        isinstance(k, str) and isinstance(v, str) for k, v in vocab.items()
    ):
        return dict(vocab)
    return dict(ACTION_TO_RELATION)


def relations_for_capabilities(map_data: dict) -> dict[str, set[str]]:
    """capability name -> relations, for the Map's effective vocabulary."""
    vocab = effective_vocabulary(map_data)
    out: dict[str, set[str]] = {}
    for action, relation in vocab.items():
        out.setdefault(relation, set()).add(action)
    return out
