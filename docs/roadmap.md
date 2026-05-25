# Burst-Oscillation Accretion Mapper Roadmap

Last verified: 2026-05-24

## Build Strategy

Build the analyzer in the order that reduces scientific risk fastest:

1. Validate on RXTE/PCA with MINBAR ground truth.
2. Add injection/recovery before making correlation claims.
3. Add NICER/XTI only after the core detector and selection function are stable.
4. Fit source-aware, instrument-aware, sensitivity-aware models.
5. Release a reusable catalog and dashboard.

The project should not begin as a neural-net classifier or a broad kHz peak scanner. The first publishable artifact is a defensible, reproducible, selection-function-corrected catalog of thermonuclear bursts, burst-oscillation candidates, non-detections, sensitivity curves, and accretion-state features.

## Phase 0: Repository And Science Foundation

Objective: establish a repo and data foundation that can support reproducible science.

Deliverables:

- `docs/architecture.md` and this roadmap.
- Source-list seed file design for known thermonuclear bursters, known spins/burst-oscillation frequencies, coordinates, and ephemeris references.
- Validation-target list for the RXTE MVP, prioritizing 3-5 known burst-oscillation sources with MINBAR coverage.
- Environment decision: local HEASoft/NICERDAS installation plus Python environment, with later Docker or Apptainer packaging.
- Citation/source tracking policy for mission status, instrument specs, catalog claims, and literature ephemerides.
- Initial repository structure proposal for `src/`, `tests/`, `pipelines/`, `docs/`, `notebooks/`, and `data/` manifests.

Acceptance criteria:

- A new contributor can explain the scientific question, why selection correction is mandatory, and why RXTE comes first.
- Required external tools and data sources are identified before code is written.
- Current mission/catalog claims are timestamped and linked to authoritative sources.

Validation checks:

- Confirm RXTE/PCA and NICER/XTI instrument assumptions against HEASARC.
- Confirm MINBAR counts and validation utility against the MINBAR paper.
- Confirm Stingray supports the required timing primitives.

Scientific risks:

- Over-scoping before the RXTE MVP exists.
- Treating source metadata, ephemerides, and calibration caveats as informal notes instead of versioned inputs.

## Phase 1: RXTE Validation MVP

Objective: reproduce known RXTE burst and burst-oscillation behavior before adding modern extensions.

Implementation deliverables:

- RXTE ingestion backend for event-mode and GoodXenon products.
- Local archive manifest with ObsID, source, raw URI, checksums, and product paths.
- Screening and GTI application with PCU/detector selection metadata.
- Barycenter correction workflow and correction provenance.
- Burst detector using multi-cadence light curves, robust local baseline estimation, Poisson likelihood tests, matched filters, and morphology filters.
- Oscillation search using event-based `Z_1^2`, `Z_n^2`, Leahy power diagnostics, dynamic power spectra, sliding windows, and targeted search ranges around known source frequencies.
- Candidate scoring with secure, probable, marginal, and non-detection classes.
- Catalog writer for initial PostgreSQL or SQLite-backed development tables, with migration path to PostgreSQL.
- Control intervals: pre-burst, post-burst, neighboring non-burst intervals, and synthetic Poisson envelopes.

Minimum target:

- 3-5 known RXTE burst-oscillation sources.
- Known strong detections recovered.
- Known non-detections represented with upper-limit placeholders.
- MINBAR burst timings matched with high recall on selected validation ObsIDs.
- False positives estimated on controls before any population claims.

Acceptance criteria:

- Burst detector finds selected MINBAR bursts with high recall and acceptable review burden.
- Oscillation search recovers known strong candidates at expected frequencies and burst phases.
- Trials-corrected false-positive behavior is measured on control intervals.
- Every candidate row stores search mode, trials accounting, energy band, window, statistic, amplitude, phase, and provenance.
- Every non-detection has a catalog row or burst-level status that can later attach sensitivity products.

Validation checks:

