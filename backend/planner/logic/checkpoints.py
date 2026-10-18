"""
Turns route samples into checkpoints with an estimated time of arrival (ETA).

The routing API gives the driving time of every polyline segment. The ETA of
a checkpoint is the departure time plus the time of all segments before it,
plus the matching share of the segment it sits on.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import accumulate

from .geo import LatLon
from .sampling import sample_along_route


@dataclass(frozen=True)
class Checkpoint:
    index: int
    location: LatLon
    mile: float  # distance from the origin along the route
    eta: datetime


def build_checkpoints(
    points: Sequence[LatLon],
    segment_durations_s: Sequence[float],
    interval_miles: float,
    departure: datetime,
) -> list[Checkpoint]:
    """Checkpoints every `interval_miles` (plus start and end), each with its ETA.

    `segment_durations_s[i]` is the driving time from points[i] to points[i + 1].
    """
    if len(segment_durations_s) != len(points) - 1:
        raise ValueError("Need exactly one duration per segment (len(points) - 1).")
    if departure.tzinfo is None:
        raise ValueError("Departure time must be timezone-aware.")

    # seconds_before[i] = driving time from the start to points[i].
    seconds_before = [0.0, *accumulate(segment_durations_s)]

    checkpoints = []
    for index, sample in enumerate(sample_along_route(points, interval_miles)):
        segment = sample.segment_index
        elapsed = seconds_before[segment] + sample.segment_fraction * segment_durations_s[segment]
        checkpoints.append(
            Checkpoint(
                index=index,
                location=sample.location,
                mile=sample.mile,
                eta=departure + timedelta(seconds=elapsed),
            )
        )
    return checkpoints
