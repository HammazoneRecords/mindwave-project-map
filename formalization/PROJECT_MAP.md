# Project Map — formalization

## Meaning

**Project Map** is a versioned, declarative description of a project’s structure and operating facts.

It is not a dashboard, a UI mockup, or a test report. It is the reference surface that Journeys traverse.

## The Map

A Map may contain:

- `nodes`: things that exist — screens, routes, services, resources, workflows, or other project-defined objects
- `edges`: relationships between nodes — navigation, dependency, ownership, data flow, or project-defined links
- `roles`: actors or contexts that can traverse or act
- `capabilities`: named actions available in the project
- `permissions`: explicit subject–relation–object rules
- `states`: declared states and transitions where relevant
- `constraints`: rules that must remain true
- `metadata`: project name, schema version, and source information

The Map is facts as declared by the project. It may be incomplete or wrong; that is why Journeys exist.

## The Journey

A Journey is a declarative sequence that exercises a Map.

A Journey can:

- set a role or actor context
- move along a relationship
- attempt a move that should be denied
- invoke a capability
- assert a permission or state
- record a named checkpoint
- steer toward a target node or outcome

A Journey is both **test** and **steer**: it tests the current structure and can guide a human or agent through the intended path.

## Trace and Finding

A Trace is append-only execution evidence. It records the Map version, Journey ID, steps, outcomes, timestamps, and observed events.

A Finding is a structured interpretation of a Trace. Examples include:

- unreachable node
- denied transition
- unexpected access
- missing capability
- broken route
- dead end
- drift between the Map and an implementation

A Finding never changes the Map by itself. Promotion from observation to fact requires an explicit project decision.

## Architecture boundary

```text
canonical facts → Map
intended movement → Journey
observed movement → Trace
interpreted mismatch → Finding
```

Keep these surfaces separate. This prevents a test result, a visual layout, or a generated report from silently becoming canonical project truth.

## Skins

The same Map and Journey can power multiple skins:

- headless runner for CI
- CLI for developers
- graph view for architecture review
- maze view for interactive exploration
- browser or API adapter for real-system checks

A skin is an interface to the model, not a replacement for the model.

## Launch boundary

The public repository must remain generic. Private product maps, business plans, customer data, credentials, and internal terminology stay outside this repository.
