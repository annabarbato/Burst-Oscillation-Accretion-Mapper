import math
import sqlite3

import pytest

from burst_oscillation_accretion_mapper.candidate_scoring import (
    NON_DETECTION,
    PROBABLE_DETECTION,
    OscillationCandidateReview,
)
from burst_oscillation_accretion_mapper.catalog_writer import (
    CONTROL_REVIEW_TABLE,
    OSCILLATION_CANDIDATE_TABLE,
    ControlCatalogWriteContext,
    CandidateCatalogWriteContext,
    CatalogWriteError,
    candidate_catalog_row_from_review,
    control_catalog_row_from_review,
    initialize_candidate_catalog,
    initialize_control_catalog,
    read_candidate_catalog_rows,
    read_control_catalog_rows,
    write_candidate_review,
    write_control_review,
    write_control_search_run,
)
from burst_oscillation_accretion_mapper.control_checks import ControlSearchRun
from burst_oscillation_accretion_mapper.control_intervals import (
    POST_BURST_CONTROL,
    PRE_BURST_CONTROL,
    ControlReview,
    ControlWindowConfig,
    build_pre_post_control_windows,
    summarize_control_reviews,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_candidate_catalog_row_from_review_preserves_required_fields() -> None:
    review = _probable_review()
    context = CandidateCatalogWriteContext(
        candidate_id="candidate-001",
        burst_id="burst-001",
        energy_band="2-20 keV",
        pipeline_version="phase1-test",
        search_config_id="targeted-581hz",
        provenance_note="synthetic fixture",
    )

    row = candidate_catalog_row_from_review(review, context=context)

    assert row.candidate_id == "candidate-001"
    assert row.burst_id == "burst-001"
    assert row.source_id == "source"
    assert row.obs_id == "obs"
    assert row.instrument == "RXTE/PCA"
    assert row.search_mode == "targeted_known_frequency"
    assert row.classification == PROBABLE_DETECTION
    assert row.trial_count == 5
    assert row.energy_band == "2-20 keV"
    assert row.window_start == 10.0
    assert row.window_stop == 12.0
    assert row.frequency_hz == 581.0
    assert row.expected_frequency_hz == 581.0
    assert row.z2_power == 42.0
    assert row.p_single == pytest.approx(math.exp(-21.0))
    assert row.p_trials == pytest.approx(1.0 - (1.0 - math.exp(-21.0)) ** 5)
    assert row.fractional_rms == 0.12
    assert row.phase_rad == 1.25
    assert row.reasons == ("z2_below_secure_threshold",)
    assert row.pipeline_version == "phase1-test"
    assert row.search_config_id == "targeted-581hz"
    assert row.provenance_note == "synthetic fixture"


def test_write_candidate_review_round_trips_detection_and_non_detection() -> None:
    connection = sqlite3.connect(":memory:")
    probable_row = write_candidate_review(
        connection,
        _probable_review(),
        context=CandidateCatalogWriteContext(
            candidate_id="candidate-002",
            burst_id="burst-001",
            energy_band="broad",
            pipeline_version="phase1-test",
            search_config_id="targeted",
        ),
    )
    non_detection_row = write_candidate_review(
        connection,
        _non_detection_review(),
        context=CandidateCatalogWriteContext(
            candidate_id="candidate-001",
            burst_id="burst-002",
            pipeline_version="phase1-test",
        ),
    )

    rows = read_candidate_catalog_rows(connection)

    assert rows == (non_detection_row, probable_row)
    assert rows[0].classification == NON_DETECTION
    assert rows[0].window_start is None
    assert rows[0].frequency_hz is None
    assert rows[0].z2_power is None
    assert rows[0].p_single is None
    assert rows[0].p_trials is None
    assert rows[0].reasons == ("no_searched_windows",)
    assert rows[1].p_single == pytest.approx(math.exp(-21.0))
    assert rows[1].p_trials == pytest.approx(1.0 - (1.0 - math.exp(-21.0)) ** 5)


def test_initialize_candidate_catalog_creates_expected_table() -> None:
    connection = sqlite3.connect(":memory:")

    initialize_candidate_catalog(connection)

    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert OSCILLATION_CANDIDATE_TABLE in table_names

    columns = {
        row[1]
        for row in connection.execute(
            f"PRAGMA table_info({OSCILLATION_CANDIDATE_TABLE})"
        )
    }
    assert "p_single" in columns
    assert "p_trials" in columns


def test_control_catalog_row_from_review_preserves_control_and_review_fields() -> None:
    control_review = ControlReview(
        control=_control_windows()[0],
        review=_probable_review(),
    )
    context = ControlCatalogWriteContext(
        energy_band="2-20 keV",
        pipeline_version="phase1-test",
        search_config_id="targeted-581hz",
        provenance_note="synthetic fixture",
    )

    row = control_catalog_row_from_review(control_review, context=context)

    assert row.control_id == "burst-001_pre_burst_001"
    assert row.burst_id == "burst-001"
    assert row.control_kind == PRE_BURST_CONTROL
    assert row.control_start == 80.0
    assert row.control_stop == 100.0
    assert row.requested_start == 80.0
    assert row.requested_stop == 100.0
    assert row.source_id == "source"
    assert row.obs_id == "obs"
    assert row.instrument == "RXTE/PCA"
    assert row.classification == PROBABLE_DETECTION
    assert row.energy_band == "2-20 keV"
    assert row.z2_power == 42.0
    assert row.p_single == pytest.approx(math.exp(-21.0))
    assert row.p_trials == pytest.approx(1.0 - (1.0 - math.exp(-21.0)) ** 5)
    assert row.pipeline_version == "phase1-test"
    assert row.search_config_id == "targeted-581hz"
    assert row.provenance_note == "synthetic fixture"


def test_write_control_search_run_round_trips_detection_and_non_detection() -> None:
    connection = sqlite3.connect(":memory:")
    controls = _control_windows()
    control_reviews = (
        ControlReview(control=controls[0], review=_probable_review()),
        ControlReview(control=controls[1], review=_non_detection_review()),
    )
    run = ControlSearchRun(
        control_reviews=control_reviews,
        summary=summarize_control_reviews(control_reviews),
    )

    written_rows = write_control_search_run(
        connection,
        run,
        context=ControlCatalogWriteContext(
            energy_band="broad",
            pipeline_version="phase1-test",
            search_config_id="targeted",
        ),
    )

    rows = read_control_catalog_rows(connection)

    assert rows == tuple(sorted(written_rows, key=lambda row: row.control_id))
    assert [row.control_kind for row in rows] == [
        POST_BURST_CONTROL,
        PRE_BURST_CONTROL,
    ]
    assert rows[0].classification == NON_DETECTION
    assert rows[0].window_start is None
    assert rows[0].p_single is None
    assert rows[1].classification == PROBABLE_DETECTION
    assert rows[1].p_single == pytest.approx(math.exp(-21.0))


def test_initialize_control_catalog_creates_expected_table() -> None:
    connection = sqlite3.connect(":memory:")

    initialize_control_catalog(connection)

    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert CONTROL_REVIEW_TABLE in table_names

    columns = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({CONTROL_REVIEW_TABLE})")
    }
    assert "control_id" in columns
    assert "control_kind" in columns
    assert "p_trials" in columns


