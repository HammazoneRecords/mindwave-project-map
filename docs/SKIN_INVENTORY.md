# Skin Inventory

> the map is the facts. the journey is the test / steer. everything else is a skin.

This document is the full inventory of skins that can sit on the Project Map framework. One Map, one Journey model — every entry here reads the same facts and only changes the reflection.

The framework rule: a skin never becomes the source of truth. If a skin disagrees with the Map, the Map wins until a verified Journey proves otherwise.

## Status legend

- ✅ built and verified
- 🟡 designed or has working precedent in the predecessor engine
- ⬜ specified, not built

## Inspection skins — see the system

| # | Skin | Reads | Status |
|---|---|---|---|
| 1 | CLI / terminal (ASCII flow, Mermaid, pseudocode export) | Map, Journey, Trace | ✅ |
| 2 | Graph view (2D nodes/edges, role reachability) | Map, Journey, Trace | ✅ |
| 3 | 3D maze / ant-cast (walkable Pac-Man surface) | Map, Journey, Trace | 🟡 |
| 4 | Room visualizer (chambers, tunnels, voids) | Map | 🟡 |
| 5 | Product screen (live website/app viewport) | Map + adapter | ⬜ |
| 6 | Code view (source context + Variable Matrix) | Map, Variables | ✅ partial |
| 7 | Schema view (2D permission matrix, read-only) | Map | 🟡 |

## Execution skins — move through the system

| # | Skin | Reads | Status |
|---|---|---|---|
| 8 | Headless CI runner (validate + run + exit codes) | Map, Journey | ✅ |
| 9 | Journey playback (step-by-step forward walk) | Journey, Trace | ⬜ |
| 10 | Trace replay scrubber (rewind, speeds, step) | Trace | 🟡 |
| 11 | Browser/API live adapter (real product targets) | Map + live target | ⬜ |
| 12 | AI agent mode (subagents walk the map, report findings) | Map, Journey | 🟡 |

## Time skins — compare states

| # | Skin | Reads | Status |
|---|---|---|---|
| 13 | State A/B diff view (before/after proposal) | Two Maps + Traces | ⬜ |
| 14 | Time-travel slider / state selector | Map versions | ⬜ |
| 15 | Puppeteer proposal workspace (stage, rank, impact) | Map + proposals | ⬜ |

## Audience skins — the same skeleton, different worlds

The skeleton is audience-agnostic. Each audience is a template skin on the same bones — no new architecture required.

| # | Audience skin | Ruling status |
|---|---|---|
| A1 | Artist site (Free League template 1) | ruled, flagship |
| A2 | Athlete site (Free League template 2) | ruled as template; public-launch lane proposed 2026-11-07, pending facts-DB ruling |
| A3 | Family-brand site (Free League template 3) | ruled |
| A4 | CAS-business site (Free League template 4) | ruled |
| A5 | Politician / public figure | not ruled — same shape would work; requires founder ruling before any pitch or published claim |

## Total count

```text
technical skins:  15  (6 built, 4 precedented, 5 specified)
audience skins:    5  (4 ruled, 1 unruled)
```

## What a new skin must prove

Before any skin is marked complete:

1. It reads Map/Journey/Trace data — no hardcoded project names.
2. It never edits the Map; proposals go through the change-proposal path.
3. It labels what it is: simulation, snapshot, or live.
4. It passes the shared leak scan (no private project material).
5. Its completion is recorded only after the artifact is exercised.

## Relationship to the launch strategy

The skin inventory is why the January traction plan is cheap to execute: the athlete lane is a skin job (template A2 on existing bones), not a new build. Every additional audience is the same equation — new skin, same skeleton, new edge touched.
