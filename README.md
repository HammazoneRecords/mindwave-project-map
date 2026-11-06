# MindWave Project Map

> the map is the facts. the journey is the test / steer.

MindWave Project Map is an open architecture for describing a project as a versioned map of facts, then running journeys across that map to test how the system behaves.

It separates four things that usually get tangled together:

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

This repository is the public foundation for the architecture. It is intentionally domain-neutral. It does not contain RAAS business material, private project data, credentials, or product-specific canon.

The first release establishes the vocabulary, schema direction, example Map, and Journey model. Runtime adapters and visual skins can be added without changing the distinction between facts and traversal.

## Project shape

```text
spec/
  map.schema.json       # declarative Map format
  journey.schema.json   # executable Journey format
examples/
  workspace.map.json    # small generic project map
  member-create.journey.yaml
formalization/
  PROJECT_MAP.md        # architecture and invariants
  TERMINOLOGY.md        # stable language
LICENSE
README.md
```

## Design invariants

1. A Journey cannot silently rewrite the Map.
2. A Trace records what happened; it does not become a new fact automatically.
3. Findings must identify the Map version and Journey that produced them.
4. A visual skin must read from the same Map and Journey model as the headless runner.
5. Domain examples remain replaceable. The architecture must not depend on one company's vocabulary.

## License

MIT. See [LICENSE](./LICENSE).

## Next

- validate Map and Journey documents
- build a headless Journey runner
- emit portable Trace JSON
- add a CLI skin
- add graph and maze skins
- add adapters for real project surfaces
