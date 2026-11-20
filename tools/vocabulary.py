#!/usr/bin/env python3
"""Shared action -> relation vocabulary for the Project Map tools.

Single source of truth for the default action vocabulary, so the validator
and the runner can never drift apart (audit D2/D3). Phase 6 moves this
vocabulary into the Map itself (parameterized capabilities); until then
every Map is checked against these known actions.
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
