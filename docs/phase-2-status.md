# Phase 2 Status

Last updated: 2026-05-24

Status: Started.

Phase 2 is selection-function and injection/recovery work for the RXTE
validation products produced in Phase 1. It must estimate what oscillation
amplitudes would have been detectable, attach upper limits to non-detections,
and preserve the search/injection provenance needed for later inference.

## Current Scope

The active Phase 2 scope is still RXTE/PCA-first. This phase does not add
NICER/XTI, hierarchical inference, dashboard code, or public catalog release
machinery.

## Completed In Repository

- Injection/recovery product contract for grid provenance, trial-level recovery
  products, burst-level sensitivity summaries, and JSON fixtures.
- Tiny tracked contract fixture under `tests/fixtures/phase2/`.
- Unit tests that validate hash stability, fixture loading, recovery label
  consistency, sensitivity-threshold monotonicity, and quality-flag behavior.

## Not Yet Implemented

- Event-level sinusoid injection.
- Drifted phase model generation.
- Reuse of the real Phase 1 search pipeline for injected products.
- Recovery-curve fitting or interpolation.
- Amplitude upper-limit production for all Phase 1 validation bursts.
- Catalog persistence for `injection_trial` or `burst_sensitivity` rows.

## Next Small Tasks

1. Add deterministic synthetic event fixtures with known injected amplitudes.
2. Add a minimal injection planner that expands `InjectionGridSpec` into trial
   identities and seeds without modifying event lists.
3. Add a simple recovery-curve summarizer for already-scored fixture trials.
4. Only then wire the runner into the Phase 1 RXTE validation bursts.

## Phase Gate

Phase 2 is not complete until every selected RXTE validation burst has an
injection/recovery curve or an explicit reason it cannot be produced, and every
non-detection has an upper-limit product suitable for later censored-amplitude
inference.
