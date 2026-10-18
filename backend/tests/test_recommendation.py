import pytest

from planner.logic.recommendation import format_duration, recommend_route
from planner.logic.risk import RiskLevel
from planner.logic.summary import RouteSummary

HOUR = 3600


def summary(
    severe: float = 0,
    high: float = 0,
    no_travel: float = 0,
    average: float = 0,
    hours: float = 5,
    has_no_travel: bool | None = None,
) -> RouteSummary:
    miles = {level: 0.0 for level in RiskLevel}
    miles[RiskLevel.SEVERE] = severe
    miles[RiskLevel.HIGH] = high
    miles[RiskLevel.NO_TRAVEL] = no_travel
    return RouteSummary(
        distance_miles=300,
        duration_seconds=hours * HOUR,
        miles_by_level=miles,
        average_risk=average,
        worst_level=RiskLevel.LOW,
        has_no_travel=no_travel > 0 if has_no_travel is None else has_no_travel,
    )


class TestPreferenceOrder:
    def test_1_fewest_severe_miles_wins_even_if_slower_and_more_high(self) -> None:
        routes = [summary(severe=20, hours=4), summary(severe=5, high=80, average=1.5, hours=7)]

        result = recommend_route(routes)

        assert result.route_index == 1
        assert result.reason == "Fewest Severe-risk miles (5 vs Route 1: 20)."

    def test_2_then_fewest_high_miles(self) -> None:
        routes = [summary(severe=5, high=30), summary(severe=5, high=10, hours=6)]

        result = recommend_route(routes)

        assert result.route_index == 1
        assert "fewest High-risk miles (10 vs Route 1: 30)" in result.reason

    def test_3_then_lowest_average_risk(self) -> None:
        routes = [summary(average=0.8, hours=4), summary(average=0.3, hours=6)]

        result = recommend_route(routes)

        assert result.route_index == 1
        assert "lowest average risk (0.30 vs Route 1: 0.80)" in result.reason

    def test_4_then_shortest_travel_time(self) -> None:
        routes = [summary(hours=6), summary(hours=5.5), summary(hours=7)]

        result = recommend_route(routes)

        assert result.route_index == 1
        assert result.reason == (
            "Weather risk is the same, and it is the fastest (5 h 30 min vs Route 1: 6 h 0 min)."
        )


class TestNoTravel:
    def test_route_without_no_travel_beats_one_with_it(self) -> None:
        routes = [summary(no_travel=1, hours=3), summary(severe=50, hours=9)]

        result = recommend_route(routes)

        assert result.route_index == 1
        assert result.reason == "It avoids the No Travel conditions found on Route 1."

    def test_when_every_route_has_no_travel_pick_fewest_and_warn(self) -> None:
        routes = [summary(no_travel=30), summary(no_travel=10)]

        result = recommend_route(routes)

        assert result.route_index == 1
        assert result.reason.startswith("Fewest No Travel miles (10 vs Route 1: 30).")
        assert "consider delaying departure" in result.reason

    def test_no_travel_only_at_destination_still_counts(self) -> None:
        routes = [summary(has_no_travel=True, hours=3), summary(hours=4)]

        assert recommend_route(routes).route_index == 1


class TestEdgeCases:
    def test_single_route(self) -> None:
        result = recommend_route([summary()])

        assert result.route_index == 0
        assert result.reason == "Only one route was found, so it is the recommendation."

    def test_floating_point_noise_does_not_decide(self) -> None:
        # 12.00001 vs 12.0 severe miles count as equal, so the faster route wins.
        routes = [summary(severe=12.00001, hours=4), summary(severe=12.0, hours=5)]

        assert recommend_route(routes).route_index == 0

    def test_identical_routes_pick_the_first(self) -> None:
        result = recommend_route([summary(), summary()])

        assert result.route_index == 0
        assert result.reason == "All routes are rated the same; this is the first option."

    def test_empty_list_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            recommend_route([])


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(0, "0 min"), (59 * 60, "59 min"), (3725, "1 h 2 min"), (10 * HOUR, "10 h 0 min")],
)
def test_format_duration(seconds: float, text: str) -> None:
    assert format_duration(seconds) == text
