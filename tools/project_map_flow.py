#!/usr/bin/env python3
"""View or export the Project Map flow as ASCII, Mermaid, or pseudocode."""
import argparse
from pathlib import Path

ASCII = r'''MINDWAVE PROJECT MAP — CLI FLOW

  ┌──────────────┐
  │ PROJECT FACTS│
  └──────┬───────┘
         v
  ┌──────────────┐       ┌──────────────┐
  │ MAP          │───────>│ ROLE / STATE │
  │ nodes edges  │        │ context      │
  │ permissions  │        └──────┬───────┘
  └──────┬───────┘               │
         v                       v
  ┌────────────────────────────────────┐
  │ JOURNEY — test / steer             │
  │ move · act · assert · checkpoint   │
  └────────────────┬───────────────────┘
                   v
  ┌────────────────────────────────────┐
  │ TRACE — observed steps and state   │
  └────────────────┬───────────────────┘
                   v
  ┌────────────────────────────────────┐
  │ FINDINGS — gaps, risk, dead ends   │
  └──────────────┬─────────────┬───────┘
                 v             v
             KEEP MAP     CHANGE PROPOSAL
                               v
                  ┌─────────────────────────┐
                  │ PAC-MAN TIME TRAVEL     │
                  │ state A → state B       │
                  │ same Journey, compare   │
                  └────────────┬────────────┘
                               v
                 improvement / neutral / regression
                               v
                    approve / record / block
                               v
                       NEW MAP VERSION
'''

MERMAID = '''flowchart TD
  FACTS[Project facts] --> MAP[Map: nodes, edges, roles, permissions]
  MAP --> CONTEXT[Role and state context]
  MAP --> JOURNEY[Journey: test / steer]
  CONTEXT --> JOURNEY
  JOURNEY --> TRACE[Trace: observed steps and outcomes]
  TRACE --> FINDINGS[Findings: gaps, denials, dead ends, risk]
  FINDINGS -->|no change| KEEP[Keep Map version]
  FINDINGS -->|change needed| PROPOSAL[Stage change proposal]
  PROPOSAL --> A[State A: current Map]
  PROPOSAL --> B[State B: proposed Map]
  A --> TIME[PAC-MAN TIME TRAVEL]
  B --> TIME
  TIME --> COMPARE[Run same Journey and compare delta]
  COMPARE --> IMPROVEMENT[Improvement]
  COMPARE --> NEUTRAL[Neutral]
  COMPARE --> REGRESSION[Regression]
  IMPROVEMENT --> APPROVE[Approve / promote]
  NEUTRAL --> RECORD[Record]
  REGRESSION --> BLOCK[Block / human review]
  APPROVE --> NEWMAP[New versioned Map]
  RECORD --> NEWMAP
'''

PSEUDOCODE = '''function project_map_run(map, journey):
    validate(map)
    validate(journey)
    state = journey.initial
    trace = Trace(map_version=map.version, journey_id=journey.id)

    for step in journey.steps:
        result = execute(step, map, state)
        trace.record(step, result)
        if result.changes_state:
            state = result.next_state
        if result.is_unexpected:
            trace.add_finding(classify(result), evidence=result)

    return trace

function pac_man_time_travel(current_map, proposal, journeys):
    state_a = snapshot(current_map)
    state_b = apply_proposal_to_clone(current_map, proposal)
    if state_b.is_invalid:
        return BLOCK(proposal, state_b.validation_errors)

    before = [project_map_run(state_a, j) for j in journeys]
    after  = [project_map_run(state_b, j) for j in journeys]
    delta = compare(before, after)

    if delta.has_critical_security_regression:
        return HARD_BLOCK(delta)
    if delta.has_notable_regression:
        return HUMAN_REVIEW(delta)
    if delta.is_improvement:
        return APPROVAL_READY(delta)
    return RECORD_AS_NEUTRAL(delta)
'''

OUTPUTS = {"ascii": ASCII, "mermaid": MERMAID, "pseudocode": PSEUDOCODE}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=OUTPUTS, default="ascii")
    parser.add_argument("--output", type=Path, help="write the selected output to a file")
    args = parser.parse_args()
    text = OUTPUTS[args.format].rstrip() + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(f"exported {args.format}: {args.output}")
    else:
        print(text, end="")

if __name__ == "__main__":
    main()
