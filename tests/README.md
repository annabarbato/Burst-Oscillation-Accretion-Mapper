# Tests

This directory is reserved for automated tests and small fixtures.

Expected early test areas:

- Configurable Poisson excess scoring, conservative interval grouping, binned morphology review, multi-cadence candidate clustering, and review summary products on synthetic light curves.
- Conservative configured scoring of targeted oscillation-search outputs into review classes.
- SQLite development catalog writes for burst review rows, oscillation candidate rows, scored control rows, non-detections, Leahy diagnostics, and nominal timing significance fields.
- Targeted control-window search/scoring checks and explicit control-clearance evidence checks for empirical false-alarm review.
- Deterministic pre/post-burst and neighboring non-burst control intervals plus empirical false-alarm summaries on scored controls.
- Dynamic power-spectrum grid products from sliding targeted-search outputs.
- No-download archive planning for selected RXTE/PCA raw products.
- HEASoft/CALDB environment snapshot behavior without running mission tools.
- Local raw-product inventory and checksum behavior.
- HEASARC RXTE/PCA archive URL discovery and local mirroring helper behavior.
- RXTE/PCA detector-selection and barycenter provenance configuration.
- RXTE/PCA ingestion preflight behavior before event-table ingestion.
- RXTE/PCA product-selection ranking, real-orbit `barycorr` command construction, and `GEOCENTER` refusal.
- GoodXenon pairing checks that record `unpaired_goodxenon` instead of silently claiming conversion.
- Astropy-based local RXTE FITS event-table reading on tiny synthetic FITS fixtures.
- RXTE/PCA SingleBit high-time binned product expansion on tiny synthetic FITS fixtures.
- RXTE TT mission-time conversion for MINBAR UTC MJD validation windows.
- Manifest parsing and validation.
- MINBAR timing-window matching, observation-level reports, and validation metrics against detector summary products.
- Phase 1 validation recovery statuses for probable known detections, expected non-detection review cases, p-values, and control-FAP fields.
- Phase 1 validation-run summaries and gate checks across burst, candidate, control, and MINBAR timing products.
- Phase 2 injection/recovery product contracts, hash-linked configuration fixtures, and sensitivity-summary validation.
- Phase 1 manifest access for selected RXTE/PCA validation ObsIDs.
- Targeted event-based `Z_n^2` oscillation-search, Leahy diagnostics, first-harmonic phase/amplitude estimates, and sliding-window primitives on synthetic events.
- Deterministic targeted-search review configuration fingerprints for catalog provenance.
- Single-trial and nominal independent-trial corrected p-value helpers for `Z_n^2` timing products.
- GTI-corrected single- and multi-cadence light-curve binning plus baseline estimation on synthetic events.
- In-memory event product slicing on synthetic events.
- Time-window and GTI handling with half-open event intervals.
- Synthetic event fixtures with known burst envelopes.
- Synthetic Poisson null-control products with event-rate envelopes for false-alarm review.
- Targeted oscillation-search fixtures for later known-frequency validation windows.

Large mission data products must not be committed as fixtures. Use tiny synthetic data or documented external-data skips.

## Current Checks

Run the manifest validation check with:

```powershell
python tests\validate_manifests.py
```

The check uses only the Python standard library and validates tracked CSV schemas, required fields, references, source IDs, observation rows, RXTE-only validation scope, numeric coordinates, and expected oscillation frequencies.

Run the Python test suite with:

```powershell
python -m pytest
```

The suite now covers the local RXTE validation skeleton, strict Phase 1 closeout guardrails, and the first Phase 2 injection/recovery contract fixtures. Large external mission products remain ignored; the real-data runner documents those outputs under `data/products/phase1_real_validation/`.
