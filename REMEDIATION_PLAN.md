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

- [ ] 0.1 Reproduce the audit's execution log on HEAD: validate, run, build on both fixtures; confirm byte-identical rebuild. Save the outputs as the regression baseline under `tests/baseline/`.
- [ ] 0.2 README: fix the builder command (single backslashes), refresh the "Project shape" file list, point "Next" at this plan, declare Python >= 3.9.
- [ ] 0.3 Convert `examples/member-create.journey.yaml` into a loadable JSON example; delete the YAML.
- [ ] 0.4 Remove `.hermes/plans/` from git.

**Accept:** every README command pastes and runs verbatim; no unloadable examples; `git grep -i hermes` is empty.

### Phase 1 — Unify validation (D1, D2, D4) — audit §5 step 1 (S–M)

- [ ] 1.1 New `tools/schema_lite.py` — vendored JSON-Schema subset validator (type, required, properties, items, enum, pattern, additionalProperties, minItems, `$defs`/`$ref`). No external dependency.
- [ ] 1.2 Fix schema drift so schemas describe reality:
  - `journey.schema.json` describes the **file** (array of journeys); steps gain `move.to`, `act.target`, `act.action`, `checkpoint.label` requirements where the subset validator allows, else they are enforced semantically; `expect` enum becomes `allowed|denied` only; `assert` removed from the enum until implemented; `comment` stays as a legal no-op.
  - `map.schema.json` allows `source`.
  - `trace.schema.json` matches what the runner actually emits today (Phase 3 then extends it with `runId`, `mapSha256`, timestamps).
- [ ] 1.3 Validator = schema gate first, then semantic checks; **collect-all-errors mode** (report every problem, never just the first); **never crashes** — catch-all converts any exception into a structured error (A10).
- [ ] 1.4 New semantic checks: journey `initial.role` must exist in `roles` (A05); step types must be known (A06); `act` needs an existing `target` and a known action (A03, A07, A09); `checkpoint` needs `label` (A08); permission subjects must carry the `role:` prefix (A11); duplicate journey ids rejected (A15); duplicate edges on the same node pair rejected (A13); empty journeys array warns (A14); declared-but-ungranted capability warns (A01); unknown `move` target already checked (A02 stays sound).
- [ ] 1.5 Runner and builder both call this one validator before doing anything (D2); the runner's private weak re-check is removed.

**Accept:** A03–A15 and A19 flip from silent to caught; A08–A11 become clean errors with zero tracebacks; the audit reproduction reruns clean.

### Phase 2 — Guard the Map (A23, invariant 1) — audit §5 step 2 (S)

- [ ] 2.1 Refuse when `--trace` (runner) or `--output` (builder) resolves to any input path (`--map`, `--journeys`, `--variables`), comparing resolved realpaths.
- [ ] 2.2 All file writes go through temp file + `os.replace` (atomic).

**Accept:** A23 refused with a clear message; a regression test lands in `tests/` (suite grows in Phase 5).

### Phase 3 — Provenance and Findings (D3, D7, D8) — audit §5 step 3 (S–M)

- [ ] 3.1 Trace header gains `runId` (UUID4), `timestamp` (UTC), `toolVersion`, `mapSha256`, `journeysSha256`; the schema's declared `mapVersion`/`runId` fields get populated for real.
- [ ] 3.2 Map and Journey documents gain optional `version`; the builder records the content hash in every Finding's `source`.
- [ ] 3.3 Finding taxonomy: `category` ∈ {under_permission, over_permission, missing_edge, spec_drift, unreachable}, rule-based `severity`, `confidence` field; the hardcoded `"medium"` dies (D8).
- [ ] 3.4 The dead `missing_edge` branch (A17) is repaired or removed; over-permission and under-permission produce distinct categories (A18).
- [ ] 3.5 Replace the self-map's vacuous `validate` denial evidence with a denial that actually distinguishes (D3).

**Accept:** two Map revisions with the same id are distinguishable in any Finding; A17/A18 produce distinct kinds; expected-denial evidence is no longer guaranteed-pass.

### Phase 4 — The package tells the truth (D5, D6, D9, D10) — audit §5 step 4 (S–M)

