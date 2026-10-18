import pytest

from planner.logic.risk import RiskLevel, classify_rain, classify_snow, classify_wind


class TestRiskLevel:
    def test_levels_are_ordered_from_safest_to_most_dangerous(self) -> None:
        assert (
            RiskLevel.LOW
            < RiskLevel.MODERATE
            < RiskLevel.HIGH
            < RiskLevel.SEVERE
            < RiskLevel.NO_TRAVEL
        )

    def test_max_picks_the_worst_level(self) -> None:
        assert max(RiskLevel.MODERATE, RiskLevel.SEVERE, RiskLevel.LOW) is RiskLevel.SEVERE

    @pytest.mark.parametrize(
        ("level", "label"),
        [
            (RiskLevel.LOW, "Low"),
            (RiskLevel.MODERATE, "Moderate"),
            (RiskLevel.HIGH, "High"),
            (RiskLevel.SEVERE, "Severe"),
            (RiskLevel.NO_TRAVEL, "No Travel"),
        ],
    )
    def test_label_is_human_readable(self, level: RiskLevel, label: str) -> None:
        assert level.label == label


class TestClassifyWind:
    @pytest.mark.parametrize(
        ("speed_mph", "expected"),
        [
            # Low: < 25
            (0, RiskLevel.LOW),
            (24.9, RiskLevel.LOW),
            # Moderate: 25â€“34
            (25, RiskLevel.MODERATE),
            (34, RiskLevel.MODERATE),
            (34.9, RiskLevel.MODERATE),
            # High: 35â€“44
            (35, RiskLevel.HIGH),
            (44.9, RiskLevel.HIGH),
            # Severe: 45â€“54
            (45, RiskLevel.SEVERE),
            (54.9, RiskLevel.SEVERE),
            # No Travel: >= 55
            (55, RiskLevel.NO_TRAVEL),
            (90, RiskLevel.NO_TRAVEL),
        ],
    )
    def test_spec_boundaries(self, speed_mph: float, expected: RiskLevel) -> None:
        assert classify_wind(speed_mph) is expected

    def test_negative_speed_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            classify_wind(-1)


class TestClassifyRain:
    @pytest.mark.parametrize(
        ("rate_in_per_hr", "expected"),
        [
            # Low: < 0.10
            (0, RiskLevel.LOW),
            (0.09, RiskLevel.LOW),
            # Moderate: 0.10–0.25
            (0.10, RiskLevel.MODERATE),
            (0.24, RiskLevel.MODERATE),
            # High: 0.25–0.50
            (0.25, RiskLevel.HIGH),
            (0.49, RiskLevel.HIGH),
            # Severe: 0.50–1.00 (1.00 itself is still Severe)
            (0.50, RiskLevel.SEVERE),
            (1.00, RiskLevel.SEVERE),
            # No Travel: > 1.00
            (1.01, RiskLevel.NO_TRAVEL),
            (3.0, RiskLevel.NO_TRAVEL),
        ],
    )
    def test_spec_boundaries(self, rate_in_per_hr: float, expected: RiskLevel) -> None:
        assert classify_rain(rate_in_per_hr) is expected

    def test_negative_rate_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            classify_rain(-0.01)


class TestClassifySnow:
    @pytest.mark.parametrize(
        ("rate_in_per_hr", "expected"),
        [
            # Low: < 0.5
            (0, RiskLevel.LOW),
            (0.49, RiskLevel.LOW),
            # Moderate: 0.5–1.0
            (0.5, RiskLevel.MODERATE),
            (0.99, RiskLevel.MODERATE),
            # High: 1.0–2.0
            (1.0, RiskLevel.HIGH),
            (1.99, RiskLevel.HIGH),
            # Severe: 2.0–3.0 (3.0 itself is still Severe)
            (2.0, RiskLevel.SEVERE),
            (3.0, RiskLevel.SEVERE),
            # No Travel: > 3.0
            (3.01, RiskLevel.NO_TRAVEL),
            (6.0, RiskLevel.NO_TRAVEL),
        ],
    )
    def test_spec_boundaries(self, rate_in_per_hr: float, expected: RiskLevel) -> None:
        assert classify_snow(rate_in_per_hr) is expected

    def test_negative_rate_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            classify_snow(-0.01)
