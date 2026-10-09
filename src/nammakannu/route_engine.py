
import json
from pathlib import Path


DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
    / "nammakannu_demo.json"
)


class RouteEngine:
    """Search BMTC GTFS data for stops, trips, and direct routes."""

    def __init__(self, data_path=DEFAULT_DATA_PATH):
        data_path = Path(data_path)

        with data_path.open(encoding="utf-8") as file:
            self.data = json.load(file)

        self.routes = {
            route["route_id"]: route
            for route in self.data["routes"]
        }
        self.stops = self.data["stops"]
        self.trips = self.data["trips"]
        self.shapes = self.data["shapes"]

        # Sort each trip's stops by their GTFS sequence number.
        for trip in self.trips:
            trip["stops"].sort(key=lambda stop: stop["sequence"])

    def search_stops(self, query, limit=10):
        """Search stop names and descriptions, ignoring case."""
        query = query.strip().casefold()

        if not query:
            return []

        matches = []

        for stop in self.stops.values():
            searchable = (
                stop.get("name", "")
                + " "
                + stop.get("description", "")
            ).casefold()

            if query in searchable:
                matches.append(stop)

        matches.sort(
            key=lambda stop: (
                not stop.get("name", "").casefold().startswith(query),
                stop.get("name", "").casefold(),
            )
        )

        return matches[:limit]

    def find_direct_routes(
        self,
        boarding_stop_id,
        destination_stop_id,
        limit=20,
    ):
        """
        Find trips where the boarding stop occurs before
        the destination stop.
        """
        boarding_stop_id = str(boarding_stop_id)
        destination_stop_id = str(destination_stop_id)

        if boarding_stop_id not in self.stops:
            raise ValueError(
                f"Unknown boarding stop: {boarding_stop_id}"
            )

        if destination_stop_id not in self.stops:
            raise ValueError(
                f"Unknown destination stop: {destination_stop_id}"
            )

        if boarding_stop_id == destination_stop_id:
            return []

        matches = []

        for trip in self.trips:
            trip_stops = trip["stops"]

            boarding_positions = [
                index
                for index, stop in enumerate(trip_stops)
                if str(stop["stop_id"]) == boarding_stop_id
            ]

            destination_positions = [
                index
                for index, stop in enumerate(trip_stops)
                if str(stop["stop_id"]) == destination_stop_id
            ]

            # A direct connection requires both stops on
            # the same trip, in the correct order.
            valid_pairs = [
                (start, end)
                for start in boarding_positions
                for end in destination_positions
                if start < end
            ]

            if not valid_pairs:
                continue

            start, end = valid_pairs[0]
            route = self.routes.get(trip["route_id"], {})

            boarding_time = trip_stops[start].get(
                "departure_time"
            ) or trip_stops[start].get("arrival_time")

            destination_time = trip_stops[end].get(
                "arrival_time"
            ) or trip_stops[end].get("departure_time")

            matches.append({
                "trip_id": trip["trip_id"],
                "route_id": trip["route_id"],
                "route_number": route.get(
                    "route_short_name", "Unknown"
                ),
                "route_name": route.get(
                    "route_long_name", ""
                ),
                "headsign": trip.get("headsign", ""),
                "direction_id": trip.get("direction_id"),
                "boarding_stop": self.stops[boarding_stop_id],
                "destination_stop": self.stops[destination_stop_id],
                "departure_time": boarding_time,
                "arrival_time": destination_time,
                "stops_between": end - start - 1,
                "shape_id": trip.get("shape_id"),
            })

        # Put earlier scheduled departures first.
        matches.sort(
            key=lambda match: (
                match["departure_time"] is None,
                match["departure_time"] or "",
                match["route_number"],
            )
        )

        return matches[:limit]

    def get_route_details(self, trip_id):
        """Return an ordered trip with stop names and coordinates."""
        trip = next(
            (
                item for item in self.trips
                if str(item["trip_id"]) == str(trip_id)
            ),
            None,
        )

        if trip is None:
            raise ValueError(f"Unknown trip: {trip_id}")

        route = self.routes.get(trip["route_id"], {})
        ordered_stops = []

        for stop_time in trip["stops"]:
            stop_id = str(stop_time["stop_id"])
            stop = self.stops.get(stop_id, {})

            ordered_stops.append({
                **stop,
                "stop_id": stop_id,
                "sequence": stop_time["sequence"],
                "arrival_time": stop_time.get("arrival_time"),
                "departure_time": stop_time.get("departure_time"),
            })

        return {
            "trip_id": trip["trip_id"],
            "route": route,
            "headsign": trip.get("headsign", ""),
            "direction_id": trip.get("direction_id"),
            "shape_id": trip.get("shape_id"),
            "stops": ordered_stops,
        }
