import math

import pytest

from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.oscillation_search import (
    SlidingWindowConfig,
    TargetedFrequencyGrid,
    TargetedZ2SearchConfig,
    search_event_product_sliding_targeted_z2,
    search_event_product_targeted_z2,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval
from burst_oscillation_accretion_mapper.timing_significance import (
    TimingSignificanceError,
    independent_trials_p_value,
    sliding_result_significance,
    targeted_result_significance,
    z2_single_trial_p_value,
    z2_trial_significance,
)


def test_z2_single_trial_p_value_matches_chi_square_survival_for_one_harmonic() -> None:
    p_value = z2_single_trial_p_value(20.0, n_harmonics=1)

    assert p_value == pytest.approx(math.exp(-10.0))


def test_z2_single_trial_p_value_supports_multiple_harmonics() -> None:
    p_value = z2_single_trial_p_value(20.0, n_harmonics=2)

    assert p_value == pytest.approx(math.exp(-10.0) * 11.0)


def test_z2_single_trial_p_value_is_one_for_zero_power() -> None:
    assert z2_single_trial_p_value(0.0, n_harmonics=3) == pytest.approx(1.0)


def test_independent_trials_p_value_uses_exact_attempt_probability() -> None:
    p_value = independent_trials_p_value(0.1, trial_count=3)

    assert p_value == pytest.approx(1.0 - 0.9**3)


def test_independent_trials_p_value_preserves_probability_edges() -> None:
    assert independent_trials_p_value(0.0, trial_count=3) == 0.0
    assert independent_trials_p_value(1.0, trial_count=3) == 1.0


def test_z2_trial_significance_summarizes_single_and_corrected_values() -> None:
    summary = z2_trial_significance(20.0, n_harmonics=1, trial_count=5)

    assert summary.z2_power == 20.0
    assert summary.n_harmonics == 1
    assert summary.trial_count == 5
    assert summary.p_single == pytest.approx(math.exp(-10.0))
    assert summary.p_trials == pytest.approx(1.0 - (1.0 - math.exp(-10.0)) ** 5)


def test_targeted_result_significance_uses_best_power_and_frequency_trials() -> None:
    result = search_event_product_targeted_z2(
        _phase_aligned_product(),
        window=TimeInterval(0.0, 1.0),
        config=TargetedZ2SearchConfig(
            frequency_grid=TargetedFrequencyGrid(
                center_hz=10.0,
                half_width_hz=1.0,
                step_hz=1.0,
            ),
            min_photons=5,
        ),
    )

    summary = targeted_result_significance(result)

    assert summary.z2_power == pytest.approx(20.0)
    assert summary.n_harmonics == 1
    assert summary.trial_count == 3
    assert summary.p_single == pytest.approx(math.exp(-10.0))
    assert summary.p_trials == pytest.approx(1.0 - (1.0 - math.exp(-10.0)) ** 3)


def test_sliding_result_significance_uses_total_window_frequency_trials() -> None:
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

    summary = sliding_result_significance(result)

    assert summary.z2_power == pytest.approx(10.0)
    assert summary.trial_count == 6
    assert summary.p_single == pytest.approx(math.exp(-5.0))
    assert summary.p_trials == pytest.approx(1.0 - (1.0 - math.exp(-5.0)) ** 6)


def test_timing_significance_validates_inputs() -> None:
    with pytest.raises(TimingSignificanceError, match="z2_power"):
        z2_single_trial_p_value(-1.0, n_harmonics=1)

    with pytest.raises(TimingSignificanceError, match="n_harmonics"):
        z2_single_trial_p_value(1.0, n_harmonics=0)

    with pytest.raises(TimingSignificanceError, match="p_single"):
        independent_trials_p_value(1.1, trial_count=1)

    with pytest.raises(TimingSignificanceError, match="trial_count"):
        independent_trials_p_value(0.1, trial_count=0)


def _phase_aligned_product() -> EventProduct:
    return EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=tuple(index * 0.1 for index in range(10)),
        gtis=(TimeInterval(0.0, 1.0),),
    )
