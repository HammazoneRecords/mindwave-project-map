#!/usr/bin/env python3
"""diff_traces.py — differential trace report (Phase 7.4).

Compares two Traces (typically from two revisions of the same Map) and
answers: what did the change break?

    python3 tools/diff_traces.py old-trace.json new-trace.json

Reported per journey id:
  - pass -> fail          (REGRESSION)
  - fail -> pass          (fixed)
  - findings added / resolved (matched by kind + step)
  - journeys added / removed
Plus a coverage delta (newly-untouched nodes = things the Journeys no longer test)
and a provenance mismatch note when the two traces ran different Map content.

Exit codes: 0 no regressions, 1 at least one regression, 2 unreadable input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_trace(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read trace '{path}': {e}")
        sys.exit(2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("old")
    ap.add_argument("new")
    args = ap.parse_args()

    old, new = load_trace(args.old), load_trace(args.new)
    regressions = 0

    old_by_id = {r["journeyId"]: r for r in old.get("journeys", [])}
    new_by_id = {r["journeyId"]: r for r in new.get("journeys", [])}

    print(f"old: mapId={old.get('mapId')} mapSha256={str(old.get('mapSha256'))[:12]}… runId={old.get('runId', '?')[:8]}…")
    print(f"new: mapId={new.get('mapId')} mapSha256={str(new.get('mapSha256'))[:12]}… runId={new.get('runId', '?')[:8]}…")
    if old.get("mapSha256") and new.get("mapSha256") and old["mapSha256"] != new["mapSha256"]:
        print("NOTE: traces executed different Map content (sha256 differs)")
    elif old.get("mapId") != new.get("mapId"):
        print(f"WARNING: different maps ({old.get('mapId')} vs {new.get('mapId')}); deltas below may be meaningless")

    def findings_signature(result):
        return {(f["kind"], f.get("step")) for f in result.get("findings", [])}

    for jid in sorted(set(old_by_id) | set(new_by_id)):
        o, n = old_by_id.get(jid), new_by_id.get(jid)
        if o is None:
            print(f"ADDED   {jid}: new journey in the new trace ({len(n.get('events', []))} events)")
            continue
        if n is None:
            print(f"REMOVED {jid}: journey no longer in the new trace")
            continue
        o_pass, n_pass = o["passed"], n["passed"]
        if o_pass and not n_pass:
            print(f"REGRESSION {jid}: pass -> fail")
            for f in sorted(findings_signature(n) - findings_signature(o)):
                print(f"          new finding: {f[0]} @ step {f[1]}")
            regressions += 1
        elif not o_pass and n_pass:
            print(f"FIXED      {jid}: fail -> pass")
            for f in sorted(findings_signature(o) - findings_signature(n)):
                print(f"          resolved finding: {f[0]} @ step {f[1]}")
        else:
            delta = findings_signature(n) - findings_signature(o)
            if delta:
                print(f"CHANGED    {jid}: still {'fail' if not n_pass else 'pass'}, new findings:")
                for f in sorted(delta):
                    print(f"          new finding: {f[0]} @ step {f[1]}")
                if not n_pass:
                    regressions += 1

    oc = old.get("coverage") or {}
    nc = new.get("coverage") or {}
    if oc and nc:
        newly_untouched = sorted(set(nc["nodes"]["untouched"]) - set(oc["nodes"]["untouched"]))
        newly_touched = sorted(set(oc["nodes"]["untouched"]) - set(nc["nodes"]["untouched"]))
        if newly_untouched:
            print(f"COVERAGE now untested: {', '.join(newly_untouched)}")
            regressions += 0  # coverage loss is reported, not fatal
        if newly_touched:
            print(f"COVERAGE now tested:  {', '.join(newly_touched)}")

    print(f"REGRESSIONS {regressions}")
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
