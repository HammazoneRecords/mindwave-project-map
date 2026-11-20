#!/usr/bin/env python3
"""The audit's adversarial acceptance suite: cases A01-A23.

Each case ports one adversarial scenario from the 2026-11-17 independent
audit (summarized in REMEDIATION_PLAN.md) and asserts the audit's ideal
outcome: Caught (rejected with a precise message), Clean error (no
traceback), or Sound (already correct and must stay correct).

Interim outcomes: A04 (entry nodes) and A12 (edge.requires enforcement) are
enforced in Phase 6; until that lands the suite asserts the documented
interim behavior (warnings instead of silence). The suite is updated when
Phase 6 flips them to errors.

Run with: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
EXAMPLES = REPO / "examples"

sys.path.insert(0, str(TOOLS))
from validate_project_map import load, validate_all  # noqa: E402  # noqa: E402


def base_map(**overrides) -> dict:
    m = {
        "schemaVersion": "1.0.0",
        "id": "audit-case-map",
        "nodes": [
            {"id": "home", "type": "screen", "title": "Home"},
            {"id": "workspace", "type": "screen", "title": "Workspace"},
        ],
        "edges": [{"from": "home", "to": "workspace", "type": "navigation"}],
        "roles": ["member", "visitor"],
        "capabilities": ["view", "create"],
        "permissions": [
            {"subject": "role:member", "relation": "viewer", "object": "node:home"},
            {"subject": "role:member", "relation": "viewer", "object": "node:workspace"},
            {"subject": "role:member", "relation": "creator", "object": "node:workspace"},
        ],
    }
    m.update(overrides)
    return m


def base_journey(**overrides) -> list:
    j = [
        {
            "schemaVersion": "1.0.0",
            "id": "audit-case-journey",
            "map": "audit-case-map",
            "initial": {"role": "member", "node": "home"},
            "steps": [{"type": "move", "to": "workspace", "expect": "allowed"}],
        }
    ]
    for key, value in overrides.items():
        j[0][key] = value
    return j


class AuditCaseBase(unittest.TestCase):
    """Runs the real CLI tools against a temp fixture pair."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="audit_"))
        self.map_path = self.dir / "map.json"
        self.journeys_path = self.dir / "journeys.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_pair(self, map_data, journeys=None):
        self.map_path.write_text(json.dumps(map_data, indent=2))
        self.journeys_path.write_text(json.dumps(journeys if journeys is not None else base_journey(), indent=2))

    def run_validator(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TOOLS / "validate_project_map.py"),
             "--map", str(self.map_path), "--journeys", str(self.journeys_path)],
            capture_output=True, text=True, timeout=60,
        )

    def run_runner(self, *extra) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TOOLS / "run_journeys.py"),
             "--map", str(self.map_path), "--journeys", str(self.journeys_path),
             "--trace", str(self.dir / "trace.json"), *extra],
            capture_output=True, text=True, timeout=60,
        )

    def run_builder(self, output=None, *extra) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TOOLS / "build_inspection_package.py"),
             "--map", str(self.map_path), "--journeys", str(self.journeys_path),
             "--output", str(output or self.dir / "pkg"), *extra],
            capture_output=True, text=True, timeout=60,
        )

    def assert_no_traceback(self, result):
        combined = result.stdout + result.stderr
        self.assertNotIn("Traceback", combined, f"tool crashed:\n{combined}")


