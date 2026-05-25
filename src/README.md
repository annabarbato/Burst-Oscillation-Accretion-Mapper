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
- `burst_oscillation_accretion_mapper.catalog_writer`: SQLite development catalog writer for Phase 1 burst review rows, oscillation candidate rows, scored control rows, non-detections, Leahy diagnostics, and nominal timing significance fields.
- `burst_oscillation_accretion_mapper.control_checks`: targeted control-window search/scoring runner plus explicit control-clearance evidence checks for Phase 1 empirical false-alarm review.
- `burst_oscillation_accretion_mapper.control_intervals`: deterministic pre/post-burst and neighboring non-burst control-window generation plus empirical false-alarm summaries for scored controls.
- `burst_oscillation_accretion_mapper.dynamic_power`: dynamic power-spectrum grid products from sliding targeted-search outputs for Phase 1 review.
- `burst_oscillation_accretion_mapper.event_products`: in-memory event product metadata, provenance, GTI-aware slicing, and energy filtering primitives.
- `burst_oscillation_accretion_mapper.external_tools`: read-only HEASoft/CALDB environment snapshots.
- `burst_oscillation_accretion_mapper.lightcurves`: GTI-corrected single- and multi-cadence event binning plus rolling baseline helpers for early burst-detection work.
- `burst_oscillation_accretion_mapper.manifests`: typed loader for the curated RXTE/PCA source, observation, and validation-target manifests.
- `burst_oscillation_accretion_mapper.minbar_matching`: timing-window matching, deterministic detected-window construction, observation-level reports, and recall/review-burden metrics for MINBAR validation targets.
- `burst_oscillation_accretion_mapper.oscillation_search`: targeted event-based `Z_n^2` search primitives, Leahy diagnostics, first-harmonic phase/amplitude estimates, optional NumPy acceleration, and sliding-window searches around known source frequencies for Phase 1 validation windows.
- `burst_oscillation_accretion_mapper.phase1_recovery`: validation recovery status helpers that keep known-signal recovery and expected non-detection review separate from conservative catalog candidate classes.
- `burst_oscillation_accretion_mapper.phase1_validation`: Phase 1 validation-run summaries and gate checks across burst, candidate, control, and MINBAR timing products.
- `burst_oscillation_accretion_mapper.raw_inventory`: local raw-product inventory and checksum helpers.
- `burst_oscillation_accretion_mapper.rxte_archive`: HEASARC RXTE/PCA archive URL discovery and local mirroring helpers for selected Phase 1 products.
- `burst_oscillation_accretion_mapper.rxte_binned`: RXTE/PCA SingleBit high-time binned product reader that expands counts to deterministic bin-center event-equivalent times for validation products lacking paired GoodXenon conversion inputs.
- `burst_oscillation_accretion_mapper.rxte_corrections`: HEASoft `barycorr` command construction and execution wrappers that require real RXTE orbit files and reject `GEOCENTER`.
- `burst_oscillation_accretion_mapper.rxte_config`: RXTE/PCA detector-selection and barycenter provenance configuration.
- `burst_oscillation_accretion_mapper.rxte_backend`: RXTE/PCA local raw-product preflight checks and provenance assembly before event-table ingestion.
- `burst_oscillation_accretion_mapper.rxte_fits`: Astropy-based local RXTE FITS event-table reader for products with explicit event-time columns.
- `burst_oscillation_accretion_mapper.rxte_goodxenon`: guarded GoodXenon pairing checks and `make_se` conversion status recording.
- `burst_oscillation_accretion_mapper.rxte_product_selection`: explicit ranking of barycentered `XTE_SE`, raw `XTE_SE`, `make_se`, and SingleBit fallback products for Phase 1 validation.
- `burst_oscillation_accretion_mapper.rxte_time`: RXTE TT mission-time conversion helpers for MINBAR UTC MJD validation windows.
- `burst_oscillation_accretion_mapper.search_configs`: deterministic targeted-search review configuration fingerprints for Phase 1 catalog provenance.
- `burst_oscillation_accretion_mapper.synthetic_controls`: synthetic Poisson null-control products with event-rate envelopes for Phase 1 false-alarm review.
- `burst_oscillation_accretion_mapper.timing_significance`: single-trial and nominal independent-trial corrected p-value helpers for Phase 1 `Z_n^2` products.
- `burst_oscillation_accretion_mapper.time_intervals`: small GTI and event-window helpers for future event slicing.

Do not add NICER backend code, injection/recovery code, inference models, or dashboard code before the roadmap phase is explicitly advanced.
