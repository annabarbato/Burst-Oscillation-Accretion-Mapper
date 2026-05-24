import pytest

from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.oscillation_search import (
    TARGETED_SEARCH_MODE,
    OscillationSearchError,
    SlidingWindowConfig,
    TargetedFrequencyGrid,
    TargetedZ2SearchConfig,
    make_sliding_windows,
    search_event_product_sliding_targeted_z2,
    search_event_product_targeted_z2,
    z_n_squared,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_z_n_squared_is_large_for_phase_aligned_events() -> None:
    times = tuple(index * 0.1 for index in range(10))

    power = z_n_squared(times, frequency_hz=10.0)

    assert power == pytest.approx(20.0)


def test_z_n_squared_includes_requested_harmonics() -> None:
    times = tuple(index * 0.1 for index in range(10))

    power = z_n_squared(times, frequency_hz=10.0, n_harmonics=2)

    assert power == pytest.approx(40.0)


def test_z_n_squared_validates_inputs() -> None:
    with pytest.raises(OscillationSearchError, match="At least one event"):
        z_n_squared((), frequency_hz=10.0)

    with pytest.raises(OscillationSearchError, match="frequency_hz"):
        z_n_squared((0.0,), frequency_hz=0.0)

    with pytest.raises(OscillationSearchError, match="n_harmonics"):
        z_n_squared((0.0,), frequency_hz=10.0, n_harmonics=0)


def test_targeted_frequency_grid_accepts_low_frequency_burst_oscillation() -> None:
    grid = TargetedFrequencyGrid(center_hz=45.0, half_width_hz=0.5, step_hz=0.25)

    assert grid.frequencies_hz == (44.5, 44.75, 45.0, 45.25, 45.5)


def test_targeted_frequency_grid_always_includes_center() -> None:
    grid = TargetedFrequencyGrid(center_hz=581.0, half_width_hz=0.2, step_hz=1.0)

    assert grid.frequencies_hz == (581.0,)


def test_targeted_frequency_grid_validates_inputs() -> None:
    with pytest.raises(OscillationSearchError, match="center_hz"):
        TargetedFrequencyGrid(center_hz=0.0, half_width_hz=1.0, step_hz=0.5)

    with pytest.raises(OscillationSearchError, match="half_width_hz"):
        TargetedFrequencyGrid(center_hz=10.0, half_width_hz=-1.0, step_hz=0.5)

    with pytest.raises(OscillationSearchError, match="step_hz"):
        TargetedFrequencyGrid(center_hz=10.0, half_width_hz=1.0, step_hz=0.0)


def test_search_event_product_targeted_z2_finds_best_frequency() -> None:
    product = _phase_aligned_product()
    config = TargetedZ2SearchConfig(
        frequency_grid=TargetedFrequencyGrid(
            center_hz=10.0,
            half_width_hz=2.0,
            step_hz=1.0,
        ),
        n_harmonics=1,
        min_photons=5,
    )

    result = search_event_product_targeted_z2(
        product,
        window=TimeInterval(0.0, 1.0),
        config=config,
    )

    assert result.source_id == "source"
    assert result.obs_id == "obs"
    assert result.instrument == "RXTE/PCA"
    assert result.search_mode == TARGETED_SEARCH_MODE
    assert result.photon_count == 10
    assert result.n_harmonics == 1
    assert result.effective_exposure_s == 1.0
    assert tuple(power.frequency_hz for power in result.powers) == (
        8.0,
        9.0,
        10.0,
        11.0,
        12.0,
    )
    assert result.best_frequency_hz == 10.0
    assert result.best_z2_power == pytest.approx(20.0)


def test_search_event_product_targeted_z2_clips_to_requested_window() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(-0.1, 0.0, 0.1, 0.2, 0.3, 1.1),
        gtis=(TimeInterval(-0.2, 1.2),),
    )
    config = TargetedZ2SearchConfig(
        frequency_grid=TargetedFrequencyGrid(
            center_hz=10.0,
            half_width_hz=0.0,
            step_hz=1.0,
        ),
        min_photons=4,
    )

    result = search_event_product_targeted_z2(
        product,
        window=TimeInterval(0.0, 0.4),
        config=config,
    )

    assert result.photon_count == 4
    assert result.effective_exposure_s == pytest.approx(0.4)
    assert result.best_z2_power == pytest.approx(8.0)


