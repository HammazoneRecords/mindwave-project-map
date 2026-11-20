"""Adapter contract (Phase 7.2, audit plan 5.2).

An Adapter answers two questions about a live or declarative system:

    probe(role, node)  -> {"reachable": bool, "status": str}
    act(role, action, target) -> {"allowed": bool, "evidence": str}

The runner compares adapter observations against the Map's declared
expectations and writes BOTH into the Trace; disagreements become
`adapter_disagreement` findings (category spec_drift).

Invariant 2 guard: adapter observations flow only into the Trace and
Findings — never back into the Map. The runner never mutates the Map from
adapter output; tests pin the Map's bytes.

DeclarativeMapAdapter consults the Map itself (permissions, edges,
requires, roleCapabilities, effective vocabulary), so a run with the
default adapter must agree with the Map by construction; a live adapter
(system under test) is any other subclass.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from vocabulary import effective_vocabulary


class Adapter(ABC):
    """The contract every adapter implements."""

    @abstractmethod
    def probe(self, role: str, node: str) -> dict:
        """Is `role` able to be at / reach `node`? -> {"reachable": bool, "status": str}"""

    @abstractmethod
    def act(self, role: str, action: str, target: str) -> dict:
        """Can `role` perform `action` on `target`? -> {"allowed": bool, "evidence": str}"""


class DeclarativeMapAdapter(Adapter):
    """Consults the Map itself. The reference implementation of the contract."""

    def __init__(self, project_map: dict):
        self.map = project_map
        self.edges = {(e["from"], e["to"]): e for e in project_map["edges"]}
        self.perms = {
            (p["subject"], p["relation"], p["object"])
            for p in project_map.get("permissions", [])
        }
        self.vocab = effective_vocabulary(project_map)
        self.role_caps = project_map.get("roleCapabilities") or {}

    def _can_view(self, role: str, node: str) -> bool:
        return (f"role:{role}", "viewer", f"node:{node}") in self.perms

    def probe(self, role: str, node: str) -> dict:
        # movement reachability: viewer permission on the node is the base;
        # graph connectivity is the runner's job (it knows the position)
        reachable = self._can_view(role, node)
        return {"reachable": reachable, "status": "granted" if reachable else "no viewer permission"}

    def act(self, role: str, action: str, target: str) -> dict:
        relation = self.vocab.get(action, action)
        allowed = (f"role:{role}", relation, f"node:{target}") in self.perms
        return {
            "allowed": allowed,
            "evidence": f"permission (role:{role}, {relation}, node:{target}) "
                        + ("present" if allowed else "absent"),
        }
