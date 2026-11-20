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


if __name__ == "__main__":
    unittest.main()
