# MindWave Project Map


A project intelligence and validation tool built to make my complex software projects easier to understand, map, inspect, and validate. 
Connects project structure, expected workflows, execution traces, and findings to identify gaps between intended and actual implementation.

It separates four things I find that usually get tangled together:

- **Map** — the declared facts: nodes, relationships, roles, capabilities, states, and constraints.
- **Journey** — an executable test or steering path through the Map.
- **Trace** — the evidence produced when a Journey runs.
- **Finding** — a meaningful difference between what the Map says and what the Journey exposes.

The maze is only one possible skin. The core can run headlessly, in CI, from a CLI, or through a visual graph.

## Why this exists

A project can have pages, routes, permissions, and actions that look complete while the actual paths between them are broken, unreachable, over-permissioned, or never tested.

Project Map makes the structure explicit. Journeys make the structure walkable. Traces make the result inspectable.

> the map tells us what is there. the journey shows us what happens when we move through it.

## Formal model

```text
Map      = facts
Journey  = test / steer
Trace    = observed execution
Finding  = diagnosed gap, risk, or mismatch

Map + Journey → Trace → Findings
```

## Repository status

This repository is the public foundation for the architecture. It is intentionally domain-neutral. It does not contain private business material, private project data, credentials, or product-specific canon.

The first release establishes the vocabulary, schema direction, example Map, and Journey model. Runtime adapters and visual skins can be added without changing the distinction between facts and traversal.

**Requirements:** Python >= 3.9 (the tools use `str.removeprefix`). No third-party runtime dependencies — the tools run on the standard library alone.

An independent audit (2026-11-17) found the tools enforce less than this README claims and produced a prioritized remediation plan. The work is tracked in [REMEDIATION_PLAN.md](./REMEDIATION_PLAN.md); until a phase lands there, treat the tool claims below as describing intent, not verified guarantees.

## Project shape

```text
tools/
  validate_project_map.py     # schema + semantic validation, precise errors
  run_journeys.py             # executes Journeys against a Map, writes a Trace
  build_inspection_package.py # validate + run + export one portable package
  project_map_flow.py         # exports the Project Map pipeline's own flowchart/pseudocode
spec/
  map.schema.json             # declarative Map format
  journey.schema.json         # executable Journey format
  trace.schema.json           # Trace format
  finding.schema.json         # Finding format
  variable.schema.json        # Variable Matrix format
examples/
  workspace.map.json                  # small generic project map
  member-create.journey.json          # generic example Journey
  mindwavemine.map.json               # real fixture: MindWaveMine R&D Interface
  mindwavemine.journeys.json
  mindwavemine.trace.json
  project-map-self.map.json           # the repository maps itself
  project-map-self.journeys.json
  project-map-self.trace.json
  project-map-self.variables.json
viewer/
  index.html                  # static inspection viewer for built packages
formalization/
  PROJECT_MAP.md              # architecture and invariants
  TERMINOLOGY.md              # stable language
docs/                         # self-assessment, flow docs, skin inventory
tests/                        # baseline reproduction + regression tests
LICENSE
README.md
```

## invariants

1. A Journey cannot silently rewrite the Map.
2. A Trace records what happened; it does not become a new fact automatically.
3. Findings must identify the Map version and Journey that produced them.
4. A visual skin must read from the same Map and Journey model as the headless runner.
5. Domain examples remain replaceable. The architecture must not depend on one company's vocabulary.

## License

MIT. See [LICENSE](./LICENSE).

## First real test project

The first external test surface is the public [MindWaveMine R&D Interface](https://github.com/HammazoneRecords/MindWaveMine-R-D-Interface).

It is a real React + FastAPI interface with multiple views, workflows, ingestion paths, fabrication actions, handoff steps, and a persisted local data model. It gives Project Map something real to describe and traverse without putting project-specific implementation inside this core repository.

The integration boundary is:

```text
MindWaveMine R&D Interface → adapter / Map → Journeys → Traces → Findings
```

The interface remains its own repository. This repository owns the generic Map/Journey model and the adapter or fixture that describes the test surface.

## Validate before running

The public demo now has a dependency-free validator:

```bash
python3 tools/validate_project_map.py \
  --map examples/mindwavemine.map.json \
  --journeys examples/mindwavemine.journeys.json
```

It checks required fields, duplicate nodes, broken edge references, unknown roles, unknown permission targets, Journey/Map identity, initial nodes, and Journey move targets before execution.


The repository includes a Map and three executable Journeys for the MindWaveMine R&D Interface:

```bash
python3 tools/run_journeys.py \
  --map examples/mindwavemine.map.json \
  --journeys examples/mindwavemine.journeys.json \
  --trace examples/mindwavemine.trace.json
```

The runner currently proves the declarative layer: allowed and denied movement, role permissions, checkpoints, and portable Trace output. It does not yet enforce declared `capabilities` or `edge.requires` (tracked in the remediation plan, Phase 6), and it does not pretend to be a live browser/API adapter. The next adapter will connect these Journeys to the actual R&D Interface endpoints and UI paths.

## Build a portable inspection package

Use the combined CLI to validate the Map and Journeys, execute every Journey, and export one self-contained inspection package:

```bash
python3 tools/build_inspection_package.py \
  --map examples/mindwavemine.map.json \
  --journeys examples/mindwavemine.journeys.json \
  --output build/mindwavemine-inspection
```

The output directory contains `map.json`, `journeys.json`, `trace.json`, `findings.json`, `links.json`, optional `variables.json`, `source-reference.md`, `flowchart.mmd`, and `pseudocode.txt`. `links.json` preserves shared Map-node → Journey-step → Trace-event relationships for linked viewers. The command exits non-zero when validation fails or a Journey fails. This is a declarative fixture runner and package exporter; it is not a live browser/API adapter or visualizer.

## Self-assessment

Project Map now maps and journeys its own repository. Run the high-level and tunnel-vision assessment with:

```bash
python3 tools/validate_project_map.py \
  --map examples/project-map-self.map.json \
  --journeys examples/project-map-self.journeys.json
python3 tools/build_inspection_package.py \
  --map examples/project-map-self.map.json \
  --journeys examples/project-map-self.journeys.json \
  --variables examples/project-map-self.variables.json \
  --output ./self-inspection
```

Read the observations in [`docs/SELF_ASSESSMENT.md`](./docs/SELF_ASSESSMENT.md). The assessment names what the current implementation proves and what remains a gap; it does not promote the roadmap into completed functionality.

I built MindWave Project Map to give myself a more structured way to understand project architecture, workflows, implementation and gaps between expected and actual behaviour.

As I developed it, I started wondering whether other developers experience the same problem. I'm sharing it to get honest technical feedback, understand whether the problem is common, and find out where the approach could be improved.