class ValidatorCases(AuditCaseBase):
    def validate_pair(self, map_data, journeys):
        self.write_pair(map_data, journeys)
        return validate_all(load(self.map_path), load(self.journeys_path), str(self.map_path), str(self.journeys_path))

    def test_a01_declared_but_ungranted_capability_warns(self):
        errors, warnings = self.validate_pair(
            base_map(capabilities=["view", "create", "delete"]),
            base_journey(),
        )
        self.assertEqual(errors, [])
        self.assertTrue(any("delete" in w and "declared but no permission" in w for w in warnings),
                        f"expected unused-capability warning, got: {warnings}")

    def test_a02_unknown_move_target_caught(self):
        errors, _ = self.validate_pair(base_map(), base_journey(steps=[{"type": "move", "to": "ghost-node", "expect": "allowed"}]))
        self.assertTrue(any("ghost-node" in e for e in errors), errors)

    def test_a03_act_unknown_target_caught(self):
        errors, _ = self.validate_pair(base_map(), base_journey(steps=[{"type": "act", "action": "create", "target": "ghost-node", "expect": "denied"}]))
        self.assertTrue(any("ghost-node" in e for e in errors), errors)

    def test_a04_entry_nodes_enforced(self):
        # Phase 6.2: with entry declared, a journey may only start where its
        # role is allowed to enter; without entry the validator still warns.
        errors, warnings = self.validate_pair(base_map(), base_journey())
        self.assertEqual(errors, [])
        self.assertTrue(any("entry" in w for w in warnings), warnings)

        enforced_map = base_map(entry={"default": ["home"]})
        errors, _ = self.validate_pair(enforced_map, base_journey())
        self.assertEqual(errors, [], "legal start must pass")

        errors, _ = self.validate_pair(enforced_map, base_journey(initial={"role": "member", "node": "workspace"}))
        self.assertTrue(any("not a legal entry" in e for e in errors), errors)

        # role-specific entry lists override the default
        errors, _ = self.validate_pair(
            base_map(entry={"default": ["home"], "roles": {"member": ["workspace"]}}),
            base_journey(initial={"role": "member", "node": "workspace"}),
        )
        self.assertEqual(errors, [])

    def test_a05_unknown_journey_role_caught(self):
        errors, _ = self.validate_pair(base_map(), base_journey(initial={"role": "ghost", "node": "home"}))
        self.assertTrue(any("ghost" in e for e in errors), errors)

    def test_a06_unknown_step_type_caught_by_schema(self):
        errors, _ = self.validate_pair(base_map(), base_journey(steps=[{"type": "teleport", "to": "workspace"}]))
        self.assertTrue(any("teleport" in e or "enum" in e for e in errors), errors)

    def test_a07_known_target_unknown_action_caught(self):
        errors, _ = self.validate_pair(base_map(), base_journey(steps=[{"type": "act", "action": "nuke", "target": "workspace", "expect": "denied"}]))
        self.assertTrue(any("nuke" in e and "unknown action" in e for e in errors), errors)

    def test_a08_checkpoint_without_label_clean_error(self):
        self.write_pair(base_map(), base_journey(steps=[{"type": "checkpoint"}]))
        r = self.run_validator()
        self.assertEqual(r.returncode, 1)
        self.assert_no_traceback(r)
        self.assertIn("requires 'label'", r.stdout)

    def test_a09_act_missing_target_clean_error(self):
        self.write_pair(base_map(), base_journey(steps=[{"type": "act", "action": "create"}]))
        r = self.run_validator()
        self.assertEqual(r.returncode, 1)
        self.assert_no_traceback(r)
        self.assertIn("requires 'target'", r.stdout)

    def test_a10_malformed_json_clean_error(self):
        self.map_path.write_text("{ this is not json ]")
        self.journeys_path.write_text(json.dumps(base_journey()))
        r = self.run_validator()
        self.assertEqual(r.returncode, 1)
        self.assert_no_traceback(r)
        self.assertIn("JSON line", r.stdout)

    def test_a11_permission_subject_missing_role_prefix_caught(self):
        errors, _ = self.validate_pair(
            base_map(permissions=[{"subject": "member", "relation": "viewer", "object": "node:home"}]),
            base_journey(),
        )
        self.assertTrue(any("role:" in e for e in errors), errors)

    def test_a12_edge_requires_enforced(self):
        # Phase 6.1: requires is real. The roleCapabilities mapping grants
        # capabilities per role; the runner denies a move when the role lacks one.
        map_data = base_map(
            edges=[{"from": "home", "to": "workspace", "type": "navigation", "requires": ["create"]}],
            roleCapabilities={"member": ["view"]},  # member canNOT create
        )
        errors, _ = self.validate_pair(map_data, base_journey())
        self.assertEqual(errors, [])

        r = self.run_runner()
        self.assertEqual(r.returncode, 1, f"journey must fail: {r.stdout}{r.stderr}")
        trace = json.loads((self.dir / "trace.json").read_text())
        raw = trace["journeys"][0]["findings"][0]
        self.assertEqual(raw["kind"], "journey_expectation_mismatch")
        self.assertEqual(raw["actual"], "denied")
        self.assertIn("missing capability", raw.get("reason", ""), raw)

        # grant the capability and the same journey passes
        map_data["roleCapabilities"] = {"member": ["view", "create"]}
        errors, _ = self.validate_pair(map_data, base_journey())
        self.assertEqual(errors, [])
        r = self.run_runner()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        # an edge requiring an undeclared capability is rejected outright
        broken = base_map(edges=[{"from": "home", "to": "workspace", "type": "navigation", "requires": ["ghost_cap"]}])
        errors, _ = self.validate_pair(broken, base_journey())
        self.assertTrue(any("ghost_cap" in e for e in errors), errors)

    def test_a13_duplicate_edges_caught(self):
        errors, _ = self.validate_pair(
            base_map(edges=[
                {"from": "home", "to": "workspace", "type": "navigation"},
                {"from": "home", "to": "workspace", "type": "navigation"},
            ]),
            base_journey(),
        )
        self.assertTrue(any("duplicate edge" in e for e in errors), errors)

    def test_a14_empty_journeys_warns(self):
        errors, warnings = self.validate_pair(base_map(), [])
        self.assertEqual(errors, [])
        self.assertTrue(any("empty" in w for w in warnings), warnings)

    def test_a15_duplicate_journey_ids_caught(self):
        journeys = base_journey()
        journeys.append(dict(journeys[0]))
        errors, _ = self.validate_pair(base_map(), journeys)
        self.assertTrue(any("duplicate journey id" in e for e in errors), errors)

    def test_a21_unknown_permission_object_node_caught(self):
        errors, _ = self.validate_pair(
            base_map(permissions=[{"subject": "role:member", "relation": "viewer", "object": "node:ghost"}]),
            base_journey(),
        )
        self.assertTrue(any("unknown object node 'ghost'" in e for e in errors), errors)

    def test_d4_expect_enum_drift_caught(self):
        errors, _ = self.validate_pair(base_map(), base_journey(steps=[{"type": "move", "to": "workspace", "expect": "pass"}]))
        self.assertTrue(any("enum" in e.lower() for e in errors), errors)


