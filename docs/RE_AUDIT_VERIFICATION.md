# Independent Re-Audit — Claim Verification Report

**Repo:** `HammazoneRecords/mindwave-project-map`
**Audited state:** `891c636` (phase 8, "REMEDIATION COMPLETE")
**Post-fix state:** `a2b493b`
**Date:** 2026-11-20
**Method:** three independent passes — (1) remediation implemented in phases 0–8; (2) a separate AI agent performed a cold adversarial assessment with its own fixtures and 24 novel attacks, trusting nothing; (3) every claim the agent made was independently fact-checked by reproducing it (several agent claims were re-verified with corrected fixtures after initial reproductions were confounded).

---

## 1. What the re-audit confirmed (independently reproduced)

| Area | Result |
|---|---|
| Adversarial cases A01–A23 | **23/23** matched the audit's ideal outcomes — the agent rebuilt every case from scratch with its own fixture set (`clerkdom-map`), no reuse of committed tests |
| Test suite | **52/52 green** at `891c636`; agent judged the suite "not vacuous" (real CLI subprocesses, exact message assertions, anti-vacuousness guard on the fuzz) |
| Invariant 1 (no silent Map rewrites) | **HOLDS** — direct, symlink, `..`, parent-dir, hardlink, and symlink-in-output attacks all refused or harmless |
| Invariant 2 (adapter observations → Trace only) | **HOLDS** — lying adapter produced findings while the Map stayed byte-identical |
| Invariant 3 (Findings pin Map content) | **HOLDS** — same-id Map revisions distinguishable via `mapSha256`; findings schema-conformant |
| Invariant 4 (skin reads the runner's model) | **PARTIAL** — package mode exact; standalone fallback heuristics unlabeled (fixed, see L6) |
| Invariant 5 (domain replaceable) | **HOLDS** — brewery (brew/siphon/seal/taste) runs with zero CRUD vocabulary |
| Package determinism | **VERIFIED** — 9 files byte-identical across builds, modulo runId/timestamp |
| No hardcoded severity | **VERIFIED** — severities come from the rules table only |
| README commands | **VERIFIED** — all 5 paste-and-run verbatim |
| Variable Matrix verification | **VERIFIED** — forged stale matrices (line 99999, ghost node, ghost journey) all become spec_drift findings |

## 2. Claims fact-checked and corrected

All **9 defect claims** were confirmed by reproduction (two initially failed to reproduce because the fact-checker's own fixtures were confounded; clean reproductions confirmed them). One agent claim was **rejected as described**: the builder's deep-nesting crash (`M3a`) reproduced as a traceback only with a *valid* deep map — with an invalid one the builder already errored cleanly. The diagnosis (RecursionError escaping the builder's `except` clause) was nevertheless correct and fixed.

| Agent claim | Fact-check verdict |
|---|---|
| H1 builder × matrix: `KeyError 'steps'`, half-written package | **CONFIRMED** (exit 2, 5/9 files) |
| M1 matrix traces violate trace.schema (`expandedJourneys`) | **CONFIRMED** (`unexpected field 'expandedJourneys'`) |
| M2 doctor/coverage diverge from effective vocabulary + traversal | **CONFIRMED** (false `view` warning with remapped vocabulary; code review confirms hardcoded table) |
| M3a builder RecursionError traceback | **CONFIRMED** (with a valid deep map: exit 1 + traceback) |
| M3b diff_traces TypeError on `runId: null` | **CONFIRMED** (exit 1 + traceback) |
| L1 schema_lite `$` accepts `id: "evil-id\n"` | **CONFIRMED** (validator exit 0 on clean repro) |
| L2 `assert_unreachable` self-target fabricates "confirmed unreachable" | **CONFIRMED** (exact text reproduced) |
| L3 empty `steps: []` vacuous pass | **CONFIRMED** (validator 0, runner "PASS (0 events)") |
| L4 matrix expansion bypasses entry enforcement | **CONFIRMED** (validator 0, runner 0 on entry-violating expansion) |
| SELF_ASSESSMENT "Still open" block stale | **CONFIRMED** (falsifies plan 4.4 as of `891c636`) |
| FUTURE_UPDATES stale checkboxes | **CONFIRMED** (done-work lines still `[ ]`, incl. duplicated entries) |
| README omits `project_map_flow.py` | **CONFIRMED** (0 hits) |
| `hermes` grep non-empty | **CONFIRMED** (trivially — 5 hits, all REMEDIATION_PLAN.md self-references; repo itself clean) |
| CI misses brewery fixture; findings gate single-package | **CONFIRMED** (CI predates the brewery fixture) |
| HANDOFF "public leak checks" claim has no artifact | **CONFIRMED** (unverifiable) |
| NA3 duplicate JSON keys last-win | **CONFIRMED** (stdlib behavior; accepted wart) |
| NA22 declarative adapter produces no spurious disagreements | **CONFIRMED** (comparison is permission-component-only, as designed) |

## 3. Defects → fixes (all landed in `a2b493b`)

| ID | Severity | Fix | Regression pin |
|---|---|---|---|
| H1 | High | `build_links` consumes expanded journeys; builder completes all 9 files on matrix journeys | `test_h1_builder_handles_matrix_journeys` |
| M1 | Medium | trace.schema declares `expandedJourneys`; `events` items typed | `test_m1_matrix_trace_conforms_to_trace_schema` |
| M2 | Medium | doctor + coverage use `effective_vocabulary` and runner-mirroring traversal (requires/when-state); unused `roleCapabilities` grants flagged | `test_m2_doctor_uses_effective_vocabulary`, `test_na4_unused_capability_grant_warns` |
| M3 | Medium | builder catches `RecursionError` (clean INVALID); diff_traces validates inputs and wraps its report | `test_m3a_builder_survives_deep_nesting_with_clean_error`, `test_m3b_diff_traces_survives_null_runid` |
| L1 | Low | schema_lite re-anchors trailing `$` to `\Z` (ECMA-262 end-of-string semantics) | `test_l1_trailing_newline_id_rejected` |
| L2 | Low | vacuous absence claims recorded as `assert_unreachable_vacuous` (spec_drift/low) with honest event text | `test_l2_vacuous_absence_claim_recorded_honestly` |
| L3 | Low | zero-step journeys warn | `test_l3_empty_steps_warns` |
| L4 | Low | matrix expansions entry-checked per role | `test_l4_matrix_expansion_entry_enforced` |
| L6/L7/L8 | Low | viewer HTML-escapes titles/ids; docs de-staled; CI covers brewery and gates both packages | viewer conformance suite re-run |

## 4. Accepted warts (documented, deliberately not "fixed")

- Duplicate JSON keys: stdlib last-wins, undetected (would need an `object_pairs_hook`; cosmetic today).
- A step's `set` applies before that step's own edge guard — a step can unlock the edge it walks (documented order of evaluation).
- Package `map.json` is a re-serialization; provenance hashes pin the *original* input bytes (re-running on the package's own copy yields a different hash than recorded — the hash answers "what was executed", not "what was packaged").
- Mermaid node ids are not escaped (a hostile id can break `flowchart.mmd` rendering).
- The property fuzz does not generate Phase 7 constructs (matrix/entry/vocabulary/adapters); they are covered by dedicated unit tests and the re-audit pins instead.
- `assert_unreachable`'s movement relation `"viewer"` is a reserved model-level name (undocumented convention).

## 5. Final state

- Commits: `70480a9` (phase 0) → `a9e1a98` (1+2) → `162149c` (3) → `28a5def` (4) → `e6b5ebe` (5) → `8b10346` (6) → `d761967` (7) → `891c636` (8) → `a2b493b` (re-audit remediation), all pushed to `origin/main`.
- Tests: **62/62 green** (42 audit-case + 10 re-audit pins + 5 guards + 1 property fuzz ×300 seeds + 4 viewer conformance).
- Matrix: zero drift. Traces regenerated at toolVersion 1.2.0. CI gates 4 fixtures × validate/doctor/run/build + findings-vs-baseline (mindwavemine + brewery).

## 6. Overall verdict

The original remediation was real: everything it tested held under independent adversarial attack. The re-audit proved exactly where the phrase "REMEDIATION COMPLETE" had been earned only on tested surface — the matrix feature was two-thirds shipped (runner yes, builder/schema no), and the doctor could reassure authors with false statements on non-CRUD maps. Both classes are now fixed, pinned by regression tests, and the docs no longer claim more than the artifacts show. Remaining risk concentrates in the fuzz generator's blind spots, which are explicit and enumerated above.
