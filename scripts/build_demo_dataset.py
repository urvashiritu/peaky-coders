import csv
import json
import math
from collections import defaultdict
from pathlib import Path

DATA = Path("data/source/gtfs")
OUTPUT = Path("data/processed/nammakannu_demo.json")

CENTER_LAT, CENTER_LON = 13.0318, 77.5649
RADIUS_KM = 2.0
TARGET_ROUTES = {"276", "401-K", "90-E", "K-2", "401"}


def read_rows(filename):
    with (DATA / filename).open(
        encoding="utf-8-sig", newline=""
    ) as f:
        yield from csv.DictReader(f)


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(min(1, a)))


# 1. Select exact route names from the dataset.
routes = {
    r["route_id"]: r
    for r in read_rows("routes.txt")
    if r["route_short_name"].strip() in TARGET_ROUTES
}

print("Selected routes:")
for route in routes.values():
    print(
        route["route_short_name"],
        "|",
        route["route_id"],
        "|",
        route["route_long_name"],
    )

missing = TARGET_ROUTES - {
    r["route_short_name"].strip() for r in routes.values()
}
if missing:
    print("Route names not found:", sorted(missing))

if not routes:
    raise SystemExit("No target routes found. Check route names.")

# 2. Find stops within the demo area.
stops = {}
nearby_ids = set()

for s in read_rows("stops.txt"):
    try:
        lat, lon = float(s["stop_lat"]), float(s["stop_lon"])
    except (ValueError, TypeError):
        continue

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        continue

    s["stop_lat"] = lat
    s["stop_lon"] = lon
    stops[s["stop_id"]] = s

    if distance_km(CENTER_LAT, CENTER_LON, lat, lon) <= RADIUS_KM:
        nearby_ids.add(s["stop_id"])

print(f"\nNearby stops: {len(nearby_ids)}")

# 3. Map trips to their routes and retain relevant trip metadata.
trips = {
    t["trip_id"]: t
    for t in read_rows("trips.txt")
    if t["route_id"] in routes
}

# 4. Identify selected-route trips serving nearby stops.
candidate_trip_ids = set()

for st in read_rows("stop_times.txt"):
    if st["stop_id"] in nearby_ids and st["trip_id"] in trips:
        candidate_trip_ids.add(st["trip_id"])

print(f"Trips serving nearby stops: {len(candidate_trip_ids)}")

if not candidate_trip_ids:
    raise SystemExit("No candidate trips found. Check the GTFS relationships.")

# 5. Collect every stop time for those trips.
trip_stops = defaultdict(list)
used_stop_ids = set()
used_shape_ids = set()

for st in read_rows("stop_times.txt"):
    trip_id = st["trip_id"]

    if trip_id not in candidate_trip_ids:
        continue

    trip_stops[trip_id].append({
        "stop_id": st["stop_id"],
        "sequence": int(st["stop_sequence"]),
        "arrival_time": st["arrival_time"],
        "departure_time": st["departure_time"],
        "stop_headsign": st["stop_headsign"],
    })
    used_stop_ids.add(st["stop_id"])

for trip_id in candidate_trip_ids:
    shape_id = trips[trip_id].get("shape_id", "")
    if shape_id:
        used_shape_ids.add(shape_id)

for trip_id in trip_stops:
    trip_stops[trip_id].sort(key=lambda x: x["sequence"])

# 6. Read shapes used by the selected trips only.
shape_points = defaultdict(list)

for point in read_rows("shapes.txt"):
    shape_id = point["shape_id"]
    if shape_id not in used_shape_ids:
        continue

    try:
        lat = float(point["shape_pt_lat"])
        lon = float(point["shape_pt_lon"])
        sequence = int(point["shape_pt_sequence"])
    except (ValueError, TypeError):
        continue

    shape_points[shape_id].append({
        "sequence": sequence,
        "lat": lat,
        "lon": lon,
    })

# Sort and downsample very long paths for a lighter web map.
shapes = {}

for shape_id, points in shape_points.items():
    points.sort(key=lambda p: p["sequence"])

    if len(points) > 250:
        step = math.ceil((len(points) - 1) / 249)
        sampled = points[::step]
        if sampled[-1] != points[-1]:
            sampled.append(points[-1])
        points = sampled

    shapes[shape_id] = [
        [p["lat"], p["lon"]] for p in points
    ]

# 7. Build a compact, serializable dataset.
output_stops = {
    stop_id: {
        "stop_id": stops[stop_id]["stop_id"],
        "name": stops[stop_id]["stop_name"],
        "description": stops[stop_id]["stop_desc"],
        "lat": stops[stop_id]["stop_lat"],
        "lon": stops[stop_id]["stop_lon"],
    }
    for stop_id in used_stop_ids
    if stop_id in stops
}

output_trips = []

for trip_id, sequence in trip_stops.items():
    trip = trips[trip_id]
    output_trips.append({
        "trip_id": trip_id,
        "route_id": trip["route_id"],
        "direction_id": trip.get("direction_id", ""),
        "headsign": trip.get("trip_headsign", ""),
        "shape_id": trip.get("shape_id", ""),
        "stops": sequence,
    })

result = {
    "metadata": {
        "source": "Vonter/bmtc-gtfs",
        "center": [CENTER_LAT, CENTER_LON],
        "radius_km": RADIUS_KM,
        "route_names_requested": sorted(TARGET_ROUTES),
        "note": (
            "Unofficial dataset. Validate route information "
            "before relying on it for real journeys."
        ),
    },
    "routes": list(routes.values()),
    "stops": output_stops,
    "trips": output_trips,
    "shapes": shapes,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(result, ensure_ascii=False),
    encoding="utf-8",
)

print("\n=== DATASET BUILT ===")
print("Output:", OUTPUT)
print("Routes:", len(result["routes"]))
print("Stops:", len(output_stops))
print("Trips:", len(output_trips))
print("Shapes:", len(shapes))
print("File size: {:.2f} MB".format(OUTPUT.stat().st_size / 1e6))
