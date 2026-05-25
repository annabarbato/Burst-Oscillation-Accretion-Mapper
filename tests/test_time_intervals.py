import pytest

from burst_oscillation_accretion_mapper.time_intervals import (
    IntervalError,
    TimeInterval,
    clip_to_gti,
    intersect_intervals,
    merge_intervals,
    select_times_in_intervals,
    total_duration,
)


def test_interval_rejects_non_positive_duration() -> None:
    with pytest.raises(IntervalError, match="greater than start"):
        TimeInterval(10.0, 10.0)


def test_interval_uses_half_open_boundaries() -> None:
    interval = TimeInterval(1.0, 3.0)

    assert interval.contains(1.0)
    assert interval.contains(2.999)
    assert not interval.contains(3.0)


def test_merge_intervals_sorts_and_merges_touching_spans() -> None:
    merged = merge_intervals(
        (
            TimeInterval(5.0, 6.0),
            TimeInterval(1.5, 2.0),
            TimeInterval(0.0, 1.5),
        )
    )

    assert merged == (TimeInterval(0.0, 2.0), TimeInterval(5.0, 6.0))


def test_intersect_intervals_handles_unsorted_gti_like_inputs() -> None:
    intersections = intersect_intervals(
        (TimeInterval(30.0, 40.0), TimeInterval(10.0, 20.0)),
        (TimeInterval(18.0, 35.0),),
    )

    assert intersections == (TimeInterval(18.0, 20.0), TimeInterval(30.0, 35.0))


def test_clip_to_gti_returns_event_windows_inside_good_time() -> None:
    requested = TimeInterval(10.0, 40.0)
    gtis = (
        TimeInterval(0.0, 12.0),
        TimeInterval(15.0, 20.0),
        TimeInterval(35.0, 50.0),
    )

    clipped = clip_to_gti(requested, gtis)

    assert clipped == (
        TimeInterval(10.0, 12.0),
        TimeInterval(15.0, 20.0),
        TimeInterval(35.0, 40.0),
    )
    assert total_duration(clipped) == 12.0


def test_select_times_in_intervals_respects_clipped_half_open_windows() -> None:
    intervals = (TimeInterval(10.0, 12.0), TimeInterval(15.0, 20.0))
    times = (9.999, 10.0, 11.5, 12.0, 15.0, 19.999, 20.0)

    selected = select_times_in_intervals(times, intervals)

    assert selected == (10.0, 11.5, 15.0, 19.999)
