"""
Places sample points every N miles along a route polyline.

A route from the routing API is a list of points joined by straight
segments. We walk those segments, adding up their lengths, and drop a sample
each time the running total passes the next multiple of N. The start and the
end of the route are always included.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from .geo import LatLon, haversine_miles, interpolate

# A final sample closer than this to the previous one would be a duplicate.
_SAME_SPOT_MILES = 0.01


@dataclass(frozen=True)
class RouteSample:
    """A point on the route, plus where it sits on the polyline.

    `segment_index` and `segment_fraction` say which segment it lies on and how
    far along it (0..1); they are used later to work out the arrival time.
    """

    location: LatLon
    mile: float
    segment_index: int
    segment_fraction: float


def sample_along_route(points: Sequence[LatLon], interval_miles: float) -> list[RouteSample]:
    """Samples at mile 0, every `interval_miles` after that, and at the route end."""
    if len(points) < 2:
        raise ValueError("A route needs at least two points.")
    if interval_miles <= 0:
        raise ValueError(f"Interval must be positive: {interval_miles}")

    samples = [RouteSample(points[0], mile=0.0, segment_index=0, segment_fraction=0.0)]
    next_sample_mile = interval_miles
    miles_so_far = 0.0

    for index in range(len(points) - 1):
        start, end = points[index], points[index + 1]
        segment_miles = haversine_miles(start, end)

        # One long segment can contain several sample points.
        while segment_miles > 0 and miles_so_far + segment_miles >= next_sample_mile:
            fraction = (next_sample_mile - miles_so_far) / segment_miles
            samples.append(
                RouteSample(
                    location=interpolate(start, end, fraction),
                    mile=next_sample_mile,
                    segment_index=index,
                    segment_fraction=fraction,
                )
            )
            next_sample_mile += interval_miles

        miles_so_far += segment_miles

    if miles_so_far - samples[-1].mile > _SAME_SPOT_MILES:
        samples.append(
            RouteSample(
                location=points[-1],
                mile=miles_so_far,
                segment_index=len(points) - 2,
                segment_fraction=1.0,
            )
        )
    return samples
