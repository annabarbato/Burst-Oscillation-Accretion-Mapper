# Agent Rules For This Repository

These rules keep Burst-Oscillation Accretion Mapper aligned with its architecture and roadmap. They apply to all future coding, documentation, data, and analysis work in this repository.

## Canonical Project Sources

- Treat `docs/architecture.md` as the source of truth for system design, scientific framing, storage boundaries, pipeline interfaces, candidate classes, selection-function requirements, and inference principles.
- Treat `docs/roadmap.md` as the source of truth for implementation order, phase gates, deliverables, validation checks, and definition of done.
- Do not invent a new architecture, pipeline shape, database concept, or scientific framing without explicitly updating the relevant doc first.

## Phase Discipline

- Work one roadmap phase at a time.
- The active phase starts at Phase 0 until its acceptance criteria are complete or the user explicitly advances the project.
- Do not implement work from a later phase just because it is interesting or convenient.
- If a requested task belongs to a later phase, say which phase it belongs to and either defer it or make the phase advancement explicit.
- When starting work, identify the roadmap phase the task belongs to.
- When finishing work, state whether the phase acceptance criteria changed, were advanced, or remain unchanged.

## Change Control

- Any addition to scope must be explicit.
- Before implementing a capability not already described in `docs/architecture.md` or `docs/roadmap.md`, update the docs or add a short design note explaining:
  - what is being added,
  - why it is needed,
  - which phase owns it,
  - how it affects validation or acceptance criteria.
- Do not silently add new science claims, instruments, models, dashboards, schemas, or workflows.
- Prefer small, phase-aligned changes over broad refactors.

## Scientific Guardrails

- Keep the project framed as a selection-function-corrected thermonuclear burst-oscillation discovery and correlation pipeline.
- Do not drift into a generic 500 Hz to 1 kHz peak finder.
- Do not treat kHz QPOs as the primary target; they are related accretion-flow timing phenomena, not the main burst-oscillation product.
- Do not report or optimize for naive correlations without selection-function correction.
- Treat non-detections as useful data with upper limits and sensitivity curves.
- RXTE/PCA validation comes before NICER/XTI expansion unless the user explicitly changes the roadmap.

## Implementation Guardrails

- Build against the conceptual interfaces in `docs/architecture.md`: ingest backend, burst detector, oscillation searcher, injection/recovery runner, feature extractor, candidate scorer, inference runner, catalog writer, and dashboard/export layer.
- Preserve provenance in every data product: raw references, software versions, calibration versions, screening choices, barycenter settings, search configuration, and pipeline version.
- Keep candidate scoring conservative: secure, probable, marginal, and non-detection.
- Prefer validated statistical detectors and event-based timing methods before machine-learning classifiers.
- Every later scientific model must account for source identity, instrument, photon statistics, and sensitivity.

## Review Checklist Before Each Change

Before making a change, confirm:

- Which roadmap phase owns this work?
- Is the work already described in the architecture or roadmap?
- Does it preserve RXTE-first validation and NICER-second expansion?
- Does it preserve selection-function correction and non-detection handling?
- Does it need a doc update before implementation?

After making a change, report:

- Files changed.
- Phase affected.
- Whether any scope was added.
- Tests or checks run.