def test_search_event_product_targeted_z2_rejects_low_photon_windows() -> None:
    product = _phase_aligned_product()
    config = TargetedZ2SearchConfig(
        frequency_grid=TargetedFrequencyGrid(
            center_hz=10.0,
            half_width_hz=1.0,
            step_hz=1.0,
        ),
        min_photons=11,
    )

    with pytest.raises(OscillationSearchError, match="minimum"):
        search_event_product_targeted_z2(
            product,
            window=TimeInterval(0.0, 1.0),
            config=config,
        )


def test_targeted_z2_search_config_validates_inputs() -> None:
    grid = TargetedFrequencyGrid(center_hz=10.0, half_width_hz=1.0, step_hz=1.0)

    with pytest.raises(OscillationSearchError, match="n_harmonics"):
        TargetedZ2SearchConfig(frequency_grid=grid, n_harmonics=0)

    with pytest.raises(OscillationSearchError, match="min_photons"):
        TargetedZ2SearchConfig(frequency_grid=grid, min_photons=0)


def test_make_sliding_windows_returns_full_windows_inside_interval() -> None:
    windows = make_sliding_windows(
        TimeInterval(0.0, 2.0),
        config=SlidingWindowConfig(window_size_s=1.0, step_s=0.5),
    )

    assert windows == (
        TimeInterval(0.0, 1.0),
        TimeInterval(0.5, 1.5),
        TimeInterval(1.0, 2.0),
    )


def test_make_sliding_windows_returns_empty_when_interval_is_too_short() -> None:
    windows = make_sliding_windows(
        TimeInterval(0.0, 0.5),
        config=SlidingWindowConfig(window_size_s=1.0, step_s=0.5),
    )

    assert windows == ()


def test_sliding_window_config_validates_inputs() -> None:
    with pytest.raises(OscillationSearchError, match="window_size_s"):
        SlidingWindowConfig(window_size_s=0.0, step_s=0.5)

    with pytest.raises(OscillationSearchError, match="step_s"):
        SlidingWindowConfig(window_size_s=1.0, step_s=0.0)


def test_search_event_product_sliding_targeted_z2_reports_best_window() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(
            0.0,
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.2,
            1.4,
            1.6,
            1.8,
        ),
        gtis=(TimeInterval(0.0, 2.0),),
    )
    search_config = TargetedZ2SearchConfig(
        frequency_grid=TargetedFrequencyGrid(
            center_hz=10.0,
            half_width_hz=1.0,
            step_hz=1.0,
        ),
        min_photons=3,
    )

    result = search_event_product_sliding_targeted_z2(
        product,
        interval=TimeInterval(0.0, 2.0),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=search_config,
    )

    assert result.source_id == "source"
    assert result.obs_id == "obs"
    assert result.instrument == "RXTE/PCA"
    assert result.search_mode == TARGETED_SEARCH_MODE
    assert result.searched_window_count == 2
    assert result.skipped_window_count == 0
    assert result.trial_count == 6
    assert result.best_result.window == TimeInterval(0.0, 1.0)
    assert result.best_frequency_hz == 10.0
    assert result.best_z2_power == pytest.approx(20.0)


def test_search_event_product_sliding_targeted_z2_skips_low_photon_windows() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.0, 0.1, 0.2),
        gtis=(TimeInterval(0.0, 3.0),),
    )
    search_config = TargetedZ2SearchConfig(
        frequency_grid=TargetedFrequencyGrid(
            center_hz=10.0,
            half_width_hz=0.0,
            step_hz=1.0,
        ),
        min_photons=2,
    )

    result = search_event_product_sliding_targeted_z2(
        product,
        interval=TimeInterval(0.0, 3.0),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=search_config,
    )

    assert result.searched_window_count == 1
    assert result.skipped_windows == (
        TimeInterval(1.0, 2.0),
        TimeInterval(2.0, 3.0),
    )


def test_sliding_targeted_z2_result_rejects_best_result_without_windows() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(),
        gtis=(TimeInterval(0.0, 1.0),),
    )
    result = search_event_product_sliding_targeted_z2(
        product,
        interval=TimeInterval(0.0, 1.0),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=TargetedZ2SearchConfig(
            frequency_grid=TargetedFrequencyGrid(
                center_hz=10.0,
                half_width_hz=0.0,
                step_hz=1.0,
            ),
            min_photons=1,
        ),
    )

    with pytest.raises(OscillationSearchError, match="no windows"):
        _ = result.best_result


def _phase_aligned_product() -> EventProduct:
    return EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=tuple(index * 0.1 for index in range(10)),
        gtis=(TimeInterval(0.0, 1.0),),
    )
