#!/usr/bin/env python3
"""Regression tests for invariant 1: a Journey can never rewrite the Map.

Ports the audit's case A23 (2026-11-17): `run_journeys.py --trace` pointed at
the Map file used to overwrite the Map with a Trace, silently. The guard must
refuse. Suite grows in Phase 5 of REMEDIATION_PLAN.md.

Run with: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
MAP = REPO / "examples" / "workspace.map.json"
JOURNEYS = REPO / "examples" / "member-create.journey.json"


def snapshot(path: Path) -> str:
    return path.read_text()


class OverwriteGuardTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="guard_"))
        self.map_copy = self.dir / "m.json"
        self.j_copy = self.dir / "j.json"
        shutil.copy(MAP, self.map_copy)
        shutil.copy(JOURNEYS, self.j_copy)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, *args], capture_output=True, text=True, timeout=60
        )

    def test_trace_over_map_refused(self):
        before = snapshot(self.map_copy)
        r = self.run_tool(
            str(TOOLS / "run_journeys.py"),
            "--map", str(self.map_copy),
            "--journeys", str(self.j_copy),
            "--trace", str(self.map_copy),
        )
        self.assertNotEqual(r.returncode, 0, "runner must refuse (exit != 0)")
        self.assertIn("REFUSED", r.stdout + r.stderr)
        self.assertEqual(snapshot(self.map_copy), before, "Map must be byte-identical")

    def test_trace_over_journeys_refused(self):
        r = self.run_tool(
            str(TOOLS / "run_journeys.py"),
            "--map", str(self.map_copy),
            "--journeys", str(self.j_copy),
            "--trace", str(self.j_copy),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSED", r.stdout + r.stderr)

    def test_builder_output_on_input_file_refused(self):
        r = self.run_tool(
            str(TOOLS / "build_inspection_package.py"),
            "--map", str(self.map_copy),
            "--journeys", str(self.j_copy),
            "--output", str(self.map_copy),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSED", r.stdout + r.stderr)
        self.assertTrue(self.map_copy.exists())
        self.assertEqual(json.loads(self.map_copy.read_text())["id"], "example-workspace")

    def test_builder_output_dir_containing_inputs_refused(self):
        r = self.run_tool(
            str(TOOLS / "build_inspection_package.py"),
            "--map", str(self.map_copy),
            "--journeys", str(self.j_copy),
            "--output", str(self.dir),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSED", r.stdout + r.stderr)

    def test_clean_run_leaves_no_temp_files(self):
        r = self.run_tool(
            str(TOOLS / "run_journeys.py"),
            "--map", str(self.map_copy),
            "--journeys", str(self.j_copy),
            "--trace", str(self.dir / "ok-trace.json"),
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        leftovers = [p.name for p in self.dir.glob("*.tmp*")]
        self.assertEqual(leftovers, [], "atomic writes must clean up temp files")
        trace = json.loads((self.dir / "ok-trace.json").read_text())
        self.assertEqual(trace["mapId"], "example-workspace")


if __name__ == "__main__":
    unittest.main()