def test_write_candidate_review_rejects_duplicate_candidate_id() -> None:
    connection = sqlite3.connect(":memory:")
    context = CandidateCatalogWriteContext(
        candidate_id="candidate-001",
        pipeline_version="phase1-test",
    )

    write_candidate_review(connection, _probable_review(), context=context)

    with pytest.raises(sqlite3.IntegrityError):
        write_candidate_review(connection, _probable_review(), context=context)


def test_write_control_review_rejects_duplicate_control_id() -> None:
    connection = sqlite3.connect(":memory:")
    context = ControlCatalogWriteContext(pipeline_version="phase1-test")
    control_review = ControlReview(
        control=_control_windows()[0],
        review=_probable_review(),
    )

    write_control_review(connection, control_review, context=context)

    with pytest.raises(sqlite3.IntegrityError):
        write_control_review(connection, control_review, context=context)


def test_candidate_catalog_write_context_requires_identity() -> None:
    with pytest.raises(CatalogWriteError, match="candidate_id"):
        CandidateCatalogWriteContext(candidate_id="", pipeline_version="phase1-test")

    with pytest.raises(CatalogWriteError, match="pipeline_version"):
        CandidateCatalogWriteContext(candidate_id="candidate", pipeline_version="")

    with pytest.raises(CatalogWriteError, match="pipeline_version"):
        ControlCatalogWriteContext(pipeline_version="")


