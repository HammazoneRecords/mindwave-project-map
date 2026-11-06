# Future Updates

> we are not guessing the finish line. we keep the updates visible, check them off when the work is real, and leave the unfinished parts named.

## Current release surface

- [x] Create the public `MindWave Project Map` repository.
- [x] Apply MindWave branding to the public foundation.
- [x] Formalize the core distinction: **Map = facts**.
- [x] Formalize the core distinction: **Journey = test / steer**.
- [x] Define **Trace = evidence**.
- [x] Define **Finding = issue / mismatch**.
- [x] Add the Map schema.
- [x] Add the Journey schema.
- [x] Add a generic example Map.
- [x] Add a real MindWaveMine Map.
- [x] Add real MindWaveMine Journeys.
- [x] Add the first headless Journey runner.
- [x] Generate and commit the first MindWaveMine Trace.
- [x] Add the branded landing-page generation prompt.
- [x] Add dependency-free Map and Journey validation.
- [x] Add formal Trace and Finding schema files.
- [x] Map Project Map against itself with high-level and tunnel-vision Journeys.
- [x] Record self-assessment observations and implementation boundaries.
- [x] Add linked `links.json` and `source-reference.md` to inspection packages.

## Next build — make the model stronger

- [ ] Validate every Map against `spec/map.schema.json`.
- [ ] Validate every Journey against `spec/journey.schema.json`.
- [ ] Add clear validation errors with file path, record, and reason.
- [x] Add a test command that runs validation and Journeys together.
- [ ] Add a formal Trace schema.
- [ ] Add a formal Finding schema.
- [ ] Separate expected denials from unexpected failures in the output.
- [x] Add Journey result summaries that a person can read quickly.
- [x] Add exit codes for CI use.

## MindWaveMine live adapter

- [ ] Inspect the actual frontend routes and navigation behavior.
- [ ] Inspect the FastAPI endpoint surface.
- [ ] Define the adapter boundary without copying MindWaveMine into this repo.
- [ ] Add a live health-check Journey against the running API.
- [ ] Add a live workspace-status Journey.
- [ ] Add a live concept-fabrication Journey in safe dry-run mode.
- [ ] Add a live ingestion Journey using a disposable fixture.
- [ ] Add a live reports Journey.
- [ ] Add a live handoff Journey without changing production data.
- [ ] Record live Traces separately from declarative Traces.
- [ ] Mark every live result with target URL, commit, and run time.

## Visualizer

- [ ] Build a generic graph view from any Map file.
- [ ] Render nodes and edges from Map data rather than hardcoded project names.
- [ ] Show role-specific reachable paths.
- [ ] Show allowed paths and denied paths with different visual states.
- [ ] Load a Journey into the visualizer.
- [ ] Play a Journey step by step.
- [ ] Show the Trace as a route through the Map.
- [ ] Show Findings beside the affected node or edge.
- [ ] Add the MindWaveMine Map as the first built-in visualizer scene.
- [ ] Add a replaceable user Map upload or file-loading path.
- [ ] Add the 3D maze skin after the graph view is stable.

## CLI and developer use

- [ ] Add `project-map validate`.
- [ ] Add `project-map journey run`.
- [ ] Add `project-map trace inspect`.
- [ ] Add `project-map findings list`.
- [ ] Add `project-map map inspect`.
- [ ] Add a generated starter Map command.
- [ ] Add a generated starter Journey command.
- [ ] Document how to map a new project.
- [ ] Document how to write a Journey.
- [ ] Document how to write an adapter.

## Open-source launch surface

- [ ] Add contribution guidelines.
- [ ] Add a code of conduct.
- [ ] Add issue templates for Maps, Journeys, adapters, and visualizer findings.
- [ ] Add a changelog.
- [ ] Add CI for schema validation and Journey execution.
- [ ] Add a public demo command that works from a fresh clone.
- [ ] Add the landing page.
- [ ] Replace placeholder repository and documentation links.
- [ ] Publish the first tagged release.
- [ ] Write the first release notes in the project voice.

## Design rules to keep visible

- [ ] Keep the Map separate from the Journey.
- [ ] Keep the Journey separate from the Trace.
- [ ] Keep the Trace separate from the Finding.
- [ ] Do not let a visual skin become the source of truth.
- [ ] Do not copy private project code into the public core.
- [ ] Do not call a fixture a live integration.
- [ ] Do not call a passing Journey proof that the whole project is correct.
- [ ] Record what the test proves and what it does not prove.

## Check-off rule

Only mark an item `[x]` after the artifact exists and the result has been exercised or independently verified. If the work is drafted but not run, leave it unchecked and name the blocker below.

## Current blockers / decisions

- Live adapter target and safe execution mode still need to be defined.
- Visualizer implementation has not started.
- The landing page is specified but not built.

## Full route — from Map to Pac-Man Time Travel

This is the complete path from the current public foundation to the full change-impact system. The route stays ordered: facts first, then traversal, then evidence, then visual steering, then before/after simulation.

### Phase 1 — Make the contracts executable

