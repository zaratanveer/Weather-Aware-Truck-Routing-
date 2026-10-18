"""
Weather risk rules from the assessment spec.

Each table row in the spec is a range such as "25–34 mph". Weather values are
decimals (e.g. 34.6 mph), so every range is read as lower-bound inclusive:
25 <= wind < 35 is Moderate. This leaves no gaps between levels.
"""

from enum import IntEnum


class RiskLevel(IntEnum):
    """Risk levels ordered from safest to most dangerous.

    IntEnum makes levels comparable (HIGH > MODERATE) and lets max() pick the
    worst of several levels.
    """

    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        """Human-readable name, e.g. RiskLevel.NO_TRAVEL.label == "No Travel"."""
        return self.name.replace("_", " ").title()


def classify_wind(speed_mph: float) -> RiskLevel:
    """Spec: <25 Low | 25–34 Moderate | 35–44 High | 45–54 Severe | 55+ No Travel."""
    if speed_mph < 0:
        raise ValueError(f"Wind speed cannot be negative: {speed_mph}")
    if speed_mph >= 55:
        return RiskLevel.NO_TRAVEL
    if speed_mph >= 45:
        return RiskLevel.SEVERE
    if speed_mph >= 35:
        return RiskLevel.HIGH
    if speed_mph >= 25:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_rain(rate_in_per_hr: float) -> RiskLevel:
    """Spec: <0.10 Low | 0.10–0.25 Moderate | 0.25–0.50 High | 0.50–1.00 Severe | >1.00 No Travel.

    No Travel starts *above* 1.00, so exactly 1.00 in/hr is still Severe.
    """
    if rate_in_per_hr < 0:
        raise ValueError(f"Rain rate cannot be negative: {rate_in_per_hr}")
    if rate_in_per_hr > 1.00:
        return RiskLevel.NO_TRAVEL
    if rate_in_per_hr >= 0.50:
        return RiskLevel.SEVERE
    if rate_in_per_hr >= 0.25:
        return RiskLevel.HIGH
    if rate_in_per_hr >= 0.10:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_snow(rate_in_per_hr: float) -> RiskLevel:
    """Spec: <0.5 Low | 0.5–1.0 Moderate | 1.0–2.0 High | 2.0–3.0 Severe | >3.0 No Travel.

    No Travel starts *above* 3.0, so exactly 3.0 in/hr is still Severe.
    """
    if rate_in_per_hr < 0:
        raise ValueError(f"Snow rate cannot be negative: {rate_in_per_hr}")
    if rate_in_per_hr > 3.0:
        return RiskLevel.NO_TRAVEL
    if rate_in_per_hr >= 2.0:
        return RiskLevel.SEVERE
    if rate_in_per_hr >= 1.0:
        return RiskLevel.HIGH
    if rate_in_per_hr >= 0.5:
        return RiskLevel.MODERATE
    return RiskLevel.LOW
