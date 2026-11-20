# Project Map — Remediation Plan

**Repo:** `HammazoneRecords/mindwave-project-map`
**Created:** 2026-11-20
**Source:** *MindWave Project Map: Independent Audit Report* (audit date 2026-11-17, commit audited `a3df262`). The full report lives outside the repo; its findings are summarized here so this file is self-contained.
**Baseline check (2026-11-20):** at HEAD `6ff5371` every code defect D1–D11 is still open. Verified directly: no tool reads `capabilities` (0 grep hits), no tool loads a schema, `severity: "medium"` is hardcoded at `build_inspection_package.py` L31, and the README builder command still breaks on paste at L112–115. Only a README clarity revision (PR #1) landed after the audited commit.

## Decisions locked (founder, 2026-11-20)

| Decision | Choice |
|---|---|
| Scope | **Full roadmap** — audit §5 fix sequence, plus quick wins, plus the M-effort features (negative assertions, adapter contract, journey matrix, conditional edges) |
| Tests & CI | **Suite + CI** — the audit's 23 adversarial cases become committed tests, a seeded fuzz property guards "validator accepts ⟹ runner never crashes", a GitHub Action validates every PR |
| Plan home | **This file**, repo root, updated as phases land |
| Start | Phases 0–2 begin immediately after this plan is committed |

Working defaults (reversible; flagged here when used):

- **Runtime stays stdlib-only.** No PyYAML, no `jsonschema`, no Hypothesis at runtime. Schema enforcement uses a vendored subset validator (`tools/schema_lite.py`); fuzzing uses a seeded generator instead of Hypothesis. Dev-only extras may later go in `requirements-dev.txt`.
- **Python floor: 3.9+** (the code uses `str.removeprefix`); declared in README.
- **The YAML example is replaced by a JSON example.** Stdlib-only wins over YAML support.
- **`.hermes/plans/` process residue is removed from git** (audit D11).
- Commits go to `main` (the repo's existing style), one commit per phase, pushed immediately.

## Ground rules — the 5 design invariants (from README)

1. A Journey can never silently rewrite the Map. **Today: violated** — audit A23 showed `--trace` pointing at the Map overwrites it with a Trace.
2. A Trace is not an automatic fact. **Today: safe** (nothing reads a Trace back); stays safe via `derivedFrom` provenance when adapters land (Phase 7.2).
3. Every Finding identifies the exact Map version and Journey. **Today: violated** — no Map hash or version anywhere (D7).
4. The visual skin reads the same model as the runner. **Today: insufficient evidence** — viewer not audited; `links.json` heuristics make divergence likely (D5).
5. Domain examples are replaceable. **Today: violated** — the `viewer/creator/editor/deleter` vocabulary is hardcoded in `run_journeys.py` L7.

## Findings index (audit, verified open 2026-11-20)

| ID | Severity | One line |
|---|---|---|
| D1 | High | Validator and runner enforce far less than the README claims — journey `initial.role`, `act` targets/actions, step types, checkpoint labels all unchecked; `capabilities`, `constraints`, `edge.requires` never read by any tool |
| D2 | High | Tools disagree: validator accepts what the runner crashes on (A08–A11); the runner never calls the validator |
| D3 | High | Expected-denial evidence is vacuous — typos pass as denials (`RELATION.get` fallback); the self-map's `validate` denial distinguishes nothing because nobody holds that relation |
| D4 | Medium | Schemas decorative and contradict fixtures — no `act.target`, `source` forbidden, journey described as object not array, `expect` enum drift (`pass`/`fail` vs `allowed`/`denied`), `assert`/`comment` silently scored as pass |
| D5 | Medium | `links.json` unreliable — checkpoints default to the start node, events matched by substring, duplicate journey ids merge |
| D6 | Medium | `flowchart.mmd` / `pseudocode.txt` are static constants describing the pipeline, not the supplied Map |
| D7 | Medium | No Map version/hash in Findings (violates invariant 3) |
| D8 | Medium | Finding model thin — hardcoded severity, one kind, dead `missing_edge` branch (A17), no committed fixture exercises the mismatch path |
| D9 | Low-Med | Variable Matrix stale and unchecked — 4/5 `definedIn` lines wrong, 1/6 `usedBy` references dangling; builder checks only `mapId` |
| D10 | Low | Doc drift — README file list and roadmap stale, self-assessment stale, unloadable YAML example |
| D11 | Low | Hygiene — no tests/CI, no declared Python version, `.hermes/plans/` residue |

The audit's adversarial cases A01–A23 are the acceptance suite. Target outcomes: **Caught** (rejected with a precise message), **Clean error** (no traceback), **Sound** (already correct and must stay correct: A02, A16, A20b).

## Phases

### Phase 0 — Baseline + hygiene (S) — audit §5 step 0

- [x] 0.1 Reproduce the audit's execution log on HEAD: validate, run, build on both fixtures; confirm byte-identical rebuild. Save the outputs as the regression baseline under `tests/baseline/`.
- [x] 0.2 README: fix the builder command (single backslashes), refresh the "Project shape" file list, point "Next" at this plan, declare Python >= 3.9.
- [x] 0.3 Convert `examples/member-create.journey.yaml` into a loadable JSON example; delete the YAML.
- [x] 0.4 Remove `.hermes/plans/` from git.

**Accept:** every README command pastes and runs verbatim; no unloadable examples; `git grep -i hermes` is empty.

### Phase 1 — Unify validation (D1, D2, D4) — audit §5 step 1 (S–M)

- [x] 1.1 New `tools/schema_lite.py` — vendored JSON-Schema subset validator (type, required, properties, items, enum, pattern, additionalProperties, minItems, `$defs`/`$ref`). No external dependency.
- [x] 1.2 Fix schema drift so schemas describe reality:
  - `journey.schema.json` describes the **file** (array of journeys); steps gain `move.to`, `act.target`, `act.action`, `checkpoint.label` requirements where the subset validator allows, else they are enforced semantically; `expect` enum becomes `allowed|denied` only; `assert` removed from the enum until implemented; `comment` stays as a legal no-op.
  - `map.schema.json` allows `source`.
  - `trace.schema.json` matches what the runner actually emits today (Phase 3 then extends it with `runId`, `mapSha256`, timestamps).
- [x] 1.3 Validator = schema gate first, then semantic checks; **collect-all-errors mode** (report every problem, never just the first); **never crashes** — catch-all converts any exception into a structured error (A10).
- [x] 1.4 New semantic checks: journey `initial.role` must exist in `roles` (A05); step types must be known (A06); `act` needs an existing `target` and a known action (A03, A07, A09); `checkpoint` needs `label` (A08); permission subjects must carry the `role:` prefix (A11); duplicate journey ids rejected (A15); duplicate edges on the same node pair rejected (A13); empty journeys array warns (A14); declared-but-ungranted capability warns (A01); unknown `move` target already checked (A02 stays sound).
- [x] 1.5 Runner and builder both call this one validator before doing anything (D2); the runner's private weak re-check is removed.

**Accept (met 2026-11-20):** A03–A15 and A19 flip from silent to caught; A08–A11 become clean errors with zero tracebacks; the audit reproduction reruns clean. Harness result: **16/16 cases match the audit's ideal outcomes** (`scripts/a_harness.py` pattern, committed as tests in Phase 5). A04 (entry nodes) and A12 (edge.requires enforcement) are deferred by design to Phase 6 — both now emit warnings instead of silence. D3's vacuous `validate` denial was fixed ahead of schedule (see 3.5) because the new unknown-action check correctly rejected the old fixture.

### Phase 2 — Guard the Map (A23, invariant 1) — audit §5 step 2 (S)

- [x] 2.1 Refuse when `--trace` (runner) or `--output` (builder) resolves to any input path (`--map`, `--journeys`, `--variables`), comparing resolved realpaths — including output directories that contain an input file.
- [x] 2.2 All file writes go through temp file + `os.replace` (atomic) — `tools/fsutils.py`, used by runner and builder.

**Accept (met 2026-11-20):** A23 refused with a clear message; regression tests committed in `tests/test_guard.py` (5 tests, all green).

### Phase 3 — Provenance and Findings (D3, D7, D8) — audit §5 step 3 (S–M)

- [x] 3.1 Trace header gains `runId` (UUID4), `timestamp` (UTC), `toolVersion`, `mapSha256`, `journeysSha256`; the schema's declared `mapVersion`/`runId` fields get populated for real.
- [x] 3.2 Map and Journey documents gain optional `version`; the builder records the content hash in every Finding's `source`.
- [x] 3.3 Finding taxonomy: `category` ∈ {under_permission, over_permission, missing_edge, spec_drift, unreachable}, rule-based `severity`, `confidence` field; the hardcoded `"medium"` dies (D8).
- [x] 3.4 The dead `missing_edge` branch (A17) is repaired or removed; over-permission and under-permission produce distinct categories (A18).
- [x] 3.5 Replace the self-map's vacuous `validate` denial evidence with a denial that actually distinguishes (D3). **Done early (2026-11-20, in Phase 1):** the fixture now denies `auditor` acting `create` on `self_assessment` — meaningful because `architect` holds that grant there; the unknown-action check would have rejected the old evidence anyway.

**Accept (met 2026-11-20):** two Map revisions with the same id are distinguishable in any Finding (content hash in `source.mapSha256`, plus `mapVersion` when declared); A17/A18 produce distinct kinds (missing_edge vs under/over_permission); expected-denial evidence is no longer guaranteed-pass. Trace events carry exact `node` references for Phase 4's links.

### Phase 4 — The package tells the truth (D5, D6, D9, D10) — audit §5 step 4 (S–M)

- [x] 4.1 `links.json` is computed from step indices and event ordering (runner-derived), never substring matching; no default-to-start-node; duplicate journey ids are already rejected upstream (Phase 1). Fixes A15, A22, and the checkpoint mislinking.
- [x] 4.2 `flowchart.mmd` and `pseudocode.txt` are generated from the supplied Map (`tools/map_derived.py`). `project_map_flow.py` keeps describing the pipeline itself, clearly labeled.
- [x] 4.3 The builder verifies the Variable Matrix (`tools/verify_variables.py`): every `definedIn`/`usedBy` file+line+symbol check, every `mapNodes` and `journeySteps` reference resolves; dangling refs become `spec_drift` findings. The stale lines were regenerated (D9).
- [x] 4.4 SELF_ASSESSMENT.md and README updated to post-remediation reality; stale claims corrected (D10).

**Accept (met 2026-11-20):** viewer relationships equal runner relationships (exact structured references; conformance test lands in Phase 5); every package file means what the README says. Note: a committed trace now contains volatile fields (runId/timestamp); determinism comparisons normalize those two fields and compare the rest byte-for-byte.

### Phase 5 — Tests + CI + map doctor (M) — audit §5 step 5

- [x] 5.1 `tests/` — stdlib `unittest`; per-case ports of A01–A23 with the audit's ideal outcomes asserted; committed fixtures for every formerly-silent case.
- [x] 5.2 Property test: seeded random Map/Journey generator proving "validator accepts ⟹ runner never crashes" (no Hypothesis).
- [x] 5.3 `.github/workflows/validate.yml` — on PR: schema + semantic validation of all examples, journey runs, both package builds, full test suite, package artifacts uploaded, fail on new findings vs baseline.
- [x] 5.4 `tools/map_doctor.py` — orphan nodes, unreachable-per-role, unused capabilities, edges without any permission, duplicate edges, dangling variable references; exit 1 on errors, warnings listed.

**Accept (met 2026-11-20, local):** suite green (34 tests: 23-case audit suite + property fuzz at 300 seeds + 5 guard tests + links/schema conformance); the doctor flags the A01/A13/A14 classes on any authored Map; CI defined — first cloud run happens on the next push.

### Phase 6 — Quick wins (S each) — audit §5.1 / §5.4

- [x] 6.1 Enforce `edge.requires` against role capabilities via a `roleCapabilities` mapping (A01, A12) — makes `capabilities` real.
- [x] 6.2 Entry nodes and per-role start sets; a journey's `initial` node must be a legal entry for its role (A04 gets defined semantics).
- [x] 6.3 Coverage metrics per run: node/edge/permission coverage per role, reachability per role, permission surface — new `coverage.json` in the trace and package ("what did the Journeys not test").
- [x] 6.4 Parameterized capabilities: the action→relation vocabulary moves into the Map; the runner reads it from there (invariant 5); a fixture with an invented non-CRUD vocabulary proves it.

**Accept (met 2026-11-20):** A12 denied (unit test + the brewery fixture's capability-gated walk); the non-CRUD brewery fixture (`examples/brewery.map.json`: brew/siphon/seal/taste → brewer/siphoner/sealer/taster) runs clean with no CRUD vocabulary anywhere; coverage reports untouched nodes, unused edges, unexercised permissions, and per-role reachability. Design note: `missing_edge` is advisory (severity low, category missing_edge) — it records structural gaps without failing the journey; only expectation mismatches and violated absence claims are fatal. The Variable Matrix was re-synced to the shifted line numbers (the Phase 4 verifier caught the drift itself).

### Phase 7 — Depth features (M each) — audit §5.1 / §5.2 / §5.4

- [x] 7.1 Negative assertions: `assert_unreachable` step (from node X as role R) via reachability search — Journeys become proofs of absence instead of fragile expected-denial scripts. *(The audit calls this the most differentiating addition.)*
- [x] 7.2 Adapter contract: `adapters/` interface — `probe(role, node) -> {reachable, status}` and `act(role, action, target) -> {allowed, evidence}`; the runner compares adapter results to the Map's `expect` and writes both into the Trace. Invariant 2 guard: adapter observations flow only into Trace/Findings.
- [x] 7.3 Data-driven Journeys: `matrix: {roles: [...], targets: [...]}` expands into concrete journeys before execution (expansion output is a Journey, never a Map edit).
- [x] 7.4 Differential traces: `tools/diff_traces.py old new` regression report between Map revisions; trace replay against a different Map revision shows exactly what a change broke.
- [x] 7.5 Conditional edges / guards (`when: {state: ...}`) consumed by the runner — deliberately last (medium invariant risk: state mutation must live in the Trace, never the Map).

**Accept (met 2026-11-20):** each feature landed with its own tests (10 Phase 7 cases) and docs in-file. Semantics defined before build: assert_unreachable = BFS over traversable edges (permission + requires + state guard) from the current position; a violated claim is fatal (category unreachable, severity high). Omitting `expect` means observational — the outcome is recorded, never asserted (matrix probes rely on this). Expansion ids are `{base}__{role}__{target}`, collision-checked at validation time. Adapter disagreements (`spec_drift`/medium/medium) compare the permission component for moves and the full decision for acts; a lying test adapter produces findings while the Map stays byte-identical. Conditional-edge state mutations are recorded in the trace event (`setState`) and never written back; a guard key no journey ever sets is warned as a dead guard.

### Phase 8 — Close the audit's open items

- [x] 8.1 Viewer audit (invariant 4): `viewer/index.html` renders packages without re-deriving relationships; a conformance test pins links.json ↔ viewer.
- [x] 8.2 Adjacent-approach appendix (reachability/policy analysis, model-based testing) added to SELF_ASSESSMENT.md.
- [x] 8.3 Full audit re-run: target 23/23 caught-or-sound, zero silent, zero tracebacks; byte-deterministic packages still hold.

**Accept (met 2026-11-20):** viewer consumes `links.json`/`findings.json` in package mode (highlights from exact coordinates, findings rendered with taxonomy pills), pinned by `tests/test_viewer_conformance.py` (4 tests incl. node `--check` JS parse and links-coordinate verification); adjacent-approaches appendix added; full re-run clean — all 4 fixtures valid, packages byte-deterministic modulo runId/timestamp, 52 tests green, zero tracebacks. FUTURE_UPDATES.md and HANDOFF.md refreshed to the post-remediation truth.

## Session mapping

| Session | Phases | Push point |
|---|---|---|
| 1 (2026-11-20) | 0, 1, 2 | after Phase 2 |
| 2 | 3, 4 | after Phase 4 |
| 3 | 5 | after CI green |
| 4 | 6 | after the non-CRUD fixture |
| 5+ | 7 (one feature per sitting), then 8 | per feature |

## Progress log

- 2026-11-20 — plan committed; baseline verified (all D1–D11 open at `6ff5371`).
- 2026-11-20 — **Phase 0 landed** (commit `70480a9`): baseline reproduction saved, README command/file list fixed, Python 3.9 declared, JSON example replaces YAML, `.hermes/` removed.
- 2026-11-20 — **Phases 1 + 2 landed in one commit** (deviation from one-commit-per-phase: the runner edit carries both the validation gate and the overwrite guard): new `schema_lite.py` + `vocabulary.py`, rewritten validator (collect-all-errors, never crashes), schemas describe reality, runner and builder gated, vacuous denial replaced, `fsutils.py` guard + atomic writes, 5 regression tests. Verification: all fixtures valid, `mindwavemine.trace.json` regenerates byte-identical, packages deterministic, 16/16 adversarial cases ideal, 5/5 unit tests. Remaining acceptance gap: A04/A12 warn instead of enforce (Phase 6), the 23-case suite + CI + doctor (Phase 5).
- 2026-11-20 — **Phase 3 landed** (commit `162149c`): trace provenance (runId/timestamp/toolVersion/mapSha256/journeysSha256), optional Map/Journey `version`, Finding taxonomy in `tools/findings.py` (category/severity/confidence by rule), A17 dead branch repaired, A18 distinct categories, trace events carry exact node references.
- 2026-11-20 — **Phase 4 landed**: exact `links.json` from structured trace nodes (D5), Map-derived `flowchart.mmd`/`pseudocode.txt` via `tools/map_derived.py` (D6), Variable Matrix verified reference-by-reference via `tools/verify_variables.py` and regenerated to current truth (D9), README + SELF_ASSESSMENT updated to post-remediation reality (D10). Deploy key for this repo registered (`mindwave-map-sandbox`) and stored in `skills/mindwave-deploy`; pushes unblocked.
- 2026-11-20 — **Phase 5 landed**: 23-case adversarial suite (`tests/test_audit_cases.py`, A01–A23; A04/A12 assert the interim warning behavior until Phase 6), seeded property test (`tests/test_property.py`, 300 seeds, clean/chaos generator modes), `tools/map_doctor.py` (orphans, unreachable-per-role, unused capabilities, untraversable edges, duplicate edges/nodes, dangling matrix refs, no-entry warning), `.github/workflows/validate.yml` (fixtures + doctor + runs + packages + suite + findings-vs-baseline gate + artifacts), baseline `tests/baseline/findings-count.txt` = 0. Suite: 34 tests green locally.
- 2026-11-20 — Phase 4 fix-up found by the new suite: `journeySteps` now also links checkpoint steps to the node where the trace resolved them (event index == step index), and the validator's interim no-entry warning is real.
- 2026-11-20 — **Phase 6 landed**: `edge.requires` enforced against `roleCapabilities` (A12, with denial reasons in mismatch findings), entry nodes + per-role start sets enforced (A04), coverage metrics in trace + `coverage.json` (nodes/edges/permissions/per-role reachability), map-level `vocabulary` replaces the default CRUD vocabulary (invariant 5) proven by `examples/brewery.*` (brew/siphon/seal/taste). Suite: 38 tests green. A04/A12 suite cases flipped from interim warnings to enforcement assertions.
- 2026-11-20 — **Phase 7 landed** (all five depth features in one sitting, one commit): `assert_unreachable` proofs of absence (7.1), `adapters/` contract + DeclarativeMapAdapter + Trace comparison with invariant-2 byte-pin (7.2), matrix journey expansion with collision-checked ids and observational probes (7.3), `tools/diff_traces.py` regression reports (7.4), conditional edges `when.state` with trace-resident state and dead-guard warnings (7.5). Suite: 48 tests green. Matrix re-synced; committed traces regenerated (toolVersion 1.2.0).
- 2026-11-20 — **Phase 8 landed — REMEDIATION COMPLETE**: viewer consumes runner-derived links.json/findings.json with conformance tests (8.1), adjacent-approaches appendix in SELF_ASSESSMENT (8.2), full re-run 23/23 ideal outcomes + byte-deterministic packages + 52 tests green (8.3). README file list/status, FUTURE_UPDATES.md ledger, and HANDOFF.md refreshed. Next: independent re-assessment + founder review.