- [ ] 4.1 `links.json` is computed from step indices and event ordering (runner-derived), never substring matching; no default-to-start-node; duplicate journey ids are already rejected upstream (Phase 1). Fixes A15, A22, and the checkpoint mislinking.
- [ ] 4.2 `flowchart.mmd` and `pseudocode.txt` are generated from the supplied Map. `project_map_flow.py` keeps describing the pipeline itself, clearly labeled.
- [ ] 4.3 The builder verifies the Variable Matrix: every `definedIn.line` symbol check, every `usedBy` reference resolves; dangling refs become findings. The stale lines get regenerated (D9).
- [ ] 4.4 SELF_ASSESSMENT.md and README updated to post-remediation reality; stale claims corrected (D10).

**Accept:** viewer relationships equal runner relationships (conformance test lands in Phase 5); every package file means what the README says.

### Phase 5 — Tests + CI + map doctor (M) — audit §5 step 5

- [ ] 5.1 `tests/` — stdlib `unittest`; per-case ports of A01–A23 with the audit's ideal outcomes asserted; committed fixtures for every formerly-silent case.
- [ ] 5.2 Property test: seeded random Map/Journey generator proving "validator accepts ⟹ runner never crashes" (no Hypothesis).
- [ ] 5.3 `.github/workflows/validate.yml` — on PR: schema + semantic validation of all examples, journey runs, both package builds, full test suite, package artifacts uploaded, fail on new findings vs baseline.
- [ ] 5.4 `tools/map_doctor.py` — orphan nodes, unreachable-per-role, unused capabilities, edges without any permission, duplicate edges, dangling variable references; exit 1 on errors, warnings listed.

**Accept:** CI green on the repo itself; the doctor flags the A01/A13/A14 classes on any authored Map.

### Phase 6 — Quick wins (S each) — audit §5.1 / §5.4

- [ ] 6.1 Enforce `edge.requires` against role capabilities via a `roleCapabilities` mapping (A01, A12) — makes `capabilities` real.
- [ ] 6.2 Entry nodes and per-role start sets; a journey's `initial` node must be a legal entry for its role (A04 gets defined semantics).
- [ ] 6.3 Coverage metrics per run: node/edge/permission coverage per role, reachability per role, permission surface — new `coverage.json` in the trace and package ("what did the Journeys not test").
- [ ] 6.4 Parameterized capabilities: the action→relation vocabulary moves into the Map; the runner reads it from there (invariant 5); a fixture with an invented non-CRUD vocabulary proves it.

**Accept:** A12 denied; non-CRUD fixture runs; coverage answers "what was untested".

### Phase 7 — Depth features (M each) — audit §5.1 / §5.2 / §5.4

- [ ] 7.1 Negative assertions: `assert_unreachable` step (from node X as role R) via reachability search — Journeys become proofs of absence instead of fragile expected-denial scripts. *(The audit calls this the most differentiating addition.)*
- [ ] 7.2 Adapter contract: `adapters/` interface — `probe(role, node) -> {reachable, status}` and `act(role, action, target) -> {allowed, evidence}`; the runner compares adapter results to the Map's `expect` and writes both into the Trace. Invariant 2 guard: adapter observations flow only into Trace/Findings.
- [ ] 7.3 Data-driven Journeys: `matrix: {roles: [...], targets: [...]}` expands into concrete journeys before execution (expansion output is a Journey, never a Map edit).
- [ ] 7.4 Differential traces: `tools/diff_traces.py old new` regression report between Map revisions; trace replay against a different Map revision shows exactly what a change broke.
- [ ] 7.5 Conditional edges / guards (`when: {state: ...}`) consumed by the runner — deliberately last (medium invariant risk: state mutation must live in the Trace, never the Map).

**Accept:** defined per feature before build; each lands with its own tests and docs.

### Phase 8 — Close the audit's open items

- [ ] 8.1 Viewer audit (invariant 4): `viewer/index.html` renders packages without re-deriving relationships; a conformance test pins links.json ↔ viewer.
- [ ] 8.2 Adjacent-approach appendix (reachability/policy analysis, model-based testing) added to SELF_ASSESSMENT.md.
- [ ] 8.3 Full audit re-run: target 23/23 caught-or-sound, zero silent, zero tracebacks; byte-deterministic packages still hold.

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
