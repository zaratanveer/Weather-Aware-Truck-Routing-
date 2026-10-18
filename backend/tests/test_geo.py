import pytest

from planner.logic.geo import LatLon, haversine_miles, interpolate

NEW_YORK = LatLon(40.7128, -74.0060)
LOS_ANGELES = LatLon(34.0522, -118.2437)


class TestHaversineMiles:
    def test_same_point_is_zero(self) -> None:
        assert haversine_miles(NEW_YORK, NEW_YORK) == 0

    def test_new_york_to_los_angeles(self) -> None:
        # Published great-circle distance is about 2,445 miles.
        assert haversine_miles(NEW_YORK, LOS_ANGELES) == pytest.approx(2445, abs=5)

    def test_one_degree_of_latitude_is_about_69_miles(self) -> None:
        assert haversine_miles(LatLon(0, 0), LatLon(1, 0)) == pytest.approx(69.09, abs=0.01)

    def test_distance_is_symmetric(self) -> None:
        assert haversine_miles(NEW_YORK, LOS_ANGELES) == haversine_miles(LOS_ANGELES, NEW_YORK)


class TestInterpolate:
    def test_endpoints(self) -> None:
        assert interpolate(NEW_YORK, LOS_ANGELES, 0) == NEW_YORK
        assert interpolate(NEW_YORK, LOS_ANGELES, 1) == LOS_ANGELES

    def test_midpoint(self) -> None:
        assert interpolate(LatLon(0, 0), LatLon(2, 4), 0.5) == LatLon(1, 2)
