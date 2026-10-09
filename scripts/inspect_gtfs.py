import csv
import math
from pathlib import Path
from collections import Counter, defaultdict

DATA = Path("data/source/gtfs")

# Approximate MSRIT location, Bengaluru.
CENTER_LAT = 13.0318
CENTER_LON = 77.5649
RADIUS_KM = 2.0


def rows(filename):
    path = DATA / filename
    with path.open(encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def distance_km(lat1, lon1, lat2, lon2):
    radius = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(min(1, a)))


def inspect_ids(filename, key):
    seen = set()
    duplicates = 0
    count = 0

    for row in rows(filename):
        count += 1
        value = row.get(key, "")
        if value in seen:
            duplicates += 1
        seen.add(value)

    print(
        f"{filename}: rows={count:,}, "
        f"unique_{key}={len(seen):,}, duplicates={duplicates:,}"
    )


print("\n=== ID VALIDATION ===")
inspect_ids("routes.txt", "route_id")
inspect_ids("stops.txt", "stop_id")
inspect_ids("trips.txt", "trip_id")

print("\n=== ROUTE TYPES ===")
print(Counter(row["route_type"] for row in rows("routes.txt")))

print("\n=== NEARBY STOPS ===")
nearby = {}

for stop in rows("stops.txt"):
    try:
        lat = float(stop["stop_lat"])
        lon = float(stop["stop_lon"])
    except (ValueError, TypeError):
        continue

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        continue

    dist = distance_km(CENTER_LAT, CENTER_LON, lat, lon)

    if dist <= RADIUS_KM:
        nearby[stop["stop_id"]] = stop
        stop["_distance"] = dist

if not nearby:
    print("No stops found within the selected radius.")
else:
    ordered = sorted(
        nearby.values(),
        key=lambda s: s["_distance"],
    )

    for stop in ordered[:30]:
        print(
            f'{stop["_distance"]:.2f} km | '
            f'{stop["stop_id"]} | '
            f'{stop["stop_name"]} | '
            f'{stop["stop_desc"]}'
        )

print(f"\nStops within {RADIUS_KM} km: {len(nearby)}")

print("\n=== ROUTES SERVING NEARBY STOPS ===")

trip_to_route = {
    trip["trip_id"]: trip["route_id"]
    for trip in rows("trips.txt")
}

route_info = {
    route["route_id"]: route
    for route in rows("routes.txt")
}

route_stop_counts = Counter()
route_stops = defaultdict(set)

for stop_time in rows("stop_times.txt"):
    stop_id = stop_time["stop_id"]

    if stop_id not in nearby:
        continue

    route_id = trip_to_route.get(stop_time["trip_id"])
    if route_id is None:
        continue

    route_stop_counts[route_id] += 1
    route_stops[route_id].add(stop_id)

for route_id, _ in route_stop_counts.most_common(30):
    route = route_info.get(route_id, {})
    names = [
        nearby[s]["stop_name"]
        for s in sorted(route_stops[route_id])
    ]

    print(
        f'{route.get("route_short_name", "?")} | '
        f'{route.get("route_long_name", "?")} | '
        f'nearby stops: {", ".join(names[:5])}'
    )

print("\nInspection complete.")