- Compare detected burst start/peak/end times to MINBAR for selected RXTE ObsIDs.
- Compare recovered oscillation frequencies, amplitudes, and burst phases to MINBAR/literature values where available.
- Verify that pre-burst controls do not produce accepted secure detections at the configured threshold.
- Run deterministic fixture tests on synthetic event streams with known injected signals.

Scientific risks:

- RXTE mode heterogeneity can complicate event extraction and energy-channel mapping.
- Deadtime, detector selection, and background effects can bias burst brightness and amplitude estimates.
- A too-broad blind search in Phase 1 can bury validation under trials penalties; keep Phase 1 primarily targeted.

## Phase 2: Selection Function And Injection/Recovery

Objective: estimate what oscillation amplitudes would have been detectable in each burst.

Implementation deliverables:

- Injection engine for synthetic sinusoidal oscillations in event data or event simulations.
- Support for constant, linear, exponential, and quadratic drift injections.
- Injection dimensions for amplitude, frequency, drift, burst phase, energy band, and count-rate envelope.
- Reuse of the exact real-data search pipeline for recovery.
- Burst-level sensitivity summaries: `amp50`, `amp90`, `amp95`, upper limits, and recovery curves.
- Sensitivity quality flags for insufficient counts, bad background, incomplete GTIs, and unstable search configurations.
- Versioned `search_config_hash` and `pipeline_version` for all injection products.

Acceptance criteria:

- Every RXTE validation burst has an injection/recovery curve or an explicit reason it cannot be produced.
- Non-detections produce upper limits rather than empty candidate tables.
- Recovered amplitude and frequency biases are quantified on synthetic fixtures.
- Detection probability is monotonically sensible with amplitude for normal bursts, with flagged exceptions.
- Candidate classifications can reference sensitivity products.

Validation checks:

- Inject known-amplitude signals into real burst envelopes and recover them at the expected rate.
- Inject into pre-burst/non-burst controls to estimate empirical false alarms.
- Confirm that changing the search grid changes the search configuration hash and invalidates stale sensitivity products.
- Compare analytic expectations for simple Poisson event simulations against empirical recovery curves.

Scientific risks:

- Injection into already-modulated or non-Poisson data can bias sensitivity if controls are poorly chosen.
- Sensitivity is phase-dependent; a single burst-level threshold is useful but insufficient for detailed inference.
- Computational cost can grow quickly across bursts, amplitudes, windows, frequencies, and drift templates.

## Phase 3: NICER/XTI Backend

Objective: extend the validated pipeline to NICER archival data with calibration caveats treated as first-class metadata.

Implementation deliverables:

- NICER observation discovery and local archive manifest.
- NICERDAS/HEASoft screening integration or ingestion of calibrated event files.
- Detector selection, GTI, ISS filtering, day/night state, light-leak caveat, and background metadata.
- Barycenter correction workflow and provenance.
- NICER light curves in broad and energy-resolved bands.
- NICER burst detector tuned for soft response and instrument-specific background behavior.
- NICER spectral products for pre-burst and burst intervals where count rates support them.
- NICER-specific validation fixtures using public observations with known bursts or published timing behavior.

Acceptance criteria:

- NICER event products match expected time, energy, GTI, and detector metadata.
- Burst detection works on selected NICER observations without RXTE-specific assumptions.
- Screening and calibration caveats are visible in catalog tables and downstream plots.
- NICER candidates and non-detections pass through the same scoring and injection/recovery framework as RXTE.

Validation checks:

- Compare NICER light curves and spectra against NICERDAS products for selected ObsIDs.
- Check barycentered event times and time systems against HEASoft outputs.
- Verify background and light-leak flags appear in observation quality metadata.
- Run injection/recovery on NICER event envelopes and compare sensitivity behavior to photon statistics.

Scientific risks:

- NICER's soft response and background model differ strongly from RXTE/PCA.
- Light-leak and pointing-performance caveats can create observation-dependent selection effects.
- Existing archival NICER data are valuable, but as verified on 2026-05-24, new science observations have been suspended since 2025-06-17.

## Phase 4: Correlation And Inference Engine

Objective: answer the science question with sensitivity-aware population models rather than naive correlations.

