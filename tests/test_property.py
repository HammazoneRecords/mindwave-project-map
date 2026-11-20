#!/usr/bin/env python3
"""Seeded property test (audit plan 5.2): validator accepts ⟹ runner never crashes.

No Hypothesis — a deterministic seeded generator produces random Map/Journey
pairs in two modes: ~40% "clean" (structurally sound documents the validator
should accept) and ~60% "chaos" (deliberately broken documents). For every
seed:

1. the shared validator must NEVER raise (it converts anything into errors);
2. when the validator reports zero errors, the runner must execute without
   crashing, produce a trace that conforms to spec/trace.schema.json, and
   exit 0/1 (never 2, never a traceback).

Run with: python3 -m unittest tests.test_property -v
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"

sys.path.insert(0, str(TOOLS))
from schema_lite import validate as schema_validate  # noqa: E402
from validate_project_map import load, validate_all  # noqa: E402

NODE_TYPES = ["screen", "view", "endpoint", "capability", "documentation", "tool"]
EDGE_TYPES = ["navigation", "invokes", "reads", "explains"]
RELATIONS = ["viewer", "creator", "editor", "deleter", "weird_relation"]
KNOWN_ACTIONS = ["view", "create", "edit", "delete", "ingest", "handoff"]
ACTIONS = KNOWN_ACTIONS + ["typo_action", "nuke"]
STEP_TYPES = ["move", "act", "checkpoint", "comment", "assert_unreachable", "unknown_type"]
ROLE_NAMES = ["member", "visitor", "admin", "auditor", "architect"]


class RandomDocGen:
    """Deterministic random document generator (seed controls everything).

    Per-document mode coin: clean mode produces documents the validator
    should accept (the property must not be vacuous); chaos mode injects
    broken fields, unknown references, bad prefixes, and schema violations.
    """

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.clean = self.rng.random() < 0.4
        self.node_ids: list[str] = []
        self.roles: list[str] = []

    def _ref(self, pool, broken):
        return self.rng.choice(pool) if self.clean else self.rng.choice(pool + broken)

    def map(self) -> dict:
        rng = self.rng
        node_count = rng.randint(1, 6)
        nodes = [
            {"id": f"n{i}", "type": rng.choice(NODE_TYPES), "title": f"N{i}"}
            for i in range(node_count)
        ]
        if not self.clean and nodes and rng.random() < 0.3:
            nodes.append({"id": nodes[0]["id"], "type": "screen"})  # duplicate id
        node_ids = [f"n{i}" for i in range(node_count)]

        edges: list = []
        seen_pairs = set()
        for _ in range(rng.randint(0, 6)):
            frm = self._ref(node_ids, ["ghost_from"])
            to = self._ref(node_ids, ["ghost_to"])
            pair = (frm, to)
            if self.clean and (pair in seen_pairs or frm == to):
                continue
            seen_pairs.add(pair)
            edge = {"from": frm, "to": to, "type": rng.choice(EDGE_TYPES)}
            if not self.clean and rng.random() < 0.2:
                edge["requires"] = [rng.choice(["view", "ghost_cap"])]
            edges.append(edge)

        roles = rng.sample(ROLE_NAMES, k=rng.randint(1, 4)) if self.clean else \
            rng.sample(ROLE_NAMES + ["ghost_role"], k=rng.randint(0, 4))

        permissions = []
        for _ in range(rng.randint(0, 8)):
            if self.clean:
                if not roles or not node_ids:
                    break
                subject = f"role:{rng.choice(roles)}"
                obj = f"node:{rng.choice(node_ids)}"
            else:
                subject = rng.choice([f"role:{r}" for r in roles] or ["role:ghost"]) if roles else rng.choice(["member", "role:nobody"])
                obj = rng.choice([f"node:n{i}" for i in range(node_count)] + ["node:ghost", "n1"])
            permissions.append({"subject": subject, "relation": rng.choice(RELATIONS), "object": obj})

        m = {
            "schemaVersion": "1.0.0",
            "id": "fuzz-map",
            "nodes": nodes,
            "edges": edges,
            "roles": roles,
            "capabilities": rng.sample(["view", "create", "edit", "delete"], k=rng.randint(0, 4)),
            "permissions": permissions,
        }
        # clean journeys must reference what this map actually declares
        self.node_ids = node_ids
        self.roles = roles
        if not self.clean and rng.random() < 0.15:
            m["constraints"] = rng.choice(["just a string", [1, 2]])
        if not self.clean and rng.random() < 0.15:
            m["extra_field"] = True  # additionalProperties: false must catch it
        return m

    def journeys(self) -> list:
        rng = self.rng
        journeys = []
        used_ids = set()
        for index in range(rng.randint(1, 3)):
            steps = []
            for _ in range(rng.randint(1, 5)):
                typ = rng.choice(STEP_TYPES if not self.clean else ["move", "act", "checkpoint", "comment"])
                step = {"type": typ}
                if typ == "move":
                    step["to"] = self._ref(self.node_ids or ["n0"], ["ghost_node"])
                    if rng.random() < 0.7:
                        step["expect"] = rng.choice(["allowed", "denied"] if self.clean else ["allowed", "denied", "pass"])
                elif typ == "act":
                    step["action"] = rng.choice(KNOWN_ACTIONS if self.clean else ACTIONS)
                    step["target"] = self._ref(self.node_ids or ["n0"], ["ghost_node"])
                    if rng.random() < 0.7:
                        step["expect"] = rng.choice(["allowed", "denied"])
                elif typ == "checkpoint":
                    if self.clean or rng.random() < 0.85:
                        step["label"] = f"cp-{rng.randint(0, 5)}"
                elif typ == "comment":
                    step["label"] = "note"
                steps.append(step)
            jid = f"fuzz-j{index}" if self.clean else f"fuzz-j{rng.randint(0, 5)}"
            if jid in used_ids and self.clean:
                jid = f"{jid}-{index}"
            used_ids.add(jid)
            journeys.append({
                "schemaVersion": "1.0.0",
                "id": jid,
                "map": "fuzz-map",
                "initial": {
                    "role": self._ref(self.roles or ["member"], ["ghost_role"]),
                    "node": self._ref(self.node_ids or ["n0"], ["ghost_node"]),
                },
                "steps": steps,
            })
        return journeys


class ValidatorRunnerProperty(unittest.TestCase):
    SEEDS = 300

    def test_validator_accepts_implies_runner_never_crashes(self):
        trace_schema = json.loads((REPO / "spec" / "trace.schema.json").read_text())
        accepted = 0
        with tempfile.TemporaryDirectory(prefix="fuzz_") as tmp:
            tmp = Path(tmp)
            for seed in range(self.SEEDS):
                gen = RandomDocGen(seed)
                m, j = gen.map(), gen.journeys()
                map_path = tmp / f"m{seed}.json"
                j_path = tmp / f"j{seed}.json"
                trace_path = tmp / f"t{seed}.json"
                map_path.write_text(json.dumps(m))
                j_path.write_text(json.dumps(j))

                # 1. validator never raises, never crashes
                try:
                    map_data = load(map_path)
                    journeys = load(j_path)
                    errors, warnings = validate_all(map_data, journeys, str(map_path), str(j_path))
                except Exception as exc:  # noqa: BLE001
                    self.fail(f"seed {seed}: validator raised {type(exc).__name__}: {exc}")

                if errors:
                    continue
                accepted += 1

                # 2. validator accepted: runner must not crash, exit 0/1 only
                r = subprocess.run(
                    [sys.executable, str(TOOLS / "run_journeys.py"),
                     "--map", str(map_path), "--journeys", str(j_path),
                     "--trace", str(trace_path)],
                    capture_output=True, text=True, timeout=60,
                )
                combined = r.stdout + r.stderr
                self.assertNotIn("Traceback", combined, f"seed {seed}: runner crashed:\n{combined}")
                self.assertIn(r.returncode, (0, 1),
                              f"seed {seed}: accepted pair exited {r.returncode}:\n{combined}")

                # 3. the produced trace conforms to the trace schema
                if trace_path.exists():
                    trace = json.loads(trace_path.read_text())
                    errs = schema_validate(trace, trace_schema)
                    self.assertEqual(errs, [], f"seed {seed}: trace violates schema: {errs}")

        # the generator must actually produce accepted pairs, or the property is vacuous
        self.assertGreater(accepted, self.SEEDS // 5,
                           f"only {accepted}/{self.SEEDS} seeds were accepted; generator too broken")


if __name__ == "__main__":
    unittest.main()
