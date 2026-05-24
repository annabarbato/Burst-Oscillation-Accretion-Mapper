import pytest

from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.oscillation_search import (
    TARGETED_SEARCH_MODE,
    OscillationSearchError,
    TargetedFrequencyGrid,
    TargetedZ2SearchConfig,
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


def _phase_aligned_product() -> EventProduct:
    return EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=tuple(index * 0.1 for index in range(10)),
        gtis=(TimeInterval(0.0, 1.0),),
    )