Implementation deliverables:

- Feature table joining burst morphology, pre-burst accretion proxies, spectral features, source metadata, candidate classes, and sensitivity summaries.
- Hierarchical detection model with source-level effects, instrument effects, photon-statistics controls, and sensitivity terms.
- Censored amplitude model using upper limits from injection/recovery for non-detections.
- Frequency-drift model for secure detections and predeclared probable detections.
- Optional models for oscillation burst phase, harmonic content, and energy dependence.
- Posterior predictive checks and model diagnostics.
- Reproducible notebooks or scripts for paper-ready figures.

Acceptance criteria:

- Primary claims use models that control for source identity, instrument, photon statistics, and sensitivity.
- Non-detections contribute to detection and amplitude inference.
- Model inputs are generated from catalog tables, not hand-curated spreadsheets.
- Results are reproducible from a frozen catalog release and pipeline version.

Validation checks:

- Run simulated population tests with known injected dependencies.
- Confirm the model does not recover spurious accretion-state correlations when only sensitivity changes.
- Run leave-one-source-out and leave-one-instrument-out sensitivity tests.
- Compare simple summaries to hierarchical results and document where they differ.

Scientific risks:

- Source-level heterogeneity can dominate population-level trends.
- Accretion proxies may be instrument-dependent or poorly calibrated across missions.
- PRE, burst morphology, and accretion state can be correlated, requiring cautious interpretation.

## Phase 5: Public Database And Dashboard

Objective: make the catalog usable by collaborators and, eventually, external researchers.

Implementation deliverables:

- PostgreSQL release schema and migrations.
- Read-only dashboard backed by catalog tables and file-backed products.
- Source page with source metadata, known spin, observations, bursts, and summary plots.
- Burst list with morphology, pre-burst state, detection class, and sensitivity.
- Burst detail page with light curve, hardness evolution, dynamic power spectrum, candidates, controls, and injection/recovery plot.
- Candidate viewer with frequency, amplitude, phase, drift fit, significance, controls, and classification rationale.
- Population plots for detection probability, amplitude, drift, burst phase, and accretion-state predictors.
- Exports to CSV, Parquet, and FITS where practical.
- Data dictionary and release notes.

Acceptance criteria:

- Dashboard reads from released catalog products and does not recompute science results.
- Every displayed candidate links to its burst, observation, source, search configuration, and review products.
- Exported tables include enough provenance to cite the release in external work.
- Public-facing documentation distinguishes secure, probable, marginal, and non-detection classes.

Validation checks:

- Cross-check dashboard counts against SQL queries.
- Verify exported tables round-trip into analysis notebooks.
- Spot-check source pages against raw catalog rows.
- Confirm no unreleased local paths or private credentials leak into public exports.

Scientific risks:

- Dashboard polish can distract from catalog correctness.
- Review products may be large; storage and caching need explicit design.
- Public users may overinterpret marginal candidates unless classes and caveats are prominent.

## Phase 6: Publication And Catalog Release

Objective: package the analyzer and catalog into a publishable scientific result.

Implementation deliverables:

- Frozen catalog release with DOI-ready data package.
- Reproducible environment definition and pipeline version tag.
- Paper figure scripts:
  - Pipeline diagram.
  - Recovery of known RXTE burst oscillations.
  - Detection sensitivity versus burst photon count.
  - Detection probability versus pre-burst accretion proxy.
  - Fractional rms amplitude versus hardness.
  - Frequency drift versus burst rise time, peak temperature, or PRE flag.
  - NICER candidate gallery if validated candidates exist.
- Methods appendix describing trials correction, controls, injection/recovery, candidate classes, and hierarchical models.
- Known limitations and caveats page.

Acceptance criteria:

- Main result can be stated as: after controlling for photon statistics, source identity, instrument response, and selection effects, burst-oscillation detectability/amplitude/frequency drift does or does not depend on accretion state and burst morphology.
- All paper figures can be regenerated from the frozen release.
- Candidate classifications and model inputs are reproducible from documented commands.
- Catalog release includes non-detections and sensitivity curves, not just detections.

