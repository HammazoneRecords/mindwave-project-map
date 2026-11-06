# Variable + Code View

> this is the part where the notebook, the textbook, and the code stop living in separate rooms.

## The problem

When writing code, the variable definition, the syntax that uses it, and the larger path through the program are often separated across files, editors, documentation, and memory.

That creates unnecessary friction:

- the variable is defined somewhere else;
- the syntax is easy to forget;
- the current function is using a value whose meaning is not visible;
- the relationship between code and project flow is hidden;
- notes become a second system that drifts away from the code.

## The Project Map answer

The Maze should let a user examine the structure at the same time as the code that gives the structure life.

```text
Map fact
  ↓
variable / symbol definition
  ↓
actual source reference
  ↓
Journey step using it
  ↓
Trace event
  ↓
Finding or explanation
```

The user should not have to choose between:

- seeing the flow;
- seeing the variable;
- seeing the syntax;
- seeing the actual source;
- seeing what the test did.

The view should let them hold these together without pretending they are the same thing.

## Proposed inspection view

A user selects a node, capability, Journey step, or Finding and receives a linked inspection surface:

```text
┌──────────────────┬───────────────────────┬──────────────────────┐
│ PROJECT MAP      │ VARIABLE MATRIX      │ ACTUAL CODE           │
│                  │                       │                       │
│ selected node    │ symbol name           │ source file           │
│ incoming edges   │ type / interface      │ line range            │
│ outgoing edges   │ defined in            │ syntax-highlighted    │
│ role access      │ used by               │ surrounding context   │
│ Journey route    │ dependency links      │ copy reference        │
└──────────────────┴───────────────────────┴──────────────────────┘
                         │
                         v
                  TRACE / FINDING
```

## What this should support

- [ ] Select a Map node and find related source symbols.
- [ ] Select a variable and see its definition plus all known uses.
- [ ] Select a Journey step and see the code or adapter call it exercises.
- [ ] Select a Finding and jump to the affected Map element, variable, and source range.
- [ ] Show the actual code beside the explanatory pseudocode.
- [ ] Show syntax notes without making a separate notebook mandatory.
- [ ] Keep source references tied to a commit or snapshot.
- [ ] Make the relationship inspectable without editing source code.
- [ ] Allow a user to export the inspection package.

## Export package

A user-facing export should be able to contain:

```text
project-inspection/
├── map.json
├── journeys.json
├── traces.json
├── findings.json
├── flowchart.md
├── flowchart.mmd
├── pseudocode.md
├── variable-matrix.md
├── source-reference.md
└── code/
    └── selected-context.txt
```

## Boundary

The Variable Matrix describes code relationships. The Project Map describes project relationships. The Journey tests a route through those relationships. The actual code is evidence and context.

Do not flatten them into one giant generated document. Link them so the user can move between levels without losing the distinction.

## The simple promise

> see the thing in the map, see the variable that carries it, see the code that uses it, and see the journey that proves what happened.

That is how we get the notebook, the textbook, and the program on the same table.
