#!/usr/bin/env python3
"""Filesystem safety helpers shared by the Project Map tools.

Implements audit invariant 1 ("a Journey cannot silently rewrite the Map"):

- guard_output_against_inputs(): refuses any output path that collides with
  an input document — the audit's case A23 showed `--trace` pointed at the
  Map file would overwrite it with a Trace, no warning.
- atomic_write_text(): writes via a temp file in the same directory plus
  os.replace, so a crashed write can never leave a truncated artifact.
"""
from __future__ import annotations

import os
from pathlib import Path


def guard_output_against_inputs(output: Path | str, inputs: list[Path | str]) -> None:
    """Raise ValueError when an output path would overwrite an input document.

    A collision is: output resolves to an input file itself, OR output is a
    directory that contains an input file (building there could clobber it).
    """
    out = Path(output).resolve()
    for inp in inputs:
        p = Path(inp).resolve()
        if out == p:
            raise ValueError(
                f"REFUSED: output path '{output}' is the input file '{inp}'; "
                "a Trace, package, or export must never overwrite a Map or Journey (invariant 1)"
            )
        # refuse when an input file lives inside the output directory
        if str(p).startswith(str(out) + os.sep):
            raise ValueError(
                f"REFUSED: output directory '{output}' contains the input file '{inp}'; "
                "refusing to build a package over its own inputs (invariant 1)"
            )


def atomic_write_text(path: Path | str, text: str) -> None:
    """Write text atomically: temp file in the same dir, then os.replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".{target.name}.tmp-{os.getpid()}"
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()