- [ ] Validate every Map against `spec/map.schema.json`.
- [ ] Validate every Journey against `spec/journey.schema.json`.
- [ ] Add clear validation errors with file path, record, and reason.
- [ ] Add a formal `spec/trace.schema.json`.
- [ ] Add a formal `spec/finding.schema.json`.
- [ ] Add stable IDs to Map nodes, edges, roles, capabilities, Journeys, Traces, and Findings.
- [ ] Add Map version and source commit metadata to every Trace.
- [ ] Add Journey version metadata to every Trace.
- [ ] Define the difference between `expected_denial`, `unexpected_denial`, `broken_edge`, `missing_capability`, and `security_regression`.
- [ ] Add deterministic timestamps or run IDs so Traces can be compared.
- [ ] Add a single test command for validation plus Journey execution.
- [ ] Add exit codes for CI use.

### Phase 2 — Build the headless engine

- [ ] Separate Map loading from Journey execution.
- [ ] Separate permission evaluation from traversal.
- [ ] Add a graph traversal service that supports directed and undirected edges.
- [ ] Add role switching as an explicit Journey step.
- [ ] Add state changes as explicit Journey steps.
- [ ] Add assertions for node reachability.
- [ ] Add assertions for capability access.
- [ ] Add assertions for expected state.
- [ ] Add checkpoints that survive replay.
- [ ] Emit portable Trace JSON.
- [ ] Derive Findings from failed assertions and unexpected transitions.
- [ ] Add stable result summaries for people.
- [ ] Add replayable deterministic runs.

### Phase 3 — CLI and project onboarding

- [ ] Add `project-map validate`.
- [ ] Add `project-map map inspect`.
- [ ] Add `project-map journey run`.
- [ ] Add `project-map trace inspect`.
- [ ] Add `project-map findings list`.
- [ ] Add `project-map map stats`.
- [ ] Add a generated starter Map command.
- [ ] Add a generated starter Journey command.
- [ ] Add a project mapping guide.
- [ ] Add a Journey authoring guide.
- [ ] Add an adapter authoring guide.
- [ ] Add a fresh-clone demo command.
- [ ] Make the built-in MindWaveMine example run with one command.

### Phase 4 — MindWaveMine live adapter

- [ ] Inspect the actual frontend routes and navigation behavior.
- [ ] Inspect the FastAPI endpoint surface.
- [ ] Define the adapter boundary without copying project code into the core.
- [ ] Add a target configuration with URL, commit, and environment label.
- [ ] Add a live health-check Journey against the running API.
- [ ] Add a live workspace-status Journey.
- [ ] Add a live dashboard Journey.
- [ ] Add a live reports Journey.
- [ ] Add a reviewer read-only Journey.
- [ ] Add a concept-fabrication Journey in safe dry-run mode.
- [ ] Add an ingestion Journey using a disposable fixture.
- [ ] Add a handoff Journey without changing production data.
- [ ] Record live Traces separately from declarative Traces.
- [ ] Mark every live result with target URL, commit, run time, and safety mode.
- [ ] Add a live-vs-declared comparison report.

- [ ] Add click-linked selection context across Map, Variable Matrix, room/product view, pseudocode, source, Trace, and Findings.
- [ ] Make a clicked Variable Matrix row move the center viewport to the related room or product screen.
- [ ] Highlight related Map paths and pseudocode/source ranges on selection.
- [ ] Add room mode, product mode, code mode, Journey mode, and time-travel mode.
- [x] Add the linked inspection package export for users.
- [ ] Keep source references tied to a commit or snapshot.

### Phase 5 — Generic graph visualizer

- [x] Build a graph view from any Map file.
- [x] Render nodes and edges from Map data rather than hardcoded project names.
- [x] Show node type, state, and metadata.
- [x] Show role-specific reachable paths.
- [x] Show allowed paths and denied paths with different visual states.
- [x] Load a Journey into the visualizer.
- [ ] Play a Journey step by step.
- [x] Show the Trace as a route through the Map.
- [x] Show Findings beside the affected node or edge.
- [ ] Filter by role, node type, edge type, and Finding kind.
- [ ] Add keyboard navigation and accessible text output.
- [ ] Add the MindWaveMine Map as the first built-in visualizer scene.
- [ ] Add replaceable user Map loading.
- [ ] Add downloadable SVG and JSON output.

### Phase 6 — Pac-Man skin

- [ ] Define the Pac-Man avatar as a role-bound Journey actor.
- [ ] Map nodes to cells.
- [ ] Map edges to traversable paths.
- [ ] Map capabilities to pellets.
- [ ] Map denied capabilities to visible grey pellets.
- [ ] Map permission boundaries to walls or gates.
- [ ] Map Findings to visible warnings.
- [ ] Add turn-based movement.
- [ ] Add role switching.
- [ ] Add allowed and denied movement feedback.
- [ ] Add action execution from the HUD.
- [ ] Add audit events for every move, denial, action, and checkpoint.
- [ ] Add Journey playback inside the maze.
- [ ] Add Trace replay inside the maze.
- [ ] Keep the Map as the source of truth beneath the skin.

### Phase 7 — Ghost mode

