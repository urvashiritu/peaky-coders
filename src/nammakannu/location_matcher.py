
from math import radians, sin, cos, sqrt, atan2


def distance_meters(lat1, lon1, lat2, lon2):
    """Calculate straight-line distance between two coordinates."""
    earth_radius = 6_371_000

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    return 2 * earth_radius * atan2(
        sqrt(a),
        sqrt(1 - a),
    )


def find_nearby_stops(engine, latitude, longitude, radius_m=1000, limit=10):
    """Return GTFS stops near the user's permitted location."""
    nearby = []

    for stop in engine.stops.values():
        lat = stop.get("lat")
        lon = stop.get("lon")

        if lat is None or lon is None:
            continue

        distance = distance_meters(
            latitude,
            longitude,
            float(lat),
            float(lon),
        )

        if distance <= radius_m:
            nearby.append({
                **stop,
                "distance_m": round(distance),
            })

    return sorted(
        nearby,
        key=lambda stop: stop["distance_m"],
    )[:limit]
