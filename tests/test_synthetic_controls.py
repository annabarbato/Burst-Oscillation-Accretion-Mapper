import pytest

from burst_oscillation_accretion_mapper.event_products import (
    EventProduct,
    EventProductProvenance,
)
from burst_oscillation_accretion_mapper.synthetic_controls import (
    PoissonEnvelopeBin,
    PoissonEnvelopeConfig,
    SyntheticControlError,
    SyntheticPoissonControlConfig,
    estimate_poisson_count_rate_envelope,
    generate_synthetic_poisson_event_product,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_estimate_poisson_count_rate_envelope_uses_gti_clipped_bins() -> None:
    envelope = estimate_poisson_count_rate_envelope(
        _envelope_product(),
        interval=TimeInterval(0.0, 3.0),
        config=PoissonEnvelopeConfig(bin_size_s=1.0),
    )

    assert envelope == (
        PoissonEnvelopeBin(TimeInterval(0.0, 1.0), 3.0),
        PoissonEnvelopeBin(TimeInterval(1.0, 2.0), 1.0),
        PoissonEnvelopeBin(TimeInterval(2.5, 3.0), 2.0),
    )


def test_generate_synthetic_poisson_event_product_is_deterministic() -> None:
    envelope = (
        PoissonEnvelopeBin(TimeInterval(0.0, 1.0), 8.0),
        PoissonEnvelopeBin(TimeInterval(1.0, 2.0), 4.0),
    )

    first = generate_synthetic_poisson_event_product(
        _envelope_product(),
        envelope=envelope,
        seed=42,
        realization_number=2,
    )
    second = generate_synthetic_poisson_event_product(
        _envelope_product(),
        envelope=envelope,
        seed=42,
        realization_number=2,
    )

    assert first.times == second.times
    assert first.gtis == (TimeInterval(0.0, 2.0),)
    assert first.source_id == "source"
    assert first.obs_id == "obs-synthetic-poisson-002"
    assert first.instrument == "RXTE/PCA"
    assert first.provenance.raw_uri == "synthetic-poisson:raw/obs"
    assert "synthetic_poisson_null" in first.provenance.notes
    assert "seed=42" in first.provenance.notes
    assert all(0.0 <= event_time < 2.0 for event_time in first.times)


def test_generate_synthetic_poisson_event_product_preserves_zero_rate_gtis() -> None:
    product = generate_synthetic_poisson_event_product(
        _envelope_product(),
        envelope=(PoissonEnvelopeBin(TimeInterval(0.0, 1.0), 0.0),),
        seed=1,
    )

    assert product.times == ()
    assert product.gtis == (TimeInterval(0.0, 1.0),)


def test_synthetic_poisson_control_config_returns_repeatable_realization_seeds() -> None:
    config = SyntheticPoissonControlConfig(
        envelope_bin_size_s=0.5,
        realization_count=3,
        base_seed=10,
    )

    assert [config.seed_for_realization(index) for index in (1, 2, 3)] == [
        10,
        11,
        12,
    ]


def test_synthetic_control_configs_validate_inputs() -> None:
    with pytest.raises(SyntheticControlError, match="bin_size_s"):
        PoissonEnvelopeConfig(bin_size_s=0.0)

    with pytest.raises(SyntheticControlError, match="rate_per_s"):
        PoissonEnvelopeBin(TimeInterval(0.0, 1.0), -1.0)

    with pytest.raises(SyntheticControlError, match="realization_count"):
        SyntheticPoissonControlConfig(
            envelope_bin_size_s=1.0,
            realization_count=0,
        )

    with pytest.raises(SyntheticControlError, match="base_seed"):
        SyntheticPoissonControlConfig(
            envelope_bin_size_s=1.0,
            base_seed=-1,
        )


def _envelope_product() -> EventProduct:
    return EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.1, 0.2, 0.7, 1.4, 2.6),
        gtis=(TimeInterval(0.0, 2.0), TimeInterval(2.5, 3.0)),
        provenance=EventProductProvenance(
            raw_uri="raw/obs",
            software_version="test",
            screening_hash="screened",
            barycorr_applied=True,
            notes="template",
        ),
    )
