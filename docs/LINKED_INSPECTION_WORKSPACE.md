# Linked Inspection Workspace

> the variable matrix column can become the window into the room, while the map, pseudocode, and source stay linked to what is on screen.

## Concept

The Variable Matrix is not limited to a table. Its column can act as a **live inspection viewport**:

- room visualizer
- actual product screen
- live website
- local app preview
- route or component preview
- source-context view when no visual surface exists

The selected variable, Map node, Journey step, or Finding becomes the reference point for every column.

```text
┌──────────────┬─────────────────────────┬─────────────────────────┐
│ PROJECT MAP  │ VARIABLE MATRIX / ROOM  │ PSEUDOCODE + CODE       │
│              │                         │                         │
│ node         │ selected screen / room  │ related Journey         │
│ edges        │ actual product view     │ related pseudocode      │
│ permissions  │ visual state            │ source context          │
│ Journey path │ highlighted variables   │ highlighted Map links   │
└──────────────┴─────────────────────────┴─────────────────────────┘
```

## Click behavior

When a user clicks a Variable Matrix row, Map node, Journey step, room, product screen, or Finding, the workspace keeps one shared selection context.

```text
click one thing
    ↓
resolve shared ID
    ↓
highlight every related surface
    ↓
move the center viewport to the selected room / product screen
    ↓
show the linked pseudocode, Map path, variables, source, Trace, and Findings
```

### When a Variable Matrix row is clicked

- the center column opens the related room visualizer, product screen, website route, or code fallback;
- the corresponding Map node and connected edges highlight;
- the related Journey step highlights;
- the pseudocode line highlights;
- the actual source definition and use sites highlight;
- any Trace events and Findings using that variable appear in context.

### When a Map node is clicked

- the center viewport moves to the linked room or product surface;
- the Variable Matrix filters to symbols connected to that node;
- the Journey route highlights the path into and out of the node;
- pseudocode and code references follow the same selection.

### When a Journey step is clicked

- the center viewport shows the screen or room at that step;
- the Map path up to that point remains highlighted;
- the variable and source references used by the step appear;
- the Trace event is selected, with any Finding attached beside it.

### When a Finding is clicked

- every affected surface highlights together;
- the workspace shows the Map element, variable, pseudocode, actual code, and visible product state;
- the user can compare the current state against a proposed state when time-travel mode exists.

The click should move the user through the system, not open disconnected documents. One selection. Many linked reflections.


1. Select a Map node, variable, Journey step, Finding, route, or capability.
2. Resolve its linked identifiers.
3. Open the related room, product screen, website route, or source context.
4. Highlight the corresponding Map node and edges.
5. Highlight the related Variable Matrix row and symbols.
6. Highlight the relevant pseudocode step.
7. Highlight the actual source range or adapter call.
8. Show the current Trace state and any related Findings.

## Highlight relationships

### Map → room / product

Selecting a Map node should reveal the corresponding room, page, route, or component in the center viewport.

### Variable → visual state

Selecting a Variable Matrix row should reveal where that variable affects the selected room or product screen.

### Journey → movement

Selecting a Journey step should move the center viewport to the relevant room or route and show the before/after state if available.

### Finding → diagnosis

Selecting a Finding should highlight the affected Map element, variable row, pseudocode line, source range, and visible product surface together.

## Modes

- **Room mode** — abstract visualizer showing the system as spaces and paths.
- **Product mode** — actual website or application screen, embedded or connected through an adapter.
- **Code mode** — source context and Variable Matrix relationships.
- **Journey mode** — active traversal with current step highlighted.
- **Time-travel mode** — state A and state B shown side by side or with a state slider.

## Safety and truth boundaries

- The center viewport must show whether it is a room simulation, a static capture, or a live product surface.
- A highlighted relationship is not proof that the live product behaved correctly; the Trace is the evidence.
- Source references must identify the repository and commit or snapshot.
- Live product interaction must use an explicit safe mode before any mutating action.
- The Variable Matrix remains a code-relationship surface; it does not become the project Map.

## Export

An exported inspection package should preserve the links:

```text
inspection/
├── map.json
├── variables.json
├── journeys.json
├── traces.json
├── findings.json
├── flowchart.mmd
├── pseudocode.md
├── source-reference.md
├── screenshots/
│   └── selected-surface.png
└── links.json
```

`links.json` records the shared identifiers that let another viewer reconstruct the highlights.

## The user experience

The user should be able to ask:

> what room am i in, what variable controls this, what path brought me here, what code makes it happen, and what did the test prove?

…and see the answer without opening five unrelated tools.
