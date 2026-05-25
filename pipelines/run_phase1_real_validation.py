"""Run the Phase 1 RXTE real-data validation set.

This runner uses local ignored RXTE products under ``data/raw`` and writes
ignored review artifacts under ``data/products``. It stays inside Phase 1:
RXTE/PCA validation, burst recovery, targeted known-frequency searches,
controls, catalog rows, and the Phase 1 validation gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from burst_oscillation_accretion_mapper.burst_detection import (
    BurstDetectionConfig,
    MorphologyReviewConfig,
    find_multi_cadence_burst_clusters,
    summarize_multi_cadence_candidate_clusters,
)
from burst_oscillation_accretion_mapper.candidate_scoring import (
    CandidateEvidenceFlags,
    CandidateScoringConfig,
    score_sliding_targeted_z2_result,
)
from burst_oscillation_accretion_mapper.catalog_writer import (
    BurstCatalogWriteContext,
    CandidateCatalogWriteContext,
    ControlCatalogWriteContext,
    burst_catalog_row_from_summary,
    candidate_catalog_row_from_review,
    control_catalog_row_from_review,
    write_burst_catalog_row,
    write_candidate_catalog_row,
    write_control_catalog_row,
)
from burst_oscillation_accretion_mapper.control_checks import (
    build_search_and_score_synthetic_poisson_controls,
    build_search_and_score_pre_post_controls,
    search_and_score_control_windows,
)
from burst_oscillation_accretion_mapper.control_intervals import (
    ControlWindowConfig,
    NeighboringControlWindowConfig,
    build_neighboring_non_burst_control_windows,
    summarize_control_reviews,
)
from burst_oscillation_accretion_mapper.event_products import EventProductProvenance
from burst_oscillation_accretion_mapper.lightcurves import make_multi_cadence_light_curves
from burst_oscillation_accretion_mapper.manifests import (
    ValidationTargetContext,
    load_phase1_manifests,
)
from burst_oscillation_accretion_mapper.minbar_matching import (
    DetectedBurstWindow,
    MinbarBurstWindow,
    match_detected_bursts_by_observation,
)
from burst_oscillation_accretion_mapper.oscillation_search import (
    SlidingWindowConfig,
    TargetedFrequencyGrid,
    TargetedZ2SearchConfig,
    search_event_product_sliding_targeted_z2,
)
from burst_oscillation_accretion_mapper.phase1_validation import (
    Phase1ValidationGatePolicy,
    review_phase1_validation_gate,
    summarize_phase1_validation_catalog,
)
from burst_oscillation_accretion_mapper.phase1_recovery import (
    classify_phase1_recovery,
)
from burst_oscillation_accretion_mapper.rxte_archive import mirror_phase1_rxte_observation
from burst_oscillation_accretion_mapper.rxte_binned import (
    read_rxte_singlebit_event_product,
)
from burst_oscillation_accretion_mapper.rxte_corrections import (
    BARYCORR_ALREADY_APPLIED,
    BARYCORR_APPLIED,
    NO_EPHEMERIS,
    RxteCorrectionResult,
    correction_result_to_json,
    run_rxte_barycorr,
)
from burst_oscillation_accretion_mapper.rxte_fits import read_rxte_fits_event_product
from burst_oscillation_accretion_mapper.rxte_goodxenon import (
    run_make_se_if_paired,
)
from burst_oscillation_accretion_mapper.rxte_product_selection import (
    RxteProductSelection,
    rxte_filename_time_interval,
    select_rxte_phase1_product,
)
from burst_oscillation_accretion_mapper.synthetic_controls import (
    SyntheticPoissonControlConfig,
)
from burst_oscillation_accretion_mapper.rxte_time import utc_mjd_to_rxte_met
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


PIPELINE_VERSION = "phase1-strict-closeout-2026-05-24"


@dataclass(frozen=True)
class RealValidationCase:
    source_id: str
    obs_id: str
    minbar_burst_id: str
    minbar_mjd_utc: float
    rise_s: float
    duration_s: float
    expected_frequency_hz: float
    expected_signal: str
    reader: str
    product_path: str


VALIDATION_CASES = (
    RealValidationCase(
        source_id="4u_1636_536",
        obs_id="10088-01-07-02",
        minbar_burst_id="MINBAR.2257",
        minbar_mjd_utc=50445.94401,
        rise_s=2.0,
        duration_s=18.9,
        expected_frequency_hz=581.0,
        expected_signal="secure_detection",
        reader="fits",
        product_path="data/raw/rxte/10088-01-07-02/pca/SE1_5a0e110-5a0e6a1.evt.gz",
    ),
    RealValidationCase(
        source_id="4u_1728_34",
        obs_id="10073-01-01-000",
        minbar_burst_id="MINBAR.2204",
        minbar_mjd_utc=50128.74874,
        rise_s=1.0,
        duration_s=20.0,
        expected_frequency_hz=363.0,
        expected_signal="secure_detection",
        reader="singlebit",
        product_path="data/raw/rxte/10073-01-01-000/pca/FS4f_3feaf00-3feba36.gz",
    ),
    RealValidationCase(
        source_id="4u_1728_34",
        obs_id="10073-01-02-000",
        minbar_burst_id="MINBAR.2206",
        minbar_mjd_utc=50129.16469,
        rise_s=3.0,
        duration_s=19.4,
        expected_frequency_hz=363.0,
        expected_signal="non_detection",
        reader="singlebit",
        product_path="data/raw/rxte/10073-01-02-000/pca/FS4f_3ff3910-3ff45e6.gz",
    ),
    RealValidationCase(
        source_id="4u_1702_429",
        obs_id="20084-02-01-000",
        minbar_burst_id="MINBAR.2322",
        minbar_mjd_utc=50648.50237,
        rise_s=1.0,
        duration_s=22.4,
        expected_frequency_hz=330.0,
        expected_signal="probable_detection",
        reader="fits",
        product_path="data/raw/rxte/20084-02-01-000/pca/SE7_6abeaa0-6abf6ff.evt.gz",
    ),
    RealValidationCase(
        source_id="ks_1731_260",
        obs_id="30061-01-02-01",
        minbar_burst_id="MINBAR.2431",
        minbar_mjd_utc=51088.58508,
        rise_s=3.0,
        duration_s=36.8,
        expected_frequency_hz=524.0,
        expected_signal="probable_detection",
        reader="fits",
        product_path="data/raw/rxte/30061-01-02-01/pca/SE1_8f0127b-8f02053.evt.gz",
    ),
)


def main() -> int:
    os.chdir(ROOT)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="data/products/phase1_real_validation",
        help="Ignored output directory for SQLite and JSON validation products.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = output_dir / "phase1_real_validation.sqlite"
    summary_path = output_dir / "summary.json"
    if sqlite_path.exists():
        sqlite_path.unlink()

    burst_rows = []
    candidate_rows = []
    control_rows = []
    expected_windows = []
    detected_windows = []
    case_summaries = []
    manifest_index = load_phase1_manifests(ROOT / "data" / "manifests")
    contexts_by_minbar = {
        context.target.minbar_burst_id: context
        for context in manifest_index.rxte_validation_contexts()
    }

    detection_configs = {
        0.25: BurstDetectionConfig(80, 8.0, 2),
        0.5: BurstDetectionConfig(60, 8.0, 1),
        1.0: BurstDetectionConfig(40, 8.0, 1),
    }
    morphology_config = MorphologyReviewConfig(
        min_excess_counts=100.0,
        min_peak_score=8.0,
    )
    scoring_config = CandidateScoringConfig(
        marginal_z2_threshold=16.0,
        probable_z2_threshold=24.0,
        secure_z2_threshold=32.0,
        max_frequency_offset_hz=5.0,
    )
    search_window_config = SlidingWindowConfig(window_size_s=4.0, step_s=1.0)
    control_window_config = ControlWindowConfig(
        pre_duration_s=20.0,
        post_duration_s=20.0,
        pre_gap_s=20.0,
        post_gap_s=20.0,
    )
    neighboring_control_config = NeighboringControlWindowConfig(
        window_duration_s=20.0,
        max_windows_before=1,
        max_windows_after=1,
        gap_s=60.0,
    )
    synthetic_control_config = SyntheticPoissonControlConfig(
        envelope_bin_size_s=1.0,
        realization_count=32,
        base_seed=0,
    )

    with sqlite3.connect(sqlite_path) as connection:
        for case in VALIDATION_CASES:
            context = contexts_by_minbar[case.minbar_burst_id]
            case_summary = _run_case(
                case,
                context=context,
                detection_configs=detection_configs,
                morphology_config=morphology_config,
                scoring_config=scoring_config,
                search_window_config=search_window_config,
                control_window_config=control_window_config,
                neighboring_control_config=neighboring_control_config,
                synthetic_control_config=synthetic_control_config,
            )
            burst_rows.append(case_summary["burst_row"])
            candidate_rows.append(case_summary["candidate_row"])
            control_rows.extend(case_summary["control_rows"])
            expected_windows.append(case_summary["expected_window"])
            detected_windows.append(case_summary["detected_window"])
            case_summaries.append(case_summary["json"])

            write_burst_catalog_row(connection, case_summary["burst_row"])
            write_candidate_catalog_row(connection, case_summary["candidate_row"])
            for control_row in case_summary["control_rows"]:
                write_control_catalog_row(connection, control_row)

    timing_report = match_detected_bursts_by_observation(
        tuple(expected_windows),
        tuple(detected_windows),
        tolerance_s=15.0,
    )
    summary = summarize_phase1_validation_catalog(
        burst_rows=tuple(burst_rows),
        candidate_rows=tuple(candidate_rows),
        control_rows=tuple(control_rows),
        timing_metrics=timing_report.metrics,
    )
    gate = review_phase1_validation_gate(
        summary,
        policy=Phase1ValidationGatePolicy(
            max_secure_control_count=0,
            max_probable_control_count=0,
            min_minbar_recall_fraction=1.0,
        ),
    )
    strict_closeout = _strict_closeout_review(gate.passed, case_summaries)

    output = {
        "pipeline_version": PIPELINE_VERSION,
        "sqlite_path": str(sqlite_path),
        "summary": asdict(summary),
        "gate": asdict(gate),
        "strict_closeout": strict_closeout,
        "cases": case_summaries,
        "timing_by_observation": [
            {
                "source_id": report.source_id,
                "obs_id": report.obs_id,
                "metrics": asdict(report.metrics),
            }
            for report in timing_report.observation_reports
        ],
    }
    summary_path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output["summary"], indent=2, sort_keys=True))
    print(f"gate_passed={gate.passed} reasons={gate.reasons}")
    print(
        "strict_closeout_passed="
        f"{strict_closeout['passed']} reasons={strict_closeout['reasons']}"
    )
    print(f"wrote {sqlite_path}")
    print(f"wrote {summary_path}")
    return 0 if strict_closeout["passed"] else 1


def _run_case(
    case: RealValidationCase,
    *,
    context: ValidationTargetContext,
    detection_configs: dict[float, BurstDetectionConfig],
    morphology_config: MorphologyReviewConfig,
    scoring_config: CandidateScoringConfig,
    search_window_config: SlidingWindowConfig,
    control_window_config: ControlWindowConfig,
    neighboring_control_config: NeighboringControlWindowConfig,
    synthetic_control_config: SyntheticPoissonControlConfig,
) -> dict[str, object]:
    minbar_start = utc_mjd_to_rxte_met(case.minbar_mjd_utc)
    expected_peak = minbar_start + case.rise_s
    expected_stop = minbar_start + case.duration_s
    burst_id = "phase1_real_" + case.minbar_burst_id.split(".")[-1]
    raw_obs_path = Path(context.observation.local_raw_path)
    processed_obs_path = Path("data") / "processed" / "rxte" / case.obs_id
    orbit_files = _ensure_orbit_files(case.obs_id)
    make_se_result = run_make_se_if_paired(
        pca_dir=raw_obs_path / "pca",
        output_dir=processed_obs_path / "make_se",
    )
    selection = select_rxte_phase1_product(
        raw_obs_path=raw_obs_path,
        processed_obs_path=processed_obs_path,
        target_time_met=minbar_start,
    )
    correction_result = _correction_result_for_selection(
        selection,
        context=context,
        orbit_files=orbit_files,
        processed_obs_path=processed_obs_path,
    )
    if correction_result.barycorr_status not in {
        BARYCORR_APPLIED,
        BARYCORR_ALREADY_APPLIED,
    }:
        raise RuntimeError(
            f"barycorr failed for {case.minbar_burst_id}: "
            f"{correction_result.stderr}"
        )
    product = _read_product(
        case,
        selection=selection,
        correction_result=correction_result,
        make_se_status=make_se_result.make_se_status,
    )
    raw_product = _read_uncorrected_product(
        case,
        selection=selection,
        raw_obs_path=raw_obs_path,
    )
    barycentric_time_offset_s = _estimate_barycentric_time_offset(
        raw_product=raw_product,
        corrected_product=product,
        raw_reference_time=minbar_start,
    )
    corrected_minbar_start = minbar_start + barycentric_time_offset_s
    expected_peak = corrected_minbar_start + case.rise_s
    expected_stop = corrected_minbar_start + case.duration_s

    light_curves = make_multi_cadence_light_curves(
        product,
        interval=TimeInterval(
            corrected_minbar_start - 120.0,
            corrected_minbar_start + 120.0,
        ),
        bin_sizes=(0.25, 0.5, 1.0),
    )
    clusters = find_multi_cadence_burst_clusters(
        light_curves,
        detection_configs=detection_configs,
        morphology_config=morphology_config,
        passed_only=True,
    )
    summaries = summarize_multi_cadence_candidate_clusters(clusters)
    if not summaries:
        raise RuntimeError(f"No burst clusters found for {case.minbar_burst_id}")
    best_summary = min(summaries, key=lambda summary: abs(summary.peak_time - expected_peak))

    burst_row = burst_catalog_row_from_summary(
        best_summary,
        context=BurstCatalogWriteContext(
            burst_id=burst_id,
            source_id=case.source_id,
            obs_id=case.obs_id,
            instrument="RXTE/PCA",
            pipeline_version=PIPELINE_VERSION,
            detection_config_id="multi_cadence_poisson_v1",
            minbar_burst_id=case.minbar_burst_id,
            provenance_note=str(correction_result.output_path),
        ),
    )

    search_config = TargetedZ2SearchConfig(
        frequency_grid=TargetedFrequencyGrid(
            center_hz=case.expected_frequency_hz,
            half_width_hz=5.0,
            step_hz=0.25,
        ),
        n_harmonics=1,
        min_photons=100,
        reference_time=corrected_minbar_start,
    )
    search_interval = TimeInterval(
        corrected_minbar_start,
        corrected_minbar_start + min(max(case.duration_s + 20.0, 45.0), 60.0),
    )
    search_result = search_event_product_sliding_targeted_z2(
        product,
        interval=search_interval,
        window_config=search_window_config,
        search_config=search_config,
    )
    candidate_review = score_sliding_targeted_z2_result(
        search_result,
        config=scoring_config,
        expected_frequency_hz=case.expected_frequency_hz,
        evidence=CandidateEvidenceFlags(physically_plausible_phase=True),
    )
    candidate_row = candidate_catalog_row_from_review(
        candidate_review,
        context=CandidateCatalogWriteContext(
            candidate_id=f"{burst_id}_candidate",
            burst_id=burst_id,
            pipeline_version=PIPELINE_VERSION,
            energy_band="full_available",
            search_config_id="targeted_z2_4s_1s_pm5hz_v1",
            provenance_note=str(correction_result.output_path),
        ),
    )

    pre_post_control_run = build_search_and_score_pre_post_controls(
        product,
        burst_window=TimeInterval(best_summary.start, best_summary.stop),
        control_config=control_window_config,
        window_config=SlidingWindowConfig(window_size_s=4.0, step_s=4.0),
        search_config=search_config,
        scoring_config=scoring_config,
        expected_frequency_hz=case.expected_frequency_hz,
        burst_id=burst_id,
        evidence=CandidateEvidenceFlags(physically_plausible_phase=False),
    )
    neighboring_controls = build_neighboring_non_burst_control_windows(
        burst_window=TimeInterval(best_summary.start, best_summary.stop),
        good_time_intervals=product.gtis,
        excluded_intervals=(TimeInterval(corrected_minbar_start, expected_stop),),
        config=neighboring_control_config,
        burst_id=burst_id,
    )
    neighboring_control_run = search_and_score_control_windows(
        product,
        controls=neighboring_controls,
        window_config=SlidingWindowConfig(window_size_s=4.0, step_s=4.0),
        search_config=search_config,
        scoring_config=scoring_config,
        expected_frequency_hz=case.expected_frequency_hz,
        evidence=CandidateEvidenceFlags(physically_plausible_phase=False),
    )
    synthetic_config = SyntheticPoissonControlConfig(
        envelope_bin_size_s=synthetic_control_config.envelope_bin_size_s,
        realization_count=synthetic_control_config.realization_count,
        base_seed=int(case.minbar_burst_id.split(".")[-1]) * 1000,
    )
    synthetic_control_run = build_search_and_score_synthetic_poisson_controls(
        product,
        reference_interval=search_interval,
        synthetic_config=synthetic_config,
        window_config=SlidingWindowConfig(window_size_s=4.0, step_s=4.0),
        search_config=search_config,
        scoring_config=scoring_config,
        expected_frequency_hz=case.expected_frequency_hz,
        burst_id=burst_id,
        evidence=CandidateEvidenceFlags(physically_plausible_phase=False),
    )
    all_control_reviews = (
        pre_post_control_run.control_reviews
        + neighboring_control_run.control_reviews
        + synthetic_control_run.control_reviews
    )
    control_summary = summarize_control_reviews(all_control_reviews)
    control_rows = tuple(
        control_catalog_row_from_review(
            control_review,
            context=ControlCatalogWriteContext(
                pipeline_version=PIPELINE_VERSION,
                energy_band="full_available",
                search_config_id="targeted_z2_control_4s_pm5hz_v1",
                provenance_note=str(correction_result.output_path),
            ),
        )
        for control_review in all_control_reviews
    )
    recovery_status = classify_phase1_recovery(
        candidate=candidate_row,
        control_rows=control_rows,
        validation_goal=context.target.validation_goal,
        expected_signal=context.target.expected_signal,
        burst_window=TimeInterval(best_summary.start, best_summary.stop),
        correction_status=correction_result.barycorr_status,
    )

    expected_window = MinbarBurstWindow(
        source_id=case.source_id,
        obs_id=case.obs_id,
        minbar_burst_id=case.minbar_burst_id,
        start=corrected_minbar_start,
        peak=expected_peak,
        stop=expected_stop,
        expected_signal=case.expected_signal,
    )
    detected_window = DetectedBurstWindow.from_summary(
        source_id=case.source_id,
        obs_id=case.obs_id,
        candidate_id=burst_id,
        summary=best_summary,
    )

    return {
        "burst_row": burst_row,
        "candidate_row": candidate_row,
        "control_rows": control_rows,
        "expected_window": expected_window,
        "detected_window": detected_window,
        "json": {
            "source_id": case.source_id,
            "obs_id": case.obs_id,
            "minbar_burst_id": case.minbar_burst_id,
            "reader": selection.reader_type,
            "product_selection": _selection_to_json(selection),
            "make_se": _make_se_to_json(make_se_result),
            "correction": correction_result_to_json(correction_result),
            "product_path": str(correction_result.output_path),
            "event_count": product.n_events,
            "barycentric_time_offset_s": barycentric_time_offset_s,
            "burst_start_delta_s": best_summary.start - corrected_minbar_start,
            "burst_peak_delta_s": best_summary.peak_time - corrected_minbar_start,
            "burst_stop_delta_s": best_summary.stop - corrected_minbar_start,
            "candidate_classification": candidate_row.classification,
            "candidate_frequency_hz": candidate_row.frequency_hz,
            "candidate_z2_power": candidate_row.z2_power,
            "p_single": candidate_row.p_single,
            "p_trials": candidate_row.p_trials,
            "recovery": asdict(recovery_status),
            "control_count": len(control_rows),
            "control_detection_like_count": control_summary.detection_like_count,
            "control_secure_count": control_summary.secure_count,
            "control_probable_count": control_summary.probable_count,
            "control_marginal_count": control_summary.marginal_count,
            "pre_post_control_count": pre_post_control_run.summary.control_count,
            "neighboring_control_count": neighboring_control_run.summary.control_count,
            "synthetic_control_count": synthetic_control_run.summary.control_count,
        },
    }


def _read_product(
    case: RealValidationCase,
    *,
    selection: RxteProductSelection,
    correction_result: RxteCorrectionResult,
    make_se_status: str,
):
    provenance = EventProductProvenance(
        raw_uri=str(selection.selected_product_path),
        software_version="HEASoft 6.36; astropy reader",
        barycorr_ref=correction_result.ephemeris,
        barycorr_applied=correction_result.barycorr_status
        in {BARYCORR_APPLIED, BARYCORR_ALREADY_APPLIED},
        binarycorr_ref=correction_result.binarycorr_status,
        binarycorr_applied=False,
        notes=(
            f"reader={selection.reader_type}; data_mode={selection.data_mode}; "
            f"selection={selection.selection_reason}; "
            f"fallback={selection.fallback_status}; make_se={make_se_status}; "
            f"binarycorr_status={correction_result.binarycorr_status}"
        ),
    )
    if selection.reader_type == "fits":
        return read_rxte_fits_event_product(
            correction_result.output_path,
            source_id=case.source_id,
            obs_id=case.obs_id,
            provenance=provenance,
        )
    if selection.reader_type == "singlebit":
        return read_rxte_singlebit_event_product(
            correction_result.output_path,
            source_id=case.source_id,
            obs_id=case.obs_id,
            provenance=provenance,
        )
    raise RuntimeError(f"Unsupported reader: {selection.reader_type}")


def _read_uncorrected_product(
    case: RealValidationCase,
    *,
    selection: RxteProductSelection,
    raw_obs_path: Path,
):
    raw_path = _raw_product_path_for_selection(selection, raw_obs_path=raw_obs_path)
    provenance = EventProductProvenance(
        raw_uri=str(raw_path),
        software_version="Astropy raw timing-offset reader",
        barycorr_applied=False,
        notes=(
            f"reader={selection.reader_type}; "
            "raw product paired with barycentered product for offset estimation"
        ),
    )
    if selection.reader_type == "fits":
        return read_rxte_fits_event_product(
            raw_path,
            source_id=case.source_id,
            obs_id=case.obs_id,
            provenance=provenance,
        )
    if selection.reader_type == "singlebit":
        return read_rxte_singlebit_event_product(
            raw_path,
            source_id=case.source_id,
            obs_id=case.obs_id,
            provenance=provenance,
        )
    raise RuntimeError(f"Unsupported reader: {selection.reader_type}")


def _raw_product_path_for_selection(
    selection: RxteProductSelection,
    *,
    raw_obs_path: Path,
) -> Path:
    if not selection.is_barycentered:
        return selection.selected_product_path

    interval = rxte_filename_time_interval(selection.selected_product_path)
    if interval is None:
        raise RuntimeError(
            f"Cannot infer raw product for {selection.selected_product_path}"
        )
    pca_path = raw_obs_path / "pca"
    if selection.reader_type == "fits":
        candidates = tuple(pca_path.glob("SE*.evt*")) + tuple(pca_path.glob("SE*.fits"))
    elif selection.reader_type == "singlebit":
        candidates = tuple(pca_path.glob("FS4f_*"))
    else:
        candidates = ()
    for candidate in sorted(candidates):
        candidate_interval = rxte_filename_time_interval(candidate)
        if candidate_interval == interval:
            return candidate
    raise RuntimeError(f"No raw counterpart found for {selection.selected_product_path}")


def _estimate_barycentric_time_offset(
    *,
    raw_product,
    corrected_product,
    raw_reference_time: float,
) -> float:
    offsets = [
        corrected_product.times[index] - raw_time
        for index, raw_time in enumerate(raw_product.times)
        if abs(raw_time - raw_reference_time) <= 60.0
        and index < len(corrected_product.times)
    ]
    if not offsets:
        offsets = [
            corrected - raw
            for raw, corrected in zip(raw_product.times[:1000], corrected_product.times[:1000])
        ]
    if not offsets:
        raise RuntimeError("Cannot estimate barycentric time offset from empty products")
    offsets.sort()
    return offsets[len(offsets) // 2]


def _ensure_orbit_files(obs_id: str) -> tuple[Path, ...]:
    raw_obs_path = Path("data") / "raw" / "rxte" / obs_id
    orbit_dir = raw_obs_path / "orbit"
    orbit_files = tuple(sorted(path for path in orbit_dir.glob("FPorbit*") if path.is_file()))
    if not orbit_files:
        mirror_phase1_rxte_observation(obs_id, raw_root=Path("data") / "raw")
        orbit_files = tuple(
            sorted(path for path in orbit_dir.glob("FPorbit*") if path.is_file())
        )
    if not orbit_files:
        raise RuntimeError(f"No RXTE orbit files found for {obs_id}")
    return orbit_files


def _correction_result_for_selection(
    selection: RxteProductSelection,
    *,
    context: ValidationTargetContext,
    orbit_files: tuple[Path, ...],
    processed_obs_path: Path,
) -> RxteCorrectionResult:
    if selection.is_barycentered:
        return RxteCorrectionResult(
            input_path=selection.selected_product_path,
            output_path=selection.selected_product_path,
            barycorr_command=(),
            barycorr_status=BARYCORR_ALREADY_APPLIED,
            ephemeris="JPLEPH.440",
            refframe="ICRS",
            orbit_files=orbit_files,
            binarycorr_status=NO_EPHEMERIS
            if not context.source.binary_ephemeris_ref
            else "not_applied_ephemeris_available",
            ra_deg=context.source.ra_deg,
            dec_deg=context.source.dec_deg,
            returncode=0,
        )
    return run_rxte_barycorr(
        input_path=selection.selected_product_path,
        output_dir=processed_obs_path / "barycorr",
        orbit_files=orbit_files,
        ra_deg=context.source.ra_deg,
        dec_deg=context.source.dec_deg,
        binary_ephemeris_ref=context.source.binary_ephemeris_ref,
        working_dir=ROOT,
        ephem="JPLEPH.440",
        refframe="ICRS",
        overwrite=False,
    )


def _selection_to_json(selection: RxteProductSelection) -> dict[str, object]:
    return {
        "selected_product_path": str(selection.selected_product_path),
        "reader_type": selection.reader_type,
        "data_mode": selection.data_mode,
        "selection_reason": selection.selection_reason,
        "fallback_status": selection.fallback_status,
        "is_barycentered": selection.is_barycentered,
    }


def _make_se_to_json(result) -> dict[str, object]:
    return {
        "input_dir": str(result.input_dir),
        "output_dir": str(result.output_dir),
        "make_se_status": result.make_se_status,
        "goodxenon1_count": result.goodxenon1_count,
        "goodxenon2_count": result.goodxenon2_count,
        "output_paths": [str(path) for path in result.output_paths],
        "command": list(result.command),
        "log_path": str(result.log_path) if result.log_path is not None else None,
        "message": result.message,
    }


def _strict_closeout_review(
    gate_passed: bool,
    case_summaries: list[dict[str, object]],
) -> dict[str, object]:
    reasons: list[str] = []
    if not gate_passed:
        reasons.append("phase1_validation_gate_failed")

    by_minbar = {str(case["minbar_burst_id"]): case for case in case_summaries}
    for minbar_id in ("MINBAR.2204", "MINBAR.2257"):
        recovery = by_minbar.get(minbar_id, {}).get("recovery", {})
        if not isinstance(recovery, dict) or recovery.get("recovery_status") != "recovered":
            reasons.append(f"{minbar_id}_known_signal_not_recovered")

    non_detection = by_minbar.get("MINBAR.2206", {})
    recovery = non_detection.get("recovery", {}) if isinstance(non_detection, dict) else {}
    if not isinstance(recovery, dict):
        reasons.append("MINBAR.2206_missing_recovery_status")
    else:
        status = recovery.get("recovery_status")
        reason_codes = tuple(recovery.get("reason_codes", ()))
        if status == "review" and "expected_non_detection_marginal_review" in reason_codes:
            pass
        elif status == "not_recovered":
            pass
        else:
            reasons.append("MINBAR.2206_not_acceptable_non_detection_review")

    for case in case_summaries:
        recovery = case.get("recovery", {})
        correction = case.get("correction", {})
        minbar_id = case.get("minbar_burst_id", "unknown")
        if case.get("p_single") is None or case.get("p_trials") is None:
            reasons.append(f"{minbar_id}_missing_p_values")
        if not isinstance(recovery, dict) or recovery.get("empirical_control_fap") is None:
            reasons.append(f"{minbar_id}_missing_empirical_control_fap")
        if (
            not isinstance(correction, dict)
            or correction.get("barycorr_status")
            not in {BARYCORR_APPLIED, BARYCORR_ALREADY_APPLIED}
        ):
            reasons.append(f"{minbar_id}_barycorr_not_applied")
        if (
            not isinstance(correction, dict)
            or correction.get("binarycorr_status") != NO_EPHEMERIS
        ):
            reasons.append(f"{minbar_id}_binarycorr_status_not_no_ephemeris")

    return {
        "passed": not reasons,
        "reasons": reasons,
    }


if __name__ == "__main__":
    raise SystemExit(main())