Validation checks:

- Independent rerun of the frozen pipeline on a subset reproduces catalog rows.
- Paper tables match released database exports.
- Sensitivity analyses do not overturn the main claim without being documented.
- External collaborator review of candidate classes and caveats.

Scientific risks:

- Population trends may be null after sensitivity correction; this is still publishable if the upper limits and model constraints are strong.
- Literature ephemerides and source classifications may change; release notes must freeze the inputs used.
- NICER candidates should not be oversold if calibration or background caveats dominate.

## Cross-Cutting Engineering Workstreams

Data provenance:

- Every science row must carry software version, calibration version, screening hash, search configuration hash, and raw product reference.
- Any manual review or override must be recorded as data, not hidden in notebooks.

Testing:

- Unit tests for event slicing, GTI handling, time windows, p-value/trials calculations, and amplitude conversions.
- Synthetic event fixtures with known burst envelopes and injected oscillations.
- Regression tests against selected MINBAR RXTE bursts.
- Database migration tests and catalog export round-trip tests.

Performance:

- Start with correctness on a small RXTE set.
- Add parallel execution only after search products and sensitivity curves are reproducible.
- Cache expensive intermediate products by content hash and search configuration.

Review workflow:

- Secure and probable detections should have generated review packets: light curve, dynamic power spectrum, phase evolution, drift fit, controls, and injection/recovery summary.
- Marginal candidates remain visible but excluded from primary models by default.
- Non-detections should receive the same sensitivity review status as detections.

## Near-Term Implementation Order

The first coding sequence after these docs should be:

1. Create Python project skeleton, environment files, and basic CI.
2. Add source/observation manifest schema and a tiny RXTE validation manifest.
3. Implement event-product abstraction and RXTE event ingestion for one known source.
4. Build multi-cadence light curves and the first burst detector.
5. Match detected bursts against MINBAR rows.
6. Implement targeted `Z_1^2`/`Z_n^2` search for known-frequency validation bursts.
7. Add candidate catalog writes and review products.
8. Add control intervals and empirical false-alarm checks.
9. Add injection/recovery for the same selected RXTE bursts.
10. Only then widen source coverage or start NICER work.

## Definition Of Done For V1

V1 is complete when:

- RXTE validation sources run end-to-end from event products to burst catalog, candidate catalog, controls, and injection/recovery sensitivity.
- Known strong oscillations are recovered and known non-detections are represented with upper limits.
- False-positive behavior is measured on controls.
- The first hierarchical detection model can be run on the validation set, even if it is not yet scientifically definitive.
- The repo can produce a small reproducible catalog release from documented commands.

## Reference Notes

Claims in this document were checked on 2026-05-24 against sources tracked in
`data/manifests/references.csv`:

- `nicer_heasarc_status`: NICER current status and mission page, https://heasarc.gsfc.nasa.gov/docs/nicer/
- `nasa_nicer_status_updates`: NASA NICER status updates, https://www.nasa.gov/missions/station/nicer-status-updates/
- `nicer_instrument_heasarc`: NICER instrument specs, https://heasarc.gsfc.nasa.gov/docs/heasarc/missions/nicer.html
- `nicer_analysis_docs`: NICERDAS and NICER analysis documentation, https://heasarc.gsfc.nasa.gov/docs/nicer/nicer_analysis.html
- `rxte_pca_heasarc`: RXTE/PCA specs, https://heasarc.gsfc.nasa.gov/docs/xte/PCA.html
- `minbar_paper`: MINBAR paper, https://arxiv.org/abs/2003.00685
- `minbar_home`: MINBAR home, https://burst.sci.monash.edu/wiki/index.php?n=MINBAR.Home
- `stingray_docs`: Stingray documentation, https://docs.stingray.science/en/stable/
- `heasoft_docs`: HEASoft mission-tool documentation, https://heasarc.gsfc.nasa.gov/lheasoft/index.html
- `caldb_docs`: HEASARC CALDB documentation, https://heasarc.gsfc.nasa.gov/docs/heasarc/caldb/caldb_doc.html
