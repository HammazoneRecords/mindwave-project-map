# Project Map Self-Assessment

> use Project Map to examine Project Map. high-level first, then tunnel vision where the structure needs more light.

## Remediation status (2026-11-20)

The independent audit's Phases 0–4 have landed and are regression-tested. What this changes about the claims below:

- **Validator is real**: JSON Schema gate (vendored, dependency-free) + semantic checks, collect-all-errors, never crashes on malformed input.
- **Invariant 1 holds**: output paths that collide with input documents are refused; all writes are atomic.
- **Invariant 3 holds**: every Trace/Finding carries runId, timestamp, toolVersion, and the SHA-256 of the exact Map + Journey documents executed.
- **Findings have a taxonomy**: category ∈ {under_permission, over_permission, missing_edge, spec_drift, unreachable}, rule-based severity and confidence — no hardcoded "medium".
- **links.json is exact**: structured trace-event node references replace substring matching; no default-to-start-node.
- **flowchart.mmd / pseudocode.txt derive from the supplied Map**; the pipeline description lives separately in `project_map_flow.py`.
- **The Variable Matrix is verified**: every definedIn/usedBy reference, mapNode, and journeyStep is checked; stale references become spec_drift findings. The committed matrix was regenerated to match the current source.

Still open (tracked in REMEDIATION_PLAN.md): the full adversarial test suite + CI (Phase 5), entry nodes / edge.requires enforcement / coverage metrics / parameterized vocabulary (Phase 6), depth features (Phase 7), viewer conformance (Phase 8).

## Assessment input

- Map: `examples/project-map-self.map.json`
- Journeys: `examples/project-map-self.journeys.json`
- Trace: `examples/project-map-self.trace.json`
- Runner: `tools/run_journeys.py`
- Validator: `tools/validate_project_map.py`
- Package builder: `tools/build_inspection_package.py`
- Viewer: `viewer/index.html`

## What the Map says

```text
README → Formalization → Schemas → Examples → Validator → Runner
                                                    ↓
                                           Package Builder → Viewer

Future Updates ↔ Self-Assessment
Viewer → Self-Assessment
```

The project currently has four visible layers:

1. **Meaning** — README, formalization, terminology, and design documents.
2. **Contracts** — Map, Journey, Trace, and Finding schemas.
3. **Execution** — validator, Journey runner, flow exporter, and package builder.
4. **Inspection** — viewer, exported diagrams, and self-assessment traces.

## High-level Journey result

`self-high-level-audit` traversed:

```text
README
  → Formalization
  → Schemas
  → Examples
  → Validator
  → Runner
  → Package Builder
  → Viewer
```

Result: **PASS** — 8 events, no Findings.

This proves the declared high-level dependency path is internally traversable. It does not prove that every implementation file is complete or that the viewer has live product integration.

## Tunnel vision results

### Contract tunnel

`self-contract-tunnel` inspected:

```text
Schemas → Validator → Runner
```

It also attempted a create action as the `auditor` role and received the expected denial. The denial is meaningful because the `architect` role holds the same grant on that node — read-only audit is separated from write access, and the same act would be allowed for another role (audit D3, fixed).

Result: **PASS** — 5 events, expected denial preserved as evidence.

### Inspection tunnel

`self-inspection-tunnel` inspected:

```text
Package Builder → Viewer → Self-Assessment
```

Result: **PASS** — 3 events, no Findings.

This confirms the current inspection skin can be represented as part of the system it is inspecting, rather than being treated as an unexplained external surface.

## Implementation observations

### Strong points

- The core distinction remains stable: Map, Journey, Trace, and Finding are separate artifacts.
- The validator gates execution before the Journey runner is used.
- The combined package builder creates a portable inspection package.
- The viewer reads Map, Journey, and Trace data instead of hardcoding the project graph.
- The public core has a real MindWaveMine fixture and now a self-assessment fixture.
- Expected denials can be represented without turning them into runner failures.

### Current gaps exposed by the self-map

- The viewer has a generic room/product placeholder, not a live product adapter.
- The Variable Matrix is loaded by the generic viewer in `?fixture=self` mode and filters by selected Map node; the builder now verifies every reference in it (Phase 4).
- Source-code context is not yet linked to Journey steps or Findings.
- Journey steps can be selected, but full playback is not implemented.
- Findings are represented in the package contract with a rule-based taxonomy; the demo self-trace generates none because all expectations hold (a deliberate, verified outcome — mismatches and drift produce Findings in the committed regression tests).
- The self-map is hand-authored; a source scanner has not yet generated it from the repository.
- The package builder exports the variable matrix (with `--variables`), source references, links, and Map-derived flowchart/pseudocode; selected code context is not yet exported.

## Assessment boundary

This self-assessment proves:

- the architecture can describe itself;
- the declared high-level path can be traversed;
- narrow contract and inspection paths can be tested;
- the package can be generated from the self-map.

It does not prove:

- the entire repository is production-ready;
- every roadmap item is implemented;
- a live browser or API adapter works;
- the Variable Matrix is synchronized with current source;
- Pac-Man time travel is operational.

## Next tunnel

The next focused assessment should target the **linked inspection workspace**:

```text
Map node
  → Variable Matrix symbol
  → source range
  → pseudocode step
  → viewer surface
  → Journey event
  → Finding
```

That tunnel should be implemented and then assessed with a dedicated Journey before the 3D maze or live adapter is expanded.

## Appendix — adjacent approaches (Phase 8.2)

Where this model sits among neighboring techniques, and what each would add:

**Reachability / policy analysis.** The Map is already a labeled graph with per-role
traversal rules (viewer permission, `edge.requires` capability gates, conditional
state guards). `map_doctor.py` and the coverage report do per-role BFS reachability;
a dedicated policy-analysis pass would additionally check *global* properties — every
role can reach every node it must reach, no role can reach what policy forbids
(`assert_unreachable` journeys already encode the second class as tests), and
dead-end detection beyond single roles. This is the shortest path to treating Maps
as machine-checked policy documents rather than diagrams.

**Model-based testing.** Journeys are hand-authored today; the matrix journey
expansion is the first data-driven step. A model-based generator would walk the
Map graph automatically — enumerate shortest paths per role, generate probes for
every (role, capability, node) triple, and assert each generated Journey against
the declarative expectations. The existing suite (validator gate, trace schema,
seeded fuzz property) gives a generated Journey the same guarantees a hand-written
one gets, so the generator needs no new infrastructure.

**Property-based testing.** `tests/test_property.py` already proves the core
runtime property ("validator accepts ⟹ runner never crashes") with 300 seeded
random documents. A Hypothesis-style layer on top would grow targeted generators
(e.g. always-accepted maps, or maps with specific permission shapes) and shrink
failing cases to minimal documents. The seeded stdlib generator stays the runtime
default; property frameworks remain a dev-only extra.

**Differential testing.** `tools/diff_traces.py` compares two traces of the same
Map revision family and reports regressions, fixes, finding deltas, and coverage
loss — the Pac-Man time travel comparison loop, headless. Its natural extension is
replaying the same Journeys against a proposed Map revision in CI and blocking the
merge on any pass→fail regression, which is exactly the comparison the
project_map_flow pipeline diagram describes.

**Mutation-style Map testing.** The negation of the seeded fuzz: apply small
mutations to a valid Map (drop a permission, add a wrong edge, tighten a
capability) and assert that some committed Journey *fails* for the right reason.
A Map that no Journey notices being broken is under-tested; mutation analysis
would measure exactly that gap from the existing coverage report.
