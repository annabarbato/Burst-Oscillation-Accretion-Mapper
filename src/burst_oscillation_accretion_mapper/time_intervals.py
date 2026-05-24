"""Time-window and GTI helpers for Phase 1 event slicing.

Intervals are half-open: ``start <= t < stop``. That convention avoids double
counting events that land exactly on a shared boundary between adjacent windows.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite


class IntervalError(ValueError):
    """Raised when a time interval is invalid."""


@dataclass(frozen=True, order=True)
class TimeInterval:
    """A half-open time interval in seconds or mission-time units."""

    start: float
    stop: float

    def __post_init__(self) -> None:
        if not isfinite(self.start) or not isfinite(self.stop):
            raise IntervalError("Interval bounds must be finite")
        if self.stop <= self.start:
            raise IntervalError(
                f"Interval stop must be greater than start: {self.start}, {self.stop}"
            )

    @property
    def duration(self) -> float:
        return self.stop - self.start

    def contains(self, time: float) -> bool:
        return self.start <= time < self.stop

    def overlaps(self, other: "TimeInterval") -> bool:
        return self.start < other.stop and other.start < self.stop

    def touches_or_overlaps(self, other: "TimeInterval") -> bool:
        return self.start <= other.stop and other.start <= self.stop

    def intersection(self, other: "TimeInterval") -> "TimeInterval | None":
        start = max(self.start, other.start)
        stop = min(self.stop, other.stop)
        if stop <= start:
            return None
        return TimeInterval(start, stop)


def merge_intervals(intervals: Iterable[TimeInterval]) -> tuple[TimeInterval, ...]:
    """Return sorted intervals with overlapping or touching spans merged."""

    sorted_intervals = sorted(intervals)
    if not sorted_intervals:
        return ()

    merged = [sorted_intervals[0]]
    for interval in sorted_intervals[1:]:
        current = merged[-1]
        if current.touches_or_overlaps(interval):
            merged[-1] = TimeInterval(current.start, max(current.stop, interval.stop))
        else:
            merged.append(interval)
    return tuple(merged)


def intersect_intervals(
    left: Iterable[TimeInterval], right: Iterable[TimeInterval]
) -> tuple[TimeInterval, ...]:
    """Return the intersections between two interval collections."""

    left_merged = merge_intervals(left)
    right_merged = merge_intervals(right)
    intersections: list[TimeInterval] = []

    left_index = 0
    right_index = 0
    while left_index < len(left_merged) and right_index < len(right_merged):
        left_interval = left_merged[left_index]
        right_interval = right_merged[right_index]

        intersection = left_interval.intersection(right_interval)
        if intersection is not None:
            intersections.append(intersection)

        if left_interval.stop <= right_interval.stop:
            left_index += 1
        else:
            right_index += 1

    return tuple(intersections)


def clip_to_gti(
    requested: TimeInterval, good_time_intervals: Iterable[TimeInterval]
) -> tuple[TimeInterval, ...]:
    """Clip one requested event window to available good-time intervals."""

    return intersect_intervals((requested,), good_time_intervals)


def total_duration(intervals: Iterable[TimeInterval]) -> float:
    """Return total duration after merging overlapping intervals."""

    return sum(interval.duration for interval in merge_intervals(intervals))


def select_times_in_intervals(
    times: Iterable[float], intervals: Iterable[TimeInterval]
) -> tuple[float, ...]:
    """Select event times that fall within any merged half-open interval."""

    merged = merge_intervals(intervals)
    return tuple(time for time in times if any(interval.contains(time) for interval in merged))
