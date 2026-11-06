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

## Next build — make the model stronger

- [ ] Validate every Map against `spec/map.schema.json`.
- [ ] Validate every Journey against `spec/journey.schema.json`.
- [ ] Add clear validation errors with file path, record, and reason.
- [ ] Add a test command that runs validation and Journeys together.
- [ ] Add a formal Trace schema.
- [ ] Add a formal Finding schema.
- [ ] Separate expected denials from unexpected failures in the output.
- [ ] Add Journey result summaries that a person can read quickly.
- [ ] Add exit codes for CI use.

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

## Update log

- 2026-11-06 — Created the public update ledger after the first real MindWaveMine Map, Journeys, runner, and Trace landed.
