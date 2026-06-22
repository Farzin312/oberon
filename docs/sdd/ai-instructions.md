# AI Instructions — Agent Behavior Rules

**Parent**: [README.md](../README.md)

## For AI agents working on Oberon

1. **Start with the mini-SDD.** Before making any change, read the active mini-SDD's README, plan, and tasks. Every task in tasks.md has a corresponding plan.md section with the exact contract.
2. **Never skip TDD.** Write a failing test first, watch it fail, then implement. No exceptions.
3. **Bounds describe before edit.** Run `bounds describe <subsystem>` before touching any file in a subsystem. This tells you the public surface, consumed interfaces, and file ownership.
4. **Bounds validate after edit.** Run `bounds validate --quick` after every change. If a public surface changed, update the manifest.
5. **Mini-SDD docs sync in the same change.** Updating the tasks.md checkboxes, recording gate results, and updating plan.md with phase outcomes all happen in the same change, not as a follow-up.
6. **Ponytail is active.** YAGNI, stdlib first, one line over fifty. No speculative abstractions.
7. **Never fabricate API responses.** If a STAC catalog, COG read, or model inference would require actual infrastructure, write code that would work — with documentation of what needs to be running. Use fixtures for tests.
8. **Abstention is a valid result.** If the code detects poor inputs — cloud > threshold, alignment fails, insufficient valid pixels — return an AbstentionResult, not a fake finding.
9. **Provenance is product data.** Every finding must record which source scenes, bands, processing config, model version, and software version produced it. A log line is not provenance.

## Subsystem boundaries (bounds)

The bounds manifests in `.bounds/` are the single source of truth for:
- What each subsystem owns (file paths)
- What each subsystem exports (public symbols)
- What each subsystem consumes (interfaces from other subsystems)
- The subsystem's role and criticality

If bounds validation fails, the change is not complete until the manifest is updated.
