from datetime import UTC, datetime, timedelta

import pytest

from planner.logic.checkpoints import build_checkpoints
from planner.logic.geo import LatLon, haversine_miles

DEPARTURE = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
MILES_PER_DEGREE = haversine_miles(LatLon(0, 0), LatLon(0, 1))


class TestBuildCheckpoints:
    def test_eta_grows_with_driving_time(self) -> None:
        # Two 1-degree segments: the first takes 1 hour, the second 2 hours.
        points = [LatLon(0, 0), LatLon(0, 1), LatLon(0, 2)]

        checkpoints = build_checkpoints(points, [3600, 7200], interval_miles=50, departure=DEPARTURE)

        assert checkpoints[0].eta == DEPARTURE
        assert checkpoints[-1].eta == DEPARTURE + timedelta(hours=3)
        etas = [checkpoint.eta for checkpoint in checkpoints]
        assert etas == sorted(etas)

    def test_eta_inside_a_segment_is_proportional(self) -> None:
        # 50 miles into a ~69-mile segment that takes 1 hour.
        points = [LatLon(0, 0), LatLon(0, 1)]

        checkpoints = build_checkpoints(points, [3600], interval_miles=50, departure=DEPARTURE)

        expected_seconds = 3600 * 50 / MILES_PER_DEGREE
        assert (checkpoints[1].eta - DEPARTURE).total_seconds() == pytest.approx(expected_seconds)

    def test_eta_in_a_later_segment_includes_earlier_segments(self) -> None:
        # Segment 1: 1 h. Segment 2: 2 h. The 100-mile point is in segment 2.
        points = [LatLon(0, 0), LatLon(0, 1), LatLon(0, 2)]

        checkpoints = build_checkpoints(points, [3600, 7200], interval_miles=100, departure=DEPARTURE)

        fraction_into_second = (100 - MILES_PER_DEGREE) / MILES_PER_DEGREE
        expected_seconds = 3600 + fraction_into_second * 7200
        assert (checkpoints[1].eta - DEPARTURE).total_seconds() == pytest.approx(expected_seconds)

    def test_checkpoints_are_numbered_in_order(self) -> None:
        points = [LatLon(0, 0), LatLon(0, 3)]

        checkpoints = build_checkpoints(points, [10_000], interval_miles=50, departure=DEPARTURE)

        assert [checkpoint.index for checkpoint in checkpoints] == list(range(len(checkpoints)))

    def test_rejects_mismatched_durations(self) -> None:
        with pytest.raises(ValueError):
            build_checkpoints([LatLon(0, 0), LatLon(0, 1)], [1, 2], 10, DEPARTURE)

    def test_rejects_naive_departure(self) -> None:
        with pytest.raises(ValueError):
            build_checkpoints([LatLon(0, 0), LatLon(0, 1)], [60], 10, datetime(2026, 10, 20, 8))
