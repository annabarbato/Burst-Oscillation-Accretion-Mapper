# Tests

This directory is reserved for automated tests and small fixtures.

Expected early test areas:

- Configurable Poisson excess scoring, conservative interval grouping, binned morphology review, multi-cadence candidate clustering, and review summary products on synthetic light curves.
- Conservative configured scoring of targeted oscillation-search outputs into review classes.
- SQLite development catalog writes for oscillation candidate rows, scored control rows, non-detections, and nominal timing significance fields.
- Targeted control-window search/scoring checks for empirical false-alarm review.
- Deterministic pre/post-burst control intervals and empirical false-alarm summaries on scored controls.
- No-download archive planning for selected RXTE/PCA raw products.
- HEASoft/CALDB environment snapshot behavior without running mission tools.
- Local raw-product inventory and checksum behavior.
- RXTE/PCA detector-selection and barycenter provenance configuration.
- RXTE/PCA ingestion preflight behavior before FITS parsing.
- Manifest parsing and validation.
- MINBAR timing-window matching, observation-level reports, and validation metrics against detector summary products.
- Phase 1 manifest access for selected RXTE/PCA validation ObsIDs.
- Targeted event-based `Z_n^2` oscillation-search, first-harmonic phase/amplitude estimates, and sliding-window primitives on synthetic events.
- Single-trial and nominal independent-trial corrected p-value helpers for `Z_n^2` timing products.
- GTI-corrected single- and multi-cadence light-curve binning plus baseline estimation on synthetic events.
- In-memory event product slicing on synthetic events.
- Time-window and GTI handling with half-open event intervals.
- Synthetic event fixtures with known burst envelopes.
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

The initial Phase 1 test suite is intentionally small and verifies that the package skeleton imports cleanly before RXTE-specific implementation begins.
