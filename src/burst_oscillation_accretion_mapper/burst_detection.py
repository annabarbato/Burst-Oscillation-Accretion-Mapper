"""Early burst-detection primitives for Phase 1.

This module scores excess counts relative to a supplied baseline and groups
adjacent excess bins into interval candidates. It does not claim candidates are
thermonuclear bursts; later morphology filters and MINBAR validation must do
that work.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log, sqrt

from .lightcurves import (
    BaselineEstimate,
    LightCurve,
    LightCurveError,
    MultiCadenceLightCurves,
    estimate_rolling_baseline,
)


class BurstDetectionError(ValueError):
    """Raised when burst-detection scoring inputs are invalid."""


@dataclass(frozen=True)
class BurstDetectionConfig:
    """Configuration for one light-curve candidate-finding pass."""

    baseline_window_bins: int
    excess_threshold: float
    min_consecutive_bins: int = 1
    excluded_bins: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        if self.baseline_window_bins < 1:
            raise BurstDetectionError("baseline_window_bins must be at least 1")
        if not isfinite(self.excess_threshold) or self.excess_threshold <= 0:
            raise BurstDetectionError("excess_threshold must be positive")
        if self.min_consecutive_bins < 1:
            raise BurstDetectionError("min_consecutive_bins must be at least 1")


@dataclass(frozen=True)
class MorphologyReviewConfig:
    """Conservative binned-shape checks for interval candidates."""

    min_excess_counts: float = 0.0
    min_peak_score: float = 0.0
    require_fast_rise_slow_decay: bool = False
    max_rise_fraction: float | None = None

    def __post_init__(self) -> None:
        if self.min_excess_counts < 0:
            raise BurstDetectionError("min_excess_counts cannot be negative")
        if self.min_peak_score < 0:
            raise BurstDetectionError("min_peak_score cannot be negative")
        if self.max_rise_fraction is not None and not (
            0.0 < self.max_rise_fraction <= 1.0
        ):
            raise BurstDetectionError("max_rise_fraction must be in (0, 1]")


@dataclass(frozen=True)
class BinExcessScore:
    """Poisson excess score for one light-curve bin."""

    bin_index: int
    start: float
    stop: float
    observed_counts: int
    expected_counts: float | None
    exposure: float
    baseline_rate: float | None
    signed_sqrt_deviance: float | None

    def is_excess(self, threshold: float) -> bool:
        return (
            self.signed_sqrt_deviance is not None
            and self.signed_sqrt_deviance >= threshold
        )


@dataclass(frozen=True)
class BurstIntervalCandidate:
    """A contiguous interval of excess bins needing later morphology review."""

    start: float
    stop: float
    first_bin_index: int
    last_bin_index: int
    peak_bin_index: int
    peak_score: float
    total_counts: int
    total_expected_counts: float
    n_bins: int

    @property
    def duration(self) -> float:
        return self.stop - self.start

    @property
    def excess_counts(self) -> float:
        return self.total_counts - self.total_expected_counts


@dataclass(frozen=True)
class BurstMorphologySummary:
    """Binned morphology features for an interval candidate under review."""

    start: float
    peak_time: float
    stop: float
    duration: float
    approximate_rise_time: float
    approximate_decay_time: float
    peak_rate: float | None
    total_counts: int
    total_expected_counts: float
    excess_counts: float
    n_bins: int

    @property
    def rise_fraction(self) -> float:
        return self.approximate_rise_time / self.duration if self.duration > 0 else 0.0

    @property
    def has_fast_rise_slow_decay_shape(self) -> bool:
        return (
            self.approximate_rise_time > 0
            and self.approximate_decay_time >= self.approximate_rise_time
        )


@dataclass(frozen=True)
class BurstCandidateReview:
    """Candidate plus binned morphology review outcome."""

    candidate: BurstIntervalCandidate
    morphology: BurstMorphologySummary
    rejection_reasons: tuple[str, ...]

    @property
    def passes_review(self) -> bool:
        return not self.rejection_reasons


@dataclass(frozen=True)
class BurstCandidateSearchResult:
    """Intermediate products from one light-curve candidate-finding pass."""

    baseline: BaselineEstimate
    scores: tuple[BinExcessScore, ...]
    reviews: tuple[BurstCandidateReview, ...]

    @property
    def candidates(self) -> tuple[BurstIntervalCandidate, ...]:
        return tuple(review.candidate for review in self.reviews)

    @property
    def passed_reviews(self) -> tuple[BurstCandidateReview, ...]:
        return tuple(review for review in self.reviews if review.passes_review)


@dataclass(frozen=True)
class MultiCadenceBurstCandidateReview:
    """A reviewed interval candidate from one light-curve cadence."""

    bin_size: float
    review: BurstCandidateReview

    def __post_init__(self) -> None:
        if not isfinite(self.bin_size) or self.bin_size <= 0:
            raise BurstDetectionError(f"Invalid bin_size: {self.bin_size}")


@dataclass(frozen=True)
class MultiCadenceBurstCandidateCluster:
    """Conservative overlap cluster of reviewed candidates across cadences."""

    start: float
    stop: float
    reviews: tuple[MultiCadenceBurstCandidateReview, ...]

    def __post_init__(self) -> None:
        if not self.reviews:
            raise BurstDetectionError("At least one review is required")
        if (
            not isfinite(self.start)
            or not isfinite(self.stop)
            or self.stop <= self.start
        ):
            raise BurstDetectionError("Invalid cluster interval")

    @property
    def duration(self) -> float:
        return self.stop - self.start

    @property
    def bin_sizes(self) -> tuple[float, ...]:
        return tuple(sorted({review.bin_size for review in self.reviews}))

    @property
    def review_count(self) -> int:
        return len(self.reviews)

    @property
    def passed_review_count(self) -> int:
        return sum(review.review.passes_review for review in self.reviews)

    @property
    def best_cadence_review(self) -> MultiCadenceBurstCandidateReview:
        return max(
            self.reviews,
            key=lambda cadence_review: (
                cadence_review.review.candidate.peak_score,
                cadence_review.review.morphology.excess_counts,
                cadence_review.review.candidate.duration,
            ),
        )

    @property
    def best_review(self) -> BurstCandidateReview:
        return self.best_cadence_review.review

    @property
    def best_peak_score(self) -> float:
        return self.best_review.candidate.peak_score

    @property
    def passes_any_review(self) -> bool:
        return any(review.review.passes_review for review in self.reviews)

    @property
    def rejection_reasons(self) -> tuple[str, ...]:
        reasons = {
            reason
            for review in self.reviews
            for reason in review.review.rejection_reasons
        }
        return tuple(sorted(reasons))


@dataclass(frozen=True)
class MultiCadenceBurstCandidateSummary:
    """Stable review product for one multi-cadence candidate cluster."""

    start: float
    peak_time: float
    stop: float
    duration: float
    bin_sizes: tuple[float, ...]
    best_bin_size: float
    review_count: int
    passed_review_count: int
    best_peak_score: float
    best_excess_counts: float
    total_counts: int
    total_expected_counts: float
    rejection_reasons: tuple[str, ...]

    @property
    def passes_any_review(self) -> bool:
        return self.passed_review_count > 0


def signed_poisson_sqrt_deviance(observed_counts: int, expected_counts: float) -> float:
    """Return signed square root of the Poisson likelihood-ratio deviance.

    Positive values indicate excess counts, negative values indicate deficits.
    The statistic is useful for ranking bins, not as a final trials-corrected
    burst significance.
    """

    if observed_counts < 0:
        raise BurstDetectionError("observed_counts cannot be negative")
    if not isfinite(expected_counts) or expected_counts <= 0:
        raise BurstDetectionError(f"expected_counts must be positive: {expected_counts}")

    if observed_counts == expected_counts:
        return 0.0

    if observed_counts == 0:
        deviance = 2.0 * expected_counts
    else:
        deviance = 2.0 * (
            observed_counts * log(observed_counts / expected_counts)
            - (observed_counts - expected_counts)
        )

    sign = 1.0 if observed_counts > expected_counts else -1.0
    return sign * sqrt(max(deviance, 0.0))


def score_light_curve_excess(
    light_curve: LightCurve, baseline: BaselineEstimate
) -> tuple[BinExcessScore, ...]:
    """Score each light-curve bin against a baseline rate estimate."""

    if light_curve.n_bins != len(baseline.rates):
        raise LightCurveError("Light curve and baseline lengths must match")

    scores: list[BinExcessScore] = []
    for index, (count, exposure, baseline_rate) in enumerate(
        zip(light_curve.counts, light_curve.exposures, baseline.rates)
    ):
        expected_counts: float | None = None
        signed_score: float | None = None
        if exposure > 0 and baseline_rate is not None:
            if baseline_rate < 0 or not isfinite(baseline_rate):
                raise BurstDetectionError(f"Invalid baseline rate: {baseline_rate}")
            expected_counts = baseline_rate * exposure
            if expected_counts > 0:
                signed_score = signed_poisson_sqrt_deviance(count, expected_counts)

        scores.append(
            BinExcessScore(
                bin_index=index,
                start=light_curve.bin_starts[index],
                stop=light_curve.bin_stops[index],
                observed_counts=count,
                expected_counts=expected_counts,
                exposure=exposure,
                baseline_rate=baseline_rate,
                signed_sqrt_deviance=signed_score,
            )
        )

    return tuple(scores)


def group_excess_bins(
    scores: tuple[BinExcessScore, ...],
    *,
    threshold: float,
    min_consecutive_bins: int = 1,
) -> tuple[BurstIntervalCandidate, ...]:
    """Group adjacent scored bins above threshold into interval candidates."""

    if not isfinite(threshold) or threshold <= 0:
        raise BurstDetectionError(f"threshold must be positive: {threshold}")
    if min_consecutive_bins < 1:
        raise BurstDetectionError("min_consecutive_bins must be at least 1")

    candidates: list[BurstIntervalCandidate] = []
    current: list[BinExcessScore] = []
    for score in scores:
        if score.is_excess(threshold):
            current.append(score)
        else:
            _append_candidate_if_valid(candidates, current, min_consecutive_bins)
            current = []
    _append_candidate_if_valid(candidates, current, min_consecutive_bins)
    return tuple(candidates)


def summarize_candidate_morphology(
    light_curve: LightCurve, candidate: BurstIntervalCandidate
) -> BurstMorphologySummary:
    """Summarize binned morphology for a candidate interval.

    These binned features are inputs to later morphology review. They are not
    sufficient to classify an interval as a thermonuclear burst.
    """

    if candidate.first_bin_index < 0 or candidate.last_bin_index >= light_curve.n_bins:
        raise BurstDetectionError("Candidate bin range is outside the light curve")
    if not candidate.first_bin_index <= candidate.peak_bin_index <= candidate.last_bin_index:
        raise BurstDetectionError("Candidate peak bin is outside the candidate range")

    peak_start = light_curve.bin_starts[candidate.peak_bin_index]
    peak_stop = light_curve.bin_stops[candidate.peak_bin_index]
    peak_time = 0.5 * (peak_start + peak_stop)
    peak_rate = light_curve.rates[candidate.peak_bin_index]
    approximate_rise_time = peak_stop - candidate.start
    approximate_decay_time = candidate.stop - peak_start

    return BurstMorphologySummary(
        start=candidate.start,
        peak_time=peak_time,
        stop=candidate.stop,
        duration=candidate.duration,
        approximate_rise_time=approximate_rise_time,
        approximate_decay_time=approximate_decay_time,
        peak_rate=peak_rate,
        total_counts=candidate.total_counts,
        total_expected_counts=candidate.total_expected_counts,
        excess_counts=candidate.excess_counts,
        n_bins=candidate.n_bins,
    )


def review_candidate_morphology(
    candidate: BurstIntervalCandidate,
    morphology: BurstMorphologySummary,
    *,
    config: MorphologyReviewConfig,
) -> BurstCandidateReview:
    """Apply binned morphology checks without declaring a validated burst."""

    reasons: list[str] = []
    if morphology.excess_counts < config.min_excess_counts:
        reasons.append("excess_counts_below_threshold")
    if candidate.peak_score < config.min_peak_score:
        reasons.append("peak_score_below_threshold")
    if (
        config.require_fast_rise_slow_decay
        and not morphology.has_fast_rise_slow_decay_shape
    ):
        reasons.append("not_fast_rise_slow_decay")
    if (
        config.max_rise_fraction is not None
        and morphology.rise_fraction > config.max_rise_fraction
    ):
        reasons.append("rise_fraction_above_threshold")

    return BurstCandidateReview(
        candidate=candidate,
        morphology=morphology,
        rejection_reasons=tuple(reasons),
    )


def find_burst_interval_reviews(
    light_curve: LightCurve,
    *,
    detection_config: BurstDetectionConfig,
    morphology_config: MorphologyReviewConfig = MorphologyReviewConfig(),
) -> BurstCandidateSearchResult:
    """Find and review interval candidates in one binned light curve.

    This is still an intermediate detector primitive. Later code must add
    multi-cadence reconciliation, morphology filters beyond these binned checks,
    and MINBAR validation before accepting burst detections.
    """

    baseline = estimate_rolling_baseline(
        light_curve,
        window_bins=detection_config.baseline_window_bins,
        excluded_bins=detection_config.excluded_bins,
    )
    scores = score_light_curve_excess(light_curve, baseline)
    candidates = group_excess_bins(
        scores,
        threshold=detection_config.excess_threshold,
        min_consecutive_bins=detection_config.min_consecutive_bins,
    )
    reviews = tuple(
        review_candidate_morphology(
            candidate,
            summarize_candidate_morphology(light_curve, candidate),
            config=morphology_config,
        )
        for candidate in candidates
    )
    return BurstCandidateSearchResult(baseline=baseline, scores=scores, reviews=reviews)


def find_multi_cadence_burst_reviews(
    light_curves: MultiCadenceLightCurves,
    *,
    detection_configs: dict[float, BurstDetectionConfig],
    morphology_config: MorphologyReviewConfig = MorphologyReviewConfig(),
    passed_only: bool = False,
) -> tuple[MultiCadenceBurstCandidateReview, ...]:
    """Run interval review for each cadence with explicit per-cadence config."""

    missing_bin_sizes = tuple(
        bin_size
        for bin_size in light_curves.bin_sizes
        if bin_size not in detection_configs
    )
    if missing_bin_sizes:
        raise BurstDetectionError(
            "Missing detection config for bin sizes: "
            + ", ".join(str(bin_size) for bin_size in missing_bin_sizes)
        )

    reviews: list[MultiCadenceBurstCandidateReview] = []
    for bin_size in light_curves.bin_sizes:
        result = find_burst_interval_reviews(
            light_curves.get(bin_size),
            detection_config=detection_configs[bin_size],
            morphology_config=morphology_config,
        )
        cadence_reviews = result.passed_reviews if passed_only else result.reviews
        reviews.extend(
            MultiCadenceBurstCandidateReview(bin_size=bin_size, review=review)
            for review in cadence_reviews
        )
    return tuple(reviews)


def find_multi_cadence_burst_clusters(
    light_curves: MultiCadenceLightCurves,
    *,
    detection_configs: dict[float, BurstDetectionConfig],
    morphology_config: MorphologyReviewConfig = MorphologyReviewConfig(),
    passed_only: bool = False,
) -> tuple[MultiCadenceBurstCandidateCluster, ...]:
    """Run multi-cadence review and cluster overlapping interval candidates."""

    reviews = find_multi_cadence_burst_reviews(
        light_curves,
        detection_configs=detection_configs,
        morphology_config=morphology_config,
        passed_only=passed_only,
    )
    return cluster_overlapping_candidate_reviews(reviews)


def cluster_overlapping_candidate_reviews(
    reviews: tuple[MultiCadenceBurstCandidateReview, ...],
) -> tuple[MultiCadenceBurstCandidateCluster, ...]:
    """Cluster reviewed candidates whose intervals overlap or touch."""

    if not reviews:
        return ()

    sorted_reviews = sorted(
        reviews,
        key=lambda review: (
            review.review.candidate.start,
            review.review.candidate.stop,
            review.bin_size,
        ),
    )
    current_reviews: list[MultiCadenceBurstCandidateReview] = [sorted_reviews[0]]
    current_start = sorted_reviews[0].review.candidate.start
    current_stop = sorted_reviews[0].review.candidate.stop
    clusters: list[MultiCadenceBurstCandidateCluster] = []

    for review in sorted_reviews[1:]:
        candidate = review.review.candidate
        if candidate.start <= current_stop:
            current_reviews.append(review)
            current_start = min(current_start, candidate.start)
            current_stop = max(current_stop, candidate.stop)
            continue

        clusters.append(
            MultiCadenceBurstCandidateCluster(
                start=current_start,
                stop=current_stop,
                reviews=tuple(current_reviews),
            )
        )
        current_reviews = [review]
        current_start = candidate.start
        current_stop = candidate.stop

    clusters.append(
        MultiCadenceBurstCandidateCluster(
            start=current_start,
            stop=current_stop,
            reviews=tuple(current_reviews),
        )
    )
    return tuple(clusters)


def summarize_multi_cadence_candidate_cluster(
    cluster: MultiCadenceBurstCandidateCluster,
) -> MultiCadenceBurstCandidateSummary:
    """Summarize a cluster without promoting it to a validated burst."""

    best_cadence_review = cluster.best_cadence_review
    best_review = best_cadence_review.review
    return MultiCadenceBurstCandidateSummary(
        start=cluster.start,
        peak_time=best_review.morphology.peak_time,
        stop=cluster.stop,
        duration=cluster.duration,
        bin_sizes=cluster.bin_sizes,
        best_bin_size=best_cadence_review.bin_size,
        review_count=cluster.review_count,
        passed_review_count=cluster.passed_review_count,
        best_peak_score=best_review.candidate.peak_score,
        best_excess_counts=best_review.morphology.excess_counts,
        total_counts=best_review.candidate.total_counts,
        total_expected_counts=best_review.candidate.total_expected_counts,
        rejection_reasons=cluster.rejection_reasons,
    )


def summarize_multi_cadence_candidate_clusters(
    clusters: tuple[MultiCadenceBurstCandidateCluster, ...],
) -> tuple[MultiCadenceBurstCandidateSummary, ...]:
    """Summarize candidate clusters for later MINBAR/catalog comparison."""

    return tuple(
        summarize_multi_cadence_candidate_cluster(cluster) for cluster in clusters
    )


def _append_candidate_if_valid(
    candidates: list[BurstIntervalCandidate],
    scores: list[BinExcessScore],
    min_consecutive_bins: int,
) -> None:
    if len(scores) < min_consecutive_bins:
        return

    peak = max(scores, key=lambda score: score.signed_sqrt_deviance or float("-inf"))
    total_expected = sum(score.expected_counts or 0.0 for score in scores)
    candidates.append(
        BurstIntervalCandidate(
            start=scores[0].start,
            stop=scores[-1].stop,
            first_bin_index=scores[0].bin_index,
            last_bin_index=scores[-1].bin_index,
            peak_bin_index=peak.bin_index,
            peak_score=peak.signed_sqrt_deviance or 0.0,
            total_counts=sum(score.observed_counts for score in scores),
            total_expected_counts=total_expected,
            n_bins=len(scores),
        )
    )
