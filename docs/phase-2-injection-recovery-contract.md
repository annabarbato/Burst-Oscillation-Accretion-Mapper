# Phase 2 Injection/Recovery Product Contract

Last updated: 2026-05-24

This note defines the first Phase 2 product boundary before broad simulation
machinery is added. It is owned by the Phase 2 roadmap item for selection
function and injection/recovery. The implementation contract lives in
`src/burst_oscillation_accretion_mapper/injection_recovery_contract.py`, with a
small tracked fixture at
`tests/fixtures/phase2/injection_recovery_contract.json`.

## Scope

The contract defines what future injection/recovery runners must emit:

- `InjectionGridSpec`: the deterministic grid and provenance payload for a run.
- `InjectionTrialProduct`: one synthetic signal attempt and its recovery result.
- `BurstSensitivityProduct`: aggregate amplitude thresholds and upper-limit
  metadata for one burst, phase, and energy band.
- `InjectionRecoveryFixture`: a tiny tracked JSON example that validates the
  product shapes without requiring mission data.

This change does not implement photon simulation, sinusoid injection, search
execution, curve fitting, interpolation, or catalog persistence. Those remain
separate Phase 2 tasks after the product shape is stable.

## Contract Requirements

Every injection/recovery product must carry:

- `search_config_hash`, so products are tied to the exact Phase 1 search grid.
- `injection_config_hash`, so stale sensitivity products can be invalidated when
  amplitudes, frequency offsets, drift models, burst phases, energy bands,
  random seeds, or count-rate envelope references change.
- `pipeline_version`, so future catalog releases can reproduce product rows.
- Source, observation, instrument, burst, energy-band, and burst-phase identity.

Trial products must store injected amplitude, frequency, pulse phase, burst
phase, drift model, drift parameters, random seed, recovery classification,
recovered statistic, recovered amplitude/frequency when available, and p-values
when the search reports them.

Sensitivity products must store `amp50`, `amp90`, `amp95`, `upper_limit_amp`,
`curve_uri`, `trial_count`, `recovered_count`, `valid_for_primary_model`, and
quality flags. A product marked valid for the primary model must have monotonic
thresholds satisfying `amp50 <= amp90 <= amp95`.

## Fixture Rules

Tracked fixtures must be tiny and synthetic. They should validate schema,
hash-linkage, monotonic thresholds, recovery labels, and non-detection/upper
limit fields. They must not include downloaded RXTE, NICER, FITS, Parquet, HDF5,
SQLite, or other mission-derived data products.

## Phase Boundary

This contract is the first Phase 2 task. The next Phase 2 tasks can build on it
by adding deterministic fixture simulations and then running injection/recovery
against the existing RXTE validation bursts. NICER/XTI remains Phase 3, and
population inference remains Phase 4.
