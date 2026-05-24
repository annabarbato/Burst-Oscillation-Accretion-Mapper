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

## Operational Data Status

Checked on 2026-05-24:

- `astropy` is installed in the active Python environment and listed in the optional `science` dependency group.
- HEASoft/FTOOLS commands (`ftools`, `ftlist`, `fbcopy`, `make_se`, `sefilter`, `fselect`, and `barycorr`) were not available on `PATH` in this Windows environment.
- No `conda`, `mamba`, or `micromamba` executable was available on `PATH` for a lightweight local HEASoft install path.
- Local RXTE/PCA archive preflight now passes for all selected manifest rows because the curated PCA and standard GTI/filter products are present locally.
- Event-table parsing was verified for downloaded `XTE_SE` products in `10088-01-07-02`, `20084-02-01-00`, and `30061-01-02-01`.
- The mirrored PCA trees for `10073-01-01-00` and `10073-01-02-00` did not include simple `SE*.evt.gz` event tables. They currently contain binned and housekeeping-mode products that require HEASoft/FTOOLS handling or alternate event products before event-level burst and oscillation validation can run.
- The downloaded `XTE_SE` products for `20084-02-01-00` do not cover the selected MINBAR.2322 burst time, so that target also remains unavailable for event-level burst-oscillation validation with the currently mirrored event tables.

## Partial Real-Event Validation

Checked on 2026-05-24 with downloaded `XTE_SE` products and MINBAR UTC burst times converted to RXTE TT mission seconds:

- MINBAR.2257 (`10088-01-07-02`) burst recovery: multi-cadence detector found one candidate with start 0.18 s before the converted MINBAR time, peak 1.32 s after it, duration 26.0 s, and best peak score 247.90.
- MINBAR.2431 (`30061-01-02-01`) burst recovery: multi-cadence detector found one candidate with start 2.18 s before the converted MINBAR time, peak 1.32 s after it, duration 30.0 s, and best peak score 224.21.
- MINBAR.2257 targeted oscillation search around 581 Hz over 4 s sliding windows found best frequency 580.75 Hz with `Z_1^2 = 26.726`, classified as probable under Phase 1 scoring because secure-evidence checks are intentionally incomplete without full controls and Phase 2 sensitivity.
- MINBAR.2431 targeted oscillation search around 524 Hz over 4 s sliding windows found best frequency 523.25 Hz with `Z_1^2 = 17.716`, classified as marginal under current Phase 1 thresholds.
- Pre-burst controls for the two event-covered targets scored as non-detections at the same configured thresholds.

## Explicitly Deferred Or Blocked

- HEASoft/FTOOLS execution, RXTE mode conversion, barycentric correction, and binary orbital correction remain blocked until HEASoft is installed in the execution environment.
- Real end-to-end burst recovery against MINBAR timings remains blocked for the selected 4U 1728-34 validation/control rows until event-level products are available.
- Known oscillation recovery and expected non-detection confirmation on real event data remain blocked for the incomplete event-product rows and should not be certified from synthetic or binned housekeeping products.
- The Phase 1 validation gate is implemented, but should only be used for Phase 1 closeout once real burst-review, candidate/non-detection, control, and MINBAR timing outputs have been generated from event-level products.
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

The gate is intentionally about artifact completeness and conservative false-alarm hygiene. It does not certify astrophysical discovery claims and does not replace Phase 2 selection-function correction.

As of 2026-05-24, the gate should not be used to declare full Phase 1 complete on the selected validation set, because three selected MINBAR targets do not yet have event-level products covering the validation burst in this environment.