class RunnerCases(AuditCaseBase):
    def test_a16_sound_valid_fixtures_still_pass(self):
        for map_name, j_name in [
            ("mindwavemine.map.json", "mindwavemine.journeys.json"),
            ("project-map-self.map.json", "project-map-self.journeys.json"),
            ("workspace.map.json", "member-create.journey.json"),
        ]:
            r = subprocess.run(
                [sys.executable, str(TOOLS / "run_journeys.py"),
                 "--map", str(EXAMPLES / map_name), "--journeys", str(EXAMPLES / j_name),
                 "--trace", str(self.dir / f"{map_name}.trace.json")],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(r.returncode, 0, f"{map_name}: {r.stdout}{r.stderr}")
            self.assert_no_traceback(r)

    def test_a17_missing_edge_branch_is_live(self):
        # permission on the target exists, but the Map declares no edge:
        # the mismatch AND a missing_edge finding must both appear.
        self.write_pair(
            base_map(edges=[]),
            base_journey(steps=[{"type": "move", "to": "workspace", "expect": "allowed"}]),
        )
        r = self.run_builder()
        self.assertNotEqual(r.returncode, 0)  # journey fails, package still written
        findings = json.loads((self.dir / "pkg" / "findings.json").read_text())
        kinds = {f["kind"] for f in findings}
        self.assertIn("missing_edge", kinds, findings)
        self.assertIn("journey_expectation_mismatch", kinds)
        categories = {f["category"] for f in findings}
        self.assertIn("missing_edge", categories)
        self.assertIn("under_permission", categories)

    def test_a18_over_and_under_permission_distinct_categories(self):
        # under_permission: expected allowed, Map denies
        self.write_pair(
            base_map(permissions=base_map()["permissions"][:1]),  # drop workspace grants
            base_journey(steps=[{"type": "act", "action": "create", "target": "workspace", "expect": "allowed"}]),
        )
        r = self.run_builder()
        under = json.loads((self.dir / "pkg" / "findings.json").read_text())
        self.assertEqual({f["category"] for f in under}, {"under_permission"}, under)
        self.assertEqual({f["severity"] for f in under}, {"medium"})

        # over_permission: expected denied, Map allows (creator grant restored)
        self.write_pair(
            base_map(),
            base_journey(steps=[{"type": "act", "action": "create", "target": "workspace", "expect": "denied"}]),
        )
        self.run_builder(output=self.dir / "pkg2")
        over = json.loads((self.dir / "pkg2" / "findings.json").read_text())
        self.assertEqual({f["category"] for f in over}, {"over_permission"}, over)
        self.assertEqual({f["severity"] for f in over}, {"high"})

    def test_a19_validator_never_crashes_on_malformed_documents(self):
        malformed_maps = [
            {"nodes": 5, "edges": "x"},
            {"nodes": [{"id": 1, "type": None}], "edges": [[]], "roles": {}},
            {"nodes": [], "edges": [{"from": None}], "roles": ["a"], "permissions": ["nope"]},
            {"nodes": [], "edges": [], "roles": ["a"], "permissions": [{"subject": None}]},
            [],
            "a string",
        ]
        malformed_journeys = [
            {"not": "an array"},
            [{"steps": "walk"}],
            [{"id": 5, "map": None, "initial": 3, "steps": [1, 2, 3]}],
            [{"steps": [{"type": {}}]}],
        ]
        for i, m in enumerate(malformed_maps):
            self.write_pair(m, base_journey())
            r = self.run_validator()
            self.assert_no_traceback(r)
            self.assertIn("INVALID", r.stdout + r.stderr)
        for i, j in enumerate(malformed_journeys):
            self.write_pair(base_map(), j)
            r = self.run_validator()
            self.assert_no_traceback(r)
        # the runner refuses malformed input with the same discipline
        self.write_pair({"nodes": 5}, base_journey())
        r = self.run_runner()
        self.assert_no_traceback(r)
        self.assertNotEqual(r.returncode, 0)

    def test_a20_sound_trace_deterministic_modulo_volatile_fields(self):
        self.write_pair(base_map(), base_journey())
        for name in ("t1.json", "t2.json"):
            r = self.run_runner("--trace", str(self.dir / name))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        def normalized(path):
            trace = json.loads(Path(path).read_text())
            trace.pop("runId", None)
            trace.pop("timestamp", None)
            return json.dumps(trace, sort_keys=True, indent=2)

        self.assertEqual(normalized(self.dir / "t1.json"), normalized(self.dir / "t2.json"))

    def test_a23_runner_refuses_to_overwrite_inputs(self):
        self.write_pair(base_map(), base_journey())
        r = self.run_runner("--trace", str(self.map_path))
        self.assertNotEqual(r.returncode, 0)
        self.assert_no_traceback(r)
        self.assertIn("REFUSED", r.stdout + r.stderr)
        self.assertEqual(json.loads(self.map_path.read_text())["id"], "audit-case-map")


class BuilderCases(AuditCaseBase):
    def setUp(self):
        super().setUp()
        self.write_pair(base_map(), base_journey())

    def test_a22_links_exact_no_substring_no_default_to_start(self):
        r = self.run_builder()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        links = json.loads((self.dir / "pkg" / "links.json").read_text())
        by_node = {entry["mapNodeId"]: entry for entry in links["links"]}
        # home is only the start; no step targets it, and the checkpoint-less
        # journey must NOT default any step onto it
        self.assertEqual(by_node["home"]["journeySteps"], [], by_node["home"])
        self.assertEqual(by_node["home"]["traceEvents"], [], by_node["home"])
        # workspace is the move target: exactly one step and one event
        self.assertEqual(by_node["workspace"]["journeySteps"], [{"journeyId": "audit-case-journey", "step": 1}])
        self.assertEqual(by_node["workspace"]["traceEvents"], [{"journeyId": "audit-case-journey", "event": 1}])

    def test_a22b_checkpoint_links_to_actual_node_not_start(self):
        journeys = base_journey(steps=[
            {"type": "move", "to": "workspace", "expect": "allowed"},
            {"type": "checkpoint", "label": "arrived"},
        ])
        self.write_pair(base_map(), journeys)
        r = self.run_builder()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        links = json.loads((self.dir / "pkg" / "links.json").read_text())
        by_node = {entry["mapNodeId"]: entry for entry in links["links"]}
        # the checkpoint (step 2 / event 2) happened AT workspace, not home
        self.assertIn({"journeyId": "audit-case-journey", "step": 2}, by_node["workspace"]["journeySteps"])
        self.assertIn({"journeyId": "audit-case-journey", "event": 2}, by_node["workspace"]["traceEvents"])
        self.assertNotIn({"journeyId": "audit-case-journey", "step": 2}, by_node["home"]["journeySteps"])

    def test_findings_conform_to_finding_schema(self):
        # force a finding, then validate findings.json against spec/finding.schema.json
        journeys = base_journey(steps=[{"type": "act", "action": "create", "target": "workspace", "expect": "denied"}])
        self.write_pair(base_map(), journeys)
        self.run_builder(output=self.dir / "pkg3")
        from schema_lite import validate
        schema = json.loads((REPO / "spec" / "finding.schema.json").read_text())
        findings = json.loads((self.dir / "pkg3" / "findings.json").read_text())
        self.assertTrue(findings, "expected at least one finding")
        for f in findings:
            errs = validate(f, schema)
            self.assertEqual(errs, [], f"finding violates schema: {errs}")

    def test_trace_conforms_to_trace_schema(self):
        self.run_builder()
        from schema_lite import validate
        schema = json.loads((REPO / "spec" / "trace.schema.json").read_text())
        trace = json.loads((self.dir / "pkg" / "trace.json").read_text())
        self.assertEqual(validate(trace, schema), [])

    def test_map_derived_flowchart_describes_the_map(self):
        self.run_builder()
        mmd = (self.dir / "pkg" / "flowchart.mmd").read_text()
        self.assertIn("audit-case-map", mmd)
        self.assertIn('home["Home [screen]"]', mmd)
        self.assertIn("home -->|navigation| workspace", mmd)
        pseudo = (self.dir / "pkg" / "pseudocode.txt").read_text()
        self.assertIn("audit-case-map", pseudo)
        self.assertIn("member:", pseudo)
        self.assertIn("creator(workspace)", pseudo)


class Phase6Cases(AuditCaseBase):
    """Phase 6 acceptance: A12 denied; non-CRUD fixture runs; coverage answers
    "what was untested"."""

    BREWERY_MAP = EXAMPLES / "brewery.map.json"
    BREWERY_J = EXAMPLES / "brewery.journeys.json"

    def setUp(self):
        super().setUp()
        self.write_pair(base_map(), base_journey())

    def test_brewery_non_crud_vocabulary_runs(self):
        # invariant 5: an invented brew/siphon/seal vocabulary works end to end
        r = subprocess.run(
            [sys.executable, str(TOOLS / "run_journeys.py"),
             "--map", str(self.BREWERY_MAP), "--journeys", str(self.BREWERY_J),
             "--trace", str(self.dir / "brewery-trace.json")],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assert_no_traceback(r)
        trace = json.loads((self.dir / "brewery-trace.json").read_text())
        self.assertTrue(all(j["passed"] for j in trace["journeys"]),
                        [j["findings"] for j in trace["journeys"] if not j["passed"]])
        # the capability-gated walk denied for the right reason (A12 in a real fixture)
        gated = next(j for j in trace["journeys"] if j["journeyId"] == "brewer-cannot-enter-cellar")
        self.assertTrue(gated["passed"])

    def test_brewery_visitor_denials_meaningful(self):
        r = subprocess.run(
            [sys.executable, str(TOOLS / "run_journeys.py"),
             "--map", str(self.BREWERY_MAP), "--journeys", str(self.BREWERY_J),
             "--trace", str(self.dir / "t.json")],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, 0)
        trace = json.loads((self.dir / "t.json").read_text())
        visitor = next(j for j in trace["journeys"] if j["journeyId"] == "visitor-stays-out")
        denials = [e for e in visitor["events"] if e["detail"].endswith(": denied")]
        self.assertEqual(len(denials), 2, visitor)

    def test_coverage_answers_what_was_untested(self):
        r = self.run_builder()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        cov = json.loads((self.dir / "pkg" / "coverage.json").read_text())
        self.assertEqual(cov["nodes"]["total"], 2)
        self.assertIn("workspace", cov["nodes"]["touched"])
        self.assertIn("home", cov["nodes"]["untouched"])  # start node, never a step target
        self.assertEqual(cov["edges"]["used"], [["home", "workspace"]])
        self.assertEqual(cov["permissions"]["declared"], 3)
        # the exercised viewer grant on workspace is spelled out
        self.assertIn("role:member|viewer|node:workspace", cov["permissions"]["exercised"])
        # roles section reports reachability per role
        self.assertIn("member", cov["roles"])
        self.assertIn("visitor", cov["roles"])

    def test_coverage_in_trace_conforms(self):
        r = self.run_builder()
        self.assertEqual(r.returncode, 0)
        trace = json.loads((self.dir / "pkg" / "trace.json").read_text())
        self.assertIn("coverage", trace)
        self.assertIn("untouched", trace["coverage"]["nodes"])


class Phase7Cases(AuditCaseBase):
    """Phase 7 acceptance: each depth feature lands with its own tests."""

    BREWERY_MAP = EXAMPLES / "brewery.map.json"
    BREWERY_J = EXAMPLES / "brewery.journeys.json"

    def _run(self, map_path, j_path, trace, *extra):
        return subprocess.run(
            [sys.executable, str(TOOLS / "run_journeys.py"),
             "--map", str(map_path), "--journeys", str(j_path), "--trace", str(trace), *extra],
            capture_output=True, text=True, timeout=60,
        )

    # ---- 7.1 assert_unreachable ----
    def test_assert_unreachable_confirms_absence(self):
        # visitor can never reach the brew kettle from the gate
        journeys = base_journey(initial={"role": "visitor", "node": "home"},
                                steps=[{"type": "assert_unreachable", "target": "workspace"}])
        # visitor needs a legal entry
        map_data = base_map(entry={"default": ["home"]},
                            permissions=[{"subject": "role:visitor", "relation": "viewer", "object": "node:home"}])
        self.write_pair(map_data, journeys)
        r = self._run(self.map_path, self.journeys_path, self.dir / "t.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        trace = json.loads((self.dir / "t.json").read_text())
        ev = trace["journeys"][0]["events"][0]
        self.assertTrue(ev["detail"].startswith("assert_unreachable workspace: confirmed"))

    def test_assert_unreachable_violated_is_fatal_finding(self):
        # member CAN reach workspace from home: the absence claim must fail loudly
        journeys = base_journey(steps=[
            {"type": "assert_unreachable", "target": "workspace"},
        ])
        self.write_pair(base_map(), journeys)
        r = self._run(self.map_path, self.journeys_path, self.dir / "t.json")
        self.assertEqual(r.returncode, 1)
        self.assert_no_traceback(r)
        trace = json.loads((self.dir / "t.json").read_text())
        raw = trace["journeys"][0]["findings"][0]
        self.assertEqual(raw["kind"], "assert_unreachable_violated")
        self.assertFalse(trace["journeys"][0]["passed"])

    def test_assert_unreachable_finding_taxonomy(self):
        journeys = base_journey(steps=[{"type": "assert_unreachable", "target": "workspace"}])
        self.write_pair(base_map(), journeys)
        self.run_builder()
        findings = json.loads((self.dir / "pkg" / "findings.json").read_text())
        self.assertTrue(findings)
        self.assertEqual({f["category"] for f in findings}, {"unreachable"})
        self.assertEqual({f["severity"] for f in findings}, {"high"})

    # ---- 7.2 adapter contract ----
    def test_declarative_adapter_agrees_with_map(self):
        # by construction the declarative adapter mirrors the Map: zero disagreements
        for map_name, j_name in [("mindwavemine.map.json", "mindwavemine.journeys.json"),
                                 ("brewery.map.json", "brewery.journeys.json")]:
            r = self._run(EXAMPLES / map_name, EXAMPLES / j_name, self.dir / f"{map_name}.json")
            self.assertEqual(r.returncode, 0, f"{map_name}: {r.stdout}{r.stderr}")
            trace = json.loads((self.dir / f"{map_name}.json").read_text())
            disagreements = [f for res in trace["journeys"] for f in res["findings"]
                             if f["kind"] == "adapter_disagreement"]
            self.assertEqual(disagreements, [])

    def test_divergent_adapter_produces_findings_and_never_touches_map(self):
        # invariant 2: adapter observations flow into Trace/Findings only
        sys.path.insert(0, str(REPO))
        from adapters import DeclarativeMapAdapter

        class LyingAdapter(DeclarativeMapAdapter):
            def act(self, role, action, target):
                out = super().act(role, action, target)
                out["allowed"] = not out["allowed"]
                out["evidence"] = "lying adapter (test stub)"
                return out

        self.write_pair(base_map(), base_journey(steps=[
            {"type": "act", "action": "create", "target": "workspace", "expect": "allowed"}]))
        map_before = self.map_path.read_text()

        from run_journeys import index_map, run_journey
        from adapters import DeclarativeMapAdapter as D
        map_data = json.loads(map_before)
        adapter = LyingAdapter(map_data)
        nodes, edges, perms = index_map(map_data)
        result = run_journey(json.loads(self.journeys_path.read_text())[0], nodes, edges, perms, adapter=adapter)
        disagreements = [f for f in result["findings"] if f["kind"] == "adapter_disagreement"]
        self.assertEqual(len(disagreements), 1, result["findings"])
        self.assertEqual(disagreements[0]["adapter"]["evidence"], "lying adapter (test stub)")
        self.assertEqual(self.map_path.read_text(), map_before, "the Map must be byte-identical (invariant 2)")

        # the contract: probe/act return the required keys
        d = D(base_map())
        probe = d.probe("member", "workspace")
        act = d.act("member", "create", "workspace")
        self.assertEqual(set(probe), {"reachable", "status"})
        self.assertEqual(set(act), {"allowed", "evidence"})

    # ---- 7.3 matrix journeys ----
    def test_matrix_expansion_probes_permission_surface(self):
        matrix_journey = {
            "schemaVersion": "1.0.0",
            "id": "brewery-surface",
            "map": "brewery-floor",
            "initial": {"role": "visitor", "node": "gate"},
            "matrix": {"roles": ["brewer", "visitor"], "targets": ["tap", "cask"], "action": "taste"},
        }
        self.write_pair(json.loads(self.BREWERY_MAP.read_text()), [matrix_journey])
        r = self._run(self.map_path, self.journeys_path, self.dir / "m.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        trace = json.loads((self.dir / "m.json").read_text())
        ids = sorted(res["journeyId"] for res in trace["journeys"])
        self.assertEqual(ids, [
            "brewery-surface__brewer__cask",
            "brewery-surface__brewer__tap",
            "brewery-surface__visitor__cask",
            "brewery-surface__visitor__tap",
        ])
        self.assertEqual(trace["expandedJourneys"]["brewery-surface__brewer__tap"], "brewery-surface")
        # the Map was never edited: the fixture file is untouched
        self.assertIn('"matrix"', self.journeys_path.read_text())
        # the probe recorded a real permission decision per pair
        brewer_tap = next(res for res in trace["journeys"] if res["journeyId"] == "brewery-surface__brewer__tap")
        self.assertTrue(brewer_tap["events"][0]["detail"].endswith(": allowed"))

    def test_matrix_bad_fields_rejected(self):
        self.write_pair(base_map(), base_journey(matrix={"roles": ["ghost"], "targets": ["workspace"]}))
        r = self.run_validator()
        self.assertEqual(r.returncode, 1)
        self.assertTrue(any("unknown role 'ghost'" in e for e in [r.stdout]), r.stdout)

    # ---- 7.4 differential traces ----
    def test_diff_traces_reports_regressions(self):
        self.write_pair(base_map(), base_journey())
        self._run(self.map_path, self.journeys_path, self.dir / "old.json")
        # flip the expectation: now the journey fails
        self.write_pair(base_map(), base_journey(steps=[{"type": "move", "to": "workspace", "expect": "denied"}]))
        self._run(self.map_path, self.journeys_path, self.dir / "new.json")
        r = subprocess.run(
            [sys.executable, str(TOOLS / "diff_traces.py"),
             str(self.dir / "old.json"), str(self.dir / "new.json")],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("REGRESSION audit-case-journey: pass -> fail", r.stdout)
        self.assertIn("REGRESSIONS 1", r.stdout)
        self.assertNotIn("different Map content", r.stdout)  # the Map is identical here; only journeys changed

        # reverse direction: the fix is reported, exit 0
        r2 = subprocess.run(
            [sys.executable, str(TOOLS / "diff_traces.py"),
             str(self.dir / "new.json"), str(self.dir / "old.json")],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r2.returncode, 0)
        self.assertIn("FIXED", r2.stdout)

    # ---- 7.5 conditional edges ----
    def test_conditional_edge_state_guard(self):
        # the edge home->workspace carries when: {state: night_shift}
        map_data = base_map(edges=[
            {"from": "home", "to": "workspace", "type": "navigation", "when": {"state": "night_shift"}},
        ])
        # without the set: denied; with the set: allowed — same Map, same role
        without = base_journey(steps=[{"type": "move", "to": "workspace", "expect": "denied"}])
        self.write_pair(map_data, without)
        r = self._run(self.map_path, self.journeys_path, self.dir / "w.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        trace = json.loads((self.dir / "w.json").read_text())
        self.assertTrue(trace["journeys"][0]["events"][0]["detail"].endswith(": denied"))

        with_state = base_journey(steps=[
            {"type": "comment", "label": "shift begins", "set": {"night_shift": True}},
            {"type": "move", "to": "workspace", "expect": "allowed"},
        ])
        self.write_pair(map_data, with_state)
        r = self._run(self.map_path, self.journeys_path, self.dir / "s.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        trace = json.loads((self.dir / "s.json").read_text())
        events = trace["journeys"][0]["events"]
        self.assertEqual(events[0]["setState"], {"night_shift": True})
        self.assertTrue(events[1]["detail"].endswith(": allowed"))
        # the Map bytes never changed (state lives in the Trace)
        self.assertEqual(json.loads(self.map_path.read_text())["edges"][0]["when"], {"state": "night_shift"})

    def test_dead_state_guard_warns(self):
        map_data = base_map(edges=[
            {"from": "home", "to": "workspace", "type": "navigation", "when": {"state": "never_set"}},
        ])
        errors, warnings = validate_all(map_data, base_journey(), "m.json", "j.json")
        self.assertEqual(errors, [])
        self.assertTrue(any("never_set" in w and "no journey step ever sets it" in w for w in warnings),
                        warnings)


if __name__ == "__main__":
    unittest.main()
