import pytest

from planner.logic.risk import RiskLevel
from planner.logic.summary import summarize_route

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL = RiskLevel


class TestSummarizeRoute:
    def test_each_checkpoint_owns_the_miles_to_the_next(self) -> None:
        # 0-10 Low, 10-20 High, 20-25 Severe; the end checkpoint owns nothing.
        summary = summarize_route([0, 10, 20, 25], [LOW, HIGH, SEVERE, LOW], 1800)

        assert summary.miles_at(LOW) == 10
        assert summary.miles_at(HIGH) == 10
        assert summary.miles_at(SEVERE) == 5
        assert summary.miles_at(MODERATE) == 0
        assert summary.miles_at(NO_TRAVEL) == 0
        assert summary.distance_miles == 25
        assert summary.duration_seconds == 1800

    def test_miles_by_level_add_up_to_the_route_distance(self) -> None:
        summary = summarize_route([0, 25, 50, 61.3], [MODERATE, LOW, HIGH, LOW], 3600)

        assert sum(summary.miles_by_level.values()) == pytest.approx(summary.distance_miles)

    def test_average_risk_is_weighted_by_miles(self) -> None:
        # 30 miles at Low (0) and 10 miles at Severe (3): (0*30 + 3*10) / 40 = 0.75.
        summary = summarize_route([0, 10, 20, 30, 40], [LOW, LOW, LOW, SEVERE, LOW], 3600)

        assert summary.average_risk == pytest.approx(0.75)

    def test_worst_level_and_no_travel_flag(self) -> None:
        summary = summarize_route([0, 10, 20], [MODERATE, NO_TRAVEL, LOW], 900)

        assert summary.worst_level is NO_TRAVEL
        assert summary.has_no_travel is True
        assert summary.miles_at(NO_TRAVEL) == 10

    def test_no_travel_at_the_destination_is_still_flagged(self) -> None:
        summary = summarize_route([0, 10], [LOW, NO_TRAVEL], 900)

        assert summary.miles_at(NO_TRAVEL) == 0
        assert summary.has_no_travel is True

    def test_safe_route_has_no_flag(self) -> None:
        summary = summarize_route([0, 10], [LOW, MODERATE], 900)

        assert summary.has_no_travel is False
        assert summary.worst_level is MODERATE

    def test_rejects_mismatched_lengths(self) -> None:
        with pytest.raises(ValueError):
            summarize_route([0, 10], [LOW], 900)
