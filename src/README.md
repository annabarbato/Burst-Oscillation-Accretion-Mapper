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
- `burst_oscillation_accretion_mapper.burst_detection`: configurable Poisson excess scoring, grouping of adjacent interval candidates, binned morphology review, multi-cadence review clustering, and cluster summary products for later MINBAR/catalog comparison.
- `burst_oscillation_accretion_mapper.candidate_scoring`: conservative configured scoring of targeted oscillation-search products into secure/probable/marginal/non-detection review summaries.
- `burst_oscillation_accretion_mapper.event_products`: in-memory event product metadata, provenance, GTI-aware slicing, and energy filtering primitives.
- `burst_oscillation_accretion_mapper.external_tools`: read-only HEASoft/CALDB environment snapshots.
- `burst_oscillation_accretion_mapper.lightcurves`: GTI-corrected single- and multi-cadence event binning plus rolling baseline helpers for early burst-detection work.
- `burst_oscillation_accretion_mapper.manifests`: typed loader for the curated RXTE/PCA source, observation, and validation-target manifests.
- `burst_oscillation_accretion_mapper.minbar_matching`: timing-window matching, deterministic detected-window construction, observation-level reports, and recall/review-burden metrics for MINBAR validation targets.
- `burst_oscillation_accretion_mapper.oscillation_search`: targeted event-based `Z_n^2` search primitives, first-harmonic phase/amplitude estimates, and sliding-window searches around known source frequencies for Phase 1 validation windows.
- `burst_oscillation_accretion_mapper.raw_inventory`: local raw-product inventory and checksum helpers.
- `burst_oscillation_accretion_mapper.rxte_config`: RXTE/PCA detector-selection and barycenter provenance configuration.
- `burst_oscillation_accretion_mapper.rxte_backend`: RXTE/PCA local raw-product preflight checks before FITS parsing exists.
- `burst_oscillation_accretion_mapper.time_intervals`: small GTI and event-window helpers for future event slicing.

Do not add NICER backend code, injection/recovery code, inference models, or dashboard code before the roadmap phase is explicitly advanced.