- [ ] Support multiple actors on the same Map.
- [ ] Assign each actor a role and Journey.
- [ ] Render simultaneous paths.
- [ ] Detect shared-node collisions.
- [ ] Detect shared-capability collisions.
- [ ] Detect role overlap and bottlenecks.
- [ ] Detect pages reachable by nobody.
- [ ] Detect actions available to nobody.
- [ ] Produce multi-role Trace output.
- [ ] Produce findings for conflicts, bottlenecks, and orphaned surfaces.
- [ ] Add synchronized playback.
- [ ] Add comparison by role.

### Phase 8 — Map health and audit intelligence

- [ ] Calculate orphan rate.
- [ ] Calculate dead-end rate.
- [ ] Calculate permission denial rate.
- [ ] Calculate forbidden attempt rate.
- [ ] Calculate dead capability rate.
- [ ] Calculate onboarding drop-off concentration.
- [ ] Calculate bridge rate between Map versions.
- [ ] Calculate growth rate between Map versions.
- [ ] Classify orphan patterns as scattered, clustered, or layered.
- [ ] Generate a human-readable audit report.
- [ ] Export JSON findings.
- [ ] Export a visual report.
- [ ] Keep every metric linked to its source Trace.

### Phase 9 — Change proposals

- [ ] Define a declarative change proposal format.
- [ ] Support `addNode`.
- [ ] Support `removeNode`.
- [ ] Support `renameNode`.
- [ ] Support `addEdge`.
- [ ] Support `removeEdge`.
- [ ] Support `addPermission`.
- [ ] Support `removePermission`.
- [ ] Support `addCapability`.
- [ ] Support `removeCapability`.
- [ ] Validate proposals before applying them.
- [ ] Reject partial application when one mutation is invalid.
- [ ] Keep the original Map unchanged while staging.
- [ ] Record proposal author, reason, and source Finding.

### Phase 10 — Pac-Man time travel: before and after

- [ ] Snapshot the current Map as state A.
- [ ] Apply a change proposal to an in-memory Map clone as state B.
- [ ] Run the same Journeys against state A.
- [ ] Run the same Journeys against state B.
- [ ] Compare reachable surfaces by role.
- [ ] Compare allowed capabilities by role.
- [ ] Compare edges and node relationships.
- [ ] Compare Trace events.
- [ ] Compare Findings.
- [ ] Identify newly reachable nodes.
- [ ] Identify newly unreachable nodes.
- [ ] Identify permissions gained.
- [ ] Identify permissions lost.
- [ ] Identify Findings resolved.
- [ ] Identify Findings introduced.
- [ ] Identify new dead ends and orphan zones.
- [ ] Render the before/after route in the visualizer.
- [ ] Add a time slider or state selector for A and B.
- [ ] Add a delta overlay showing what changed.
- [ ] Classify every delta as improvement, regression, or neutral.
- [ ] Hard-block critical security regressions.
- [ ] Soft-block notable regressions for human review.
- [ ] Allow clean improvements to proceed to approval.

### Phase 11 — Puppeteer mode: steer before changing reality

- [ ] Add a proposed-change workspace.
- [ ] Let an operator stage multiple alternative proposals.
- [ ] Run all candidate proposals against the same baseline.
- [ ] Rank proposals by Findings resolved and regressions introduced.
- [ ] Show the blast radius before merge.
- [ ] Generate a change-impact report.
- [ ] Require explicit human approval before promotion.
- [ ] Apply only approved changes to the canonical Map.
- [ ] Re-run the complete Journey suite after promotion.
- [ ] Store the before Map, proposal, after Map, Traces, and decision together.
- [ ] Add rollback to the previous Map version.
- [ ] Keep a full decision ledger.

### Phase 12 — Open-source launch maturity

- [ ] Add contribution guidelines.
- [ ] Add a code of conduct.
- [ ] Add issue templates for Maps, Journeys, adapters, visualizer findings, and change proposals.
- [ ] Add a changelog.
- [ ] Add CI for schemas, runner tests, examples, and visualizer build.
- [ ] Add security reporting guidance.
- [ ] Add reproducible demo instructions.
- [ ] Add a live public demo using the MindWaveMine Map.
- [ ] Build the landing page.
- [ ] Replace placeholder repository and documentation links.
- [ ] Publish the first tagged release.
- [ ] Write release notes in the project voice.
- [ ] Document the full Pac-Man time-travel workflow.

## Full completion condition

The full route is not complete because the maze looks good. It is complete when a user can:

1. declare a Map of real project facts;
2. define a Journey as a test or steering path;
3. run it and receive a Trace;
4. inspect Findings tied to that Trace;
5. propose a change without touching the canonical Map;
6. run Pac-Man through the before state;
7. run Pac-Man through the proposed after state;
8. see the exact delta;
9. detect security regressions before merge;
10. approve, promote, or reject the change;
11. replay the entire decision later.

That is **Pac-Man time travel**: the project can see what a change does before the change becomes reality.

## Update log

- 2026-11-06 — Expanded the ledger from the immediate backlog to the full Map → Journey → Trace → Findings → Pac-Man time-travel route.
- 2026-11-06 — Created the public update ledger after the first real MindWaveMine Map, Journeys, runner, and Trace landed.
