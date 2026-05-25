import pytest

from burst_oscillation_accretion_mapper.dynamic_power import (
    DynamicPowerError,
    dynamic_power_spectrum_from_sliding_result,
)
from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.oscillation_search import (
    TARGETED_SEARCH_MODE,
    SlidingTargetedZ2SearchResult,
    SlidingWindowConfig,
    TargetedFrequencyGrid,
    TargetedZ2SearchConfig,
    TargetedZ2SearchResult,
    Z2FrequencyPower,
    search_event_product_sliding_targeted_z2,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_dynamic_power_spectrum_formats_sliding_search_grid() -> None:
    result = search_event_product_sliding_targeted_z2(
        _phase_aligned_product(),
        interval=TimeInterval(0.0, 1.0),
        window_config=SlidingWindowConfig(window_size_s=0.5, step_s=0.5),
        search_config=TargetedZ2SearchConfig(
            frequency_grid=TargetedFrequencyGrid(
                center_hz=10.0,
                half_width_hz=1.0,
                step_hz=1.0,
            ),
            min_photons=5,
        ),
    )

    spectrum = dynamic_power_spectrum_from_sliding_result(result)

    assert spectrum.source_id == "source"
    assert spectrum.obs_id == "obs"
    assert spectrum.instrument == "RXTE/PCA"
    assert spectrum.search_mode == TARGETED_SEARCH_MODE
    assert spectrum.windows == (
        TimeInterval(0.0, 0.5),
        TimeInterval(0.5, 1.0),
    )
    assert spectrum.frequencies_hz == (9.0, 10.0, 11.0)
    assert spectrum.window_count == 2
    assert spectrum.frequency_count == 3
    assert spectrum.trial_count == 6
    assert spectrum.photon_counts == (5, 5)
    assert spectrum.z2_power_grid[0][1] == pytest.approx(10.0)
    assert spectrum.leahy_power_grid[0][1] == pytest.approx(10.0)
    assert spectrum.best_peak.window == TimeInterval(0.0, 0.5)
    assert spectrum.best_peak.frequency_hz == 10.0
    assert spectrum.best_peak.z2_power == pytest.approx(10.0)
    assert spectrum.best_peak.leahy_power == pytest.approx(10.0)
    assert spectrum.best_peak.photon_count == 5


def test_dynamic_power_spectrum_preserves_skipped_windows() -> None:
    result = search_event_product_sliding_targeted_z2(
        EventProduct(
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            times=(0.0, 0.1, 0.2),
            gtis=(TimeInterval(0.0, 3.0),),
        ),
        interval=TimeInterval(0.0, 3.0),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=TargetedZ2SearchConfig(
            frequency_grid=TargetedFrequencyGrid(
                center_hz=10.0,
                half_width_hz=0.0,
                step_hz=1.0,
            ),
            min_photons=2,
        ),
    )

    spectrum = dynamic_power_spectrum_from_sliding_result(result)

    assert spectrum.windows == (TimeInterval(0.0, 1.0),)
    assert spectrum.skipped_windows == (
        TimeInterval(1.0, 2.0),
        TimeInterval(2.0, 3.0),
    )


def test_dynamic_power_spectrum_handles_empty_search_results() -> None:
    result = SlidingTargetedZ2SearchResult(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode=TARGETED_SEARCH_MODE,
        window_results=(),
        skipped_windows=(TimeInterval(0.0, 1.0),),
    )

    spectrum = dynamic_power_spectrum_from_sliding_result(result)

    assert spectrum.windows == ()
    assert spectrum.frequencies_hz == ()
    assert spectrum.trial_count == 0
    assert spectrum.skipped_windows == (TimeInterval(0.0, 1.0),)
    with pytest.raises(DynamicPowerError, match="empty spectrum"):
        _ = spectrum.best_peak


def test_dynamic_power_spectrum_rejects_inconsistent_frequency_grids() -> None:
    result = SlidingTargetedZ2SearchResult(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode=TARGETED_SEARCH_MODE,
        window_results=(
            _search_result(TimeInterval(0.0, 1.0), (10.0, 11.0)),
            _search_result(TimeInterval(1.0, 2.0), (10.0, 12.0)),
        ),
        skipped_windows=(),
    )

    with pytest.raises(DynamicPowerError, match="inconsistent grids"):
        dynamic_power_spectrum_from_sliding_result(result)


def _phase_aligned_product() -> EventProduct:
    return EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=tuple(index * 0.1 for index in range(10)),
        gtis=(TimeInterval(0.0, 1.0),),
    )


def _search_result(
    window: TimeInterval,
    frequencies_hz: tuple[float, ...],
) -> TargetedZ2SearchResult:
    return TargetedZ2SearchResult(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        window=window,
        effective_exposure_s=window.duration,
        search_mode=TARGETED_SEARCH_MODE,
        powers=tuple(
            Z2FrequencyPower(
                frequency_hz=frequency_hz,
                z2_power=frequency_hz,
                leahy_power=frequency_hz,
                n_harmonics=1,
                photon_count=10,
                first_harmonic_phase_rad=0.0,
                first_harmonic_fractional_rms=0.1,
            )
            for frequency_hz in frequencies_hz
        ),
    )
