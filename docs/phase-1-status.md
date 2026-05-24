# Phase 1 Status

Last updated: 2026-05-24

This checklist tracks the current Phase 1 implementation against `docs/roadmap.md`. It is a working status note, not a replacement for the architecture or roadmap.

## Scope

Phase 1 remains RXTE/PCA-only. This phase does not add NICER/XTI, population inference, dashboard code, or Phase 2 injection/recovery sensitivity products.

## Completed In Repository

- RXTE/PCA validation manifests with exact ObsIDs and MINBAR IDs where available.
- Local raw-product archive planning and preflight checks.
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

## Explicitly Deferred

- Real RXTE FITS event parsing and HEASoft command execution are still represented by preflight/provenance scaffolding until local raw products and tool availability are confirmed.
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
