# MindWave Project Map Launch Working Plan

**Status:** ACTIVE
**Goal distance:** 3/5 — public foundation structured; runtime and release proof remain.

## Goal

Launch a domain-neutral open-source Project Map repository under MindWave branding without leaking private RAAS material.

## Current position

- Source architecture inspected in private `HammazoneRecords/raas-maze`.
- Reusable distinction formalized: Map = facts; Journey = test / steer; Trace = evidence; Finding = diagnosis.
- New public foundation is being built from a clean extraction, not by publishing the private monorepo.

## Scope boundary

Keep out: RAAS business documents, pitch material, customer data, private project maps, credentials, and product-specific routes or names.

## Planned phases

1. Formalize vocabulary and schemas. **Current.**
2. Create public repository and push initial foundation.
3. Add validation and a headless Journey runner.
4. Add launch landing page and documentation.
5. Add visual skins and project adapters.

## Acceptance criteria for this stage

- public repo has a clear README
- Map and Journey schemas are present and valid JSON
- generic example files are present
- MIT license is present
- no private RAAS artifacts are copied
- remote ref is verified against local commit

## Evolution log

- 2026-11-06 — PROPOSED → ACTIVE; distance 1 → 3; formalized the Map/Journey split and started a clean public foundation.

## Next decision

Complete the first push, then implement validation and runner proof before calling the architecture launch-ready.
