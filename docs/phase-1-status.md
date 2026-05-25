# Phase 1 Status

Last updated: 2026-05-24

This checklist tracks the current Phase 1 implementation against `docs/roadmap.md`. It is a working status note, not a replacement for the architecture or roadmap.

## Scope

Phase 1 remains RXTE/PCA-only. This phase does not add NICER/XTI, population inference, dashboard code, or Phase 2 injection/recovery sensitivity products.

## Completed In Repository

- RXTE/PCA validation manifests with exact ObsIDs and MINBAR IDs where available.
- Local raw-product archive planning, HEASARC observation-directory links, mirroring helpers, and preflight checks.
- Selected RXTE/PCA Phase 1 products mirrored into ignored local paths under `data/raw/rxte/` on 2026-05-24.
- Astropy-based RXTE FITS event-table ingestion for local products with explicit `EVENTS`, `XTE_SE`, or `STDEVT` time columns.
- RXTE/PCA SingleBit high-time binned ingestion for validation products that lack paired GoodXenon files.
- RXTE detector-selection and barycenter provenance configuration.
- In-memory event products with GTI-aware time slicing and energy filtering.
- Multi-cadence light curves and rolling baseline helpers.
- Poisson excess burst candidate scoring, morphology review, multi-cadence clustering, and detector summaries.
- MINBAR timing-window matching with recall and review-burden metrics.
- Targeted event-based `Z_n^2` searches around known frequencies, Leahy diagnostics, first-harmonic phase, fractional-rms estimates, sliding windows, and dynamic power grids.
- Conservative candidate scoring into secure, probable, marginal, and non-detection review classes.
- SQLite development catalog rows for burst reviews, oscillation candidates, controls, and non-detections.
- Deterministic search-configuration fingerprints for catalog provenance.
- Pre-burst, post-burst, neighboring non-burst, and synthetic Poisson null controls for empirical false-alarm review.
- Phase 1 validation-run summaries and gate checks across burst, candidate, control, and MINBAR timing products.
- Reproducible real-data validation runner at `pipelines/run_phase1_real_validation.py`.

## Operational Data Status

Checked on 2026-05-24:

- `astropy` is installed in the active Python environment and listed in the optional `science` dependency group.
- HEASoft 6.36 is available in WSL under the `henv` conda environment. `make_se`, `seextrct`, `barycorr`, and `ftlist` were found in `/home/anna/miniforge3/envs/henv/heasoft/bin`.
- Local RXTE/PCA archive preflight now passes for all selected manifest rows because the curated PCA and standard GTI/filter products are present locally.
- The exact burst-covering archive segments are `10088-01-07-02`, `10073-01-01-000`, `10073-01-02-000`, `20084-02-01-000`, and `30061-01-02-01`.
- Real RXTE `orbit/FPorbit_Day*` products are mirrored for all five validation ObsIDs and used by HEASoft `barycorr`.
- Event-table parsing was verified for downloaded `XTE_SE` products in `10088-01-07-02`, `20084-02-01-000`, and `30061-01-02-01`.
- HEASoft `make_se` was run against the 4U 1728-34 suffixed products. It found `GoodXenon1` inputs without paired `GoodXenon2` inputs and therefore did not produce SE files. The validation runner uses burst-covering `SB_125us_0_249_1s` SingleBit products for those two targets, with binned provenance retained.
- Binary orbital correction is not applied because the current `sources.csv` rows do not contain trusted binary ephemerides; validation output records `binarycorr_status=no_ephemeris`.

## Real-Event Validation

Checked on 2026-05-24 with downloaded `XTE_SE` and SingleBit products, HEASoft `barycorr`, source coordinates from `sources.csv`, `refframe=ICRS`, `ephem=JPLEPH.440`, `barytime=no`, and real RXTE orbit files:

- `pipelines/run_phase1_real_validation.py` wrote ignored outputs to `data/products/phase1_real_validation/phase1_real_validation.sqlite` and `data/products/phase1_real_validation/summary.json`.
- The runner estimates the local barycentric time offset from paired raw/corrected products before comparing against MINBAR burst windows.
- Burst recovery matched all five selected MINBAR targets with recall 1.0, no missing detections, no unmatched detections, max absolute timing delta 8.0 s, and mean absolute peak delta 1.1 s.
- Candidate classes from targeted searches were: 0 secure, 2 probable, 2 marginal, and 1 non-detection.
- Validation recovery status, separate from catalog class, recovered MINBAR.2257 and MINBAR.2204 as known signals. MINBAR.2322 and MINBAR.2431 remain below known-signal recovery threshold under current Phase 1 evidence.
- The expected non-detection target MINBAR.2206 remained below probable threshold and was classified as marginal under the current Phase 1 review thresholds, so it should remain a review item rather than a detection claim.
- Pre/post, neighboring, and 32 synthetic Poisson null controls per target were scored: 179 controls total, 0 secure, 0 probable, 35 marginal, and 144 non-detections.
- The Phase 1 validation gate passed with `min_minbar_recall_fraction=1.0`, `max_secure_control_count=0`, and `max_probable_control_count=0`.
- The strict closeout check passed. Every case carries `p_single`, `p_trials`, empirical control-FAP, correction status, and validation recovery status in `summary.json`.

## Source Notes

External sources used by this status note are tracked in `data/manifests/references.csv`:

- RXTE/PCA archive and instrument assumptions: `rxte_pca_heasarc`.
- HEASoft availability and mission-tool context: `heasoft_docs`.
- MINBAR burst timing and ObsID mappings: `minbar_entry_2257`, `minbar_entry_2204`, `minbar_entry_2206`, `minbar_entry_2322`, and `minbar_entry_2431`.
- Source coordinates and source classes: `simbad`.
- Source-level burst-oscillation frequency seeds and published oscillation labels: `bo_4u_1636_536_581hz`, `bo_4u_1636_536_tail_osc_table`, `bo_4u_1728_34_363hz`, `bo_4u_1702_429_330hz`, and `bo_ks_1731_260_524hz`.

Operational closeout claims are local pipeline outputs from `pipelines/run_phase1_real_validation.py`, specifically the ignored `data/products/phase1_real_validation/summary.json` and `phase1_real_validation.sqlite` artifacts generated on 2026-05-24.

## Explicitly Deferred

- Binary orbital correction remains gated on curated source ephemerides. The workflow records `no_ephemeris` rather than applying an approximate correction.
- Amplitude upper limits and sensitivity curves are Phase 2 injection/recovery products. Phase 1 non-detections are represented as catalog rows that can later attach those products.
- NICER/XTI backend work remains Phase 3.
- Hierarchical correlation and inference remain Phase 4.
- Public dashboard and release exports remain Phase 5.

## Phase 1 Closeout Gate

Use `burst_oscillation_accretion_mapper.phase1_validation` to summarize a validation run and evaluate whether the Phase 1 artifacts include:

- At least one burst-review row.
- At least one candidate or non-detection row.
- At least one non-detection row.
- At least one control row.
- MINBAR timing metrics.
- No secure detections in control rows under the default policy.
- No probable detections in control rows under the strict closeout policy.
- Real RXTE barycentric correction status for every selected target.
- Trials and empirical control-FAP fields for every candidate/non-detection.

The gate is intentionally about artifact completeness and conservative false-alarm hygiene. It does not certify astrophysical discovery claims and does not replace Phase 2 selection-function correction. Phase 1 is now strictly closed out for the selected RXTE validation set; Phase 2 should add injection/recovery sensitivity rather than more Phase 1-only evidence promotion.
