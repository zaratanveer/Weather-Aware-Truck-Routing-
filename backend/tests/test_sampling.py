import pytest

from planner.logic.geo import LatLon, haversine_miles
from planner.logic.sampling import sample_along_route

# Points along the equator: one degree of longitude is ~69.09 miles there.
MILES_PER_DEGREE = haversine_miles(LatLon(0, 0), LatLon(0, 1))


def equator_route(*longitudes: float) -> list[LatLon]:
    return [LatLon(0, lon) for lon in longitudes]


class TestSampleAlongRoute:
    def test_includes_start_every_interval_and_end(self) -> None:
        # One straight 10-degree segment (~690.9 miles), samples every 100 miles.
        samples = sample_along_route(equator_route(0, 10), interval_miles=100)

        miles = [round(sample.mile, 1) for sample in samples]
        assert miles == [0, 100, 200, 300, 400, 500, 600, round(10 * MILES_PER_DEGREE, 1)]

    def test_sample_locations_are_at_the_right_distance(self) -> None:
        samples = sample_along_route(equator_route(0, 10), interval_miles=100)

        for sample in samples:
            assert haversine_miles(LatLon(0, 0), sample.location) == pytest.approx(sample.mile)

    def test_samples_cross_segment_boundaries(self) -> None:
        # Three 1-degree segments; a 100-mile sample falls in the second segment.
        samples = sample_along_route(equator_route(0, 1, 2, 3), interval_miles=100)

        hundred_mile = samples[1]
        assert hundred_mile.segment_index == 1
        assert hundred_mile.segment_fraction == pytest.approx(100 / MILES_PER_DEGREE - 1)

    def test_route_shorter_than_interval_has_only_start_and_end(self) -> None:
        samples = sample_along_route(equator_route(0, 0.1), interval_miles=50)

        assert [sample.mile for sample in samples] == [0, pytest.approx(0.1 * MILES_PER_DEGREE)]
        assert samples[-1].location == LatLon(0, 0.1)
        assert samples[-1].segment_fraction == 1.0

    def test_end_is_not_duplicated_when_route_length_is_an_exact_multiple(self) -> None:
        route = equator_route(0, 2)
        length = 2 * MILES_PER_DEGREE

        samples = sample_along_route(route, interval_miles=length / 2)

        assert len(samples) == 3
        assert samples[-1].mile == pytest.approx(length)

    def test_zero_length_segments_are_ignored(self) -> None:
        samples = sample_along_route(equator_route(0, 0, 1, 1), interval_miles=25)

        assert [round(sample.mile) for sample in samples] == [0, 25, 50, 69]

    @pytest.mark.parametrize("interval", [10, 25, 50])
    def test_supported_intervals(self, interval: int) -> None:
        samples = sample_along_route(equator_route(0, 5), interval_miles=interval)
        gaps = [b.mile - a.mile for a, b in zip(samples, samples[1:])]

        assert all(gap == pytest.approx(interval) for gap in gaps[:-1])
        assert 0 < gaps[-1] <= interval

    def test_rejects_a_single_point(self) -> None:
        with pytest.raises(ValueError):
            sample_along_route([LatLon(0, 0)], interval_miles=10)

    def test_rejects_non_positive_interval(self) -> None:
        with pytest.raises(ValueError):
            sample_along_route(equator_route(0, 1), interval_miles=0)
