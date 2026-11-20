#!/usr/bin/env python3
"""Viewer conformance (Phase 8.1, invariant 4): the skin reads the same
model the runner writes.

Pins three things:

1. the viewer consumes the runner-derived package files (links.json,
   findings.json) instead of re-deriving relationships;
2. every links.json coordinate is real: journey ids exist, step indices are
   in range, the referenced node matches the step/event's own node field;
3. the viewer's JavaScript parses (node --check on the extracted script).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
VIEWER = REPO / "viewer" / "index.html"


class ViewerConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="viewer_"))
        r = subprocess.run(
            [sys.executable, str(TOOLS / "build_inspection_package.py"),
             "--map", str(REPO / "examples" / "project-map-self.map.json"),
             "--journeys", str(REPO / "examples" / "project-map-self.journeys.json"),
             "--variables", str(REPO / "examples" / "project-map-self.variables.json"),
             "--output", str(cls.dir / "pkg")],
            capture_output=True, text=True, timeout=60,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        cls.pkg = cls.dir / "pkg"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_viewer_consumes_package_files(self):
        source = VIEWER.read_text()
        self.assertIn("links.json", source, "viewer must read runner-derived links.json")
        self.assertIn("findings.json", source, "viewer must read runner-derived findings.json")
        self.assertIn("tryFetch", source)
        # no substring highlighting when links are available: linksIndex() gates it
        self.assertIn("linksIndex()", source)

    def test_links_coordinates_are_real(self):
        links = json.loads((self.pkg / "links.json").read_text())
        journeys = {j["id"]: j for j in json.loads((self.pkg / "journeys.json").read_text())}
        trace = json.loads((self.pkg / "trace.json").read_text())
        events_by_journey = {r["journeyId"]: r["events"] for r in trace["journeys"]}
        # step index -> node as the runner resolved it (event index == step index)
        resolved = {
            jid: {i: ev.get("node") for i, ev in enumerate(events, 1)}
            for jid, events in events_by_journey.items()
        }
        checked = 0
        for entry in links["links"]:
            node_id = entry["mapNodeId"]
            for ref in entry["journeySteps"]:
                journey = journeys[ref["journeyId"]]  # must exist
                self.assertLessEqual(ref["step"], len(journey.get("steps", [])))
                step = journey["steps"][ref["step"] - 1]
                resolved_node = resolved[ref["journeyId"]].get(ref["step"])
                self.assertIn(
                    node_id, {step.get("to"), step.get("target"), resolved_node},
                    f"link {node_id} <- {ref} does not match the step's own node",
                )
                checked += 1
            for ref in entry["traceEvents"]:
                event = events_by_journey[ref["journeyId"]][ref["event"] - 1]
                self.assertEqual(event.get("node"), node_id,
                                 f"trace event {ref} must carry node '{node_id}'")
                checked += 1
        self.assertGreater(checked, 10, "the self fixture should produce a rich link set")

    def test_viewer_javascript_parses(self):
        html = VIEWER.read_text()
        script = re.search(r"<script>(.*)</script>", html, re.S).group(1)
        js = self.dir / "viewer-script.js"
        js.write_text(script)
        r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, f"viewer JS does not parse: {r.stderr}")

    def test_findings_rendered_from_package(self):
        findings = json.loads((self.pkg / "findings.json").read_text())
        # fixture trace has no findings; the viewer must render its honest
        # 'none recorded' state rather than a hardcoded claim
        self.assertEqual(findings, [])
        self.assertIn("none recorded", VIEWER.read_text())


if __name__ == "__main__":
    unittest.main()
