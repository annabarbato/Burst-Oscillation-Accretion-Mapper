# Source Package

This directory contains the Phase 1 Python package skeleton.

The current package exports only version metadata. It does not define a stable public science API yet; implementation modules should mature behind the roadmap-aligned internal boundaries before anything is advertised as reusable.

Expected Phase 1 modules should align with the conceptual interfaces in `docs/architecture.md`:

- Ingest backend.
- Burst detector.
- Oscillation searcher.
- Candidate scorer.
- Catalog writer.

Current modules:

- `burst_oscillation_accretion_mapper.archive_plan`: no-download RXTE raw archive planning from validation manifests.
- `burst_oscillation_accretion_mapper.event_products`: in-memory event product metadata, provenance, GTI-aware slicing, and energy filtering primitives.
- `burst_oscillation_accretion_mapper.lightcurves`: GTI-corrected event binning and rolling baseline helpers for early burst-detection work.
- `burst_oscillation_accretion_mapper.manifests`: typed loader for the curated RXTE/PCA source, observation, and validation-target manifests.
- `burst_oscillation_accretion_mapper.time_intervals`: small GTI and event-window helpers for future event slicing.

Do not add NICER backend code, injection/recovery code, inference models, or dashboard code before the roadmap phase is explicitly advanced.