def test_candidate_catalog_row_from_review_validates_numeric_fields() -> None:
    review = OscillationCandidateReview(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode="targeted_known_frequency",
        classification=PROBABLE_DETECTION,
        trial_count=-1,
        photon_count=20,
        window=TimeInterval(10.0, 12.0),
        frequency_hz=581.0,
        expected_frequency_hz=581.0,
        frequency_offset_hz=0.0,
        z2_power=42.0,
        n_harmonics=1,
        fractional_rms=0.12,
        phase_rad=1.25,
        reasons=(),
    )

    with pytest.raises(CatalogWriteError, match="trial_count"):
        candidate_catalog_row_from_review(
            review,
            context=CandidateCatalogWriteContext(
                candidate_id="candidate",
                pipeline_version="phase1-test",
            ),
        )


def test_candidate_catalog_row_from_review_requires_harmonic_metadata_for_power() -> None:
    review = OscillationCandidateReview(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode="targeted_known_frequency",
        classification=PROBABLE_DETECTION,
        trial_count=5,
        photon_count=20,
        window=TimeInterval(10.0, 12.0),
        frequency_hz=581.0,
        expected_frequency_hz=581.0,
        frequency_offset_hz=0.0,
        z2_power=42.0,
        n_harmonics=None,
        fractional_rms=0.12,
        phase_rad=1.25,
        reasons=(),
    )

    with pytest.raises(CatalogWriteError, match="n_harmonics"):
        candidate_catalog_row_from_review(
            review,
            context=CandidateCatalogWriteContext(
                candidate_id="candidate",
                pipeline_version="phase1-test",
            ),
        )


def _probable_review() -> OscillationCandidateReview:
    return OscillationCandidateReview(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode="targeted_known_frequency",
        classification=PROBABLE_DETECTION,
        trial_count=5,
        photon_count=20,
        window=TimeInterval(10.0, 12.0),
        frequency_hz=581.0,
        expected_frequency_hz=581.0,
        frequency_offset_hz=0.0,
        z2_power=42.0,
        n_harmonics=1,
        fractional_rms=0.12,
        phase_rad=1.25,
        reasons=("z2_below_secure_threshold",),
    )


def _non_detection_review() -> OscillationCandidateReview:
    return OscillationCandidateReview(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode="targeted_known_frequency",
        classification=NON_DETECTION,
        trial_count=0,
        photon_count=0,
        window=None,
        frequency_hz=None,
        expected_frequency_hz=581.0,
        frequency_offset_hz=None,
        z2_power=None,
        n_harmonics=None,
        fractional_rms=None,
        phase_rad=None,
        reasons=("no_searched_windows",),
    )


def _control_windows():
    return build_pre_post_control_windows(
        burst_window=TimeInterval(100.0, 110.0),
        good_time_intervals=(TimeInterval(0.0, 200.0),),
        config=ControlWindowConfig(pre_duration_s=20.0, post_duration_s=20.0),
        burst_id="burst-001",
    )
