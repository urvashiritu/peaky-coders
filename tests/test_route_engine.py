
import pytest

from nammakannu.route_engine import RouteEngine


@pytest.fixture
def engine():
    return RouteEngine()


def test_dataset_loads(engine):
    assert len(engine.routes) == 5
    assert len(engine.stops) == 252
    assert len(engine.trips) == 1123
    assert len(engine.shapes) == 10


def test_search_stops(engine):
    results = engine.search_stops("Mathikere")

    assert results
    assert any("Mathikere" in stop["name"] for stop in results)


def test_search_empty_query_returns_no_results(engine):
    assert engine.search_stops("") == []
    assert engine.search_stops("   ") == []


def test_direct_route_in_forward_direction(engine):
    trip = next(
        trip for trip in engine.trips
        if len(trip["stops"]) >= 2
    )

    stops = trip["stops"]
    boarding_id = str(stops[0]["stop_id"])
    destination_id = str(stops[1]["stop_id"])

    results = engine.find_direct_routes(
        boarding_id, destination_id
    )

    assert any(
        result["trip_id"] == trip["trip_id"]
        for result in results
    )


def test_reverse_direction_excludes_original_trip(engine):
    trip = next(
        trip for trip in engine.trips
        if len(trip["stops"]) >= 2
    )

    stops = trip["stops"]
    first_id = str(stops[0]["stop_id"])
    second_id = str(stops[1]["stop_id"])

    results = engine.find_direct_routes(second_id, first_id)

    assert all(
        result["trip_id"] != trip["trip_id"]
        for result in results
    )


def test_unknown_boarding_stop_raises_error(engine):
    known_stop_id = next(iter(engine.stops))

    with pytest.raises(ValueError, match="Unknown boarding stop"):
        engine.find_direct_routes("INVALID_STOP", known_stop_id)


def test_unknown_destination_stop_raises_error(engine):
    known_stop_id = next(iter(engine.stops))

    with pytest.raises(ValueError, match="Unknown destination stop"):
        engine.find_direct_routes(known_stop_id, "INVALID_STOP")


def test_same_boarding_and_destination_returns_empty(engine):
    stop_id = next(iter(engine.stops))

    assert engine.find_direct_routes(stop_id, stop_id) == []


def test_route_details_returns_ordered_stops(engine):
    trip = next(
        trip for trip in engine.trips
        if len(trip["stops"]) >= 2
    )

    details = engine.get_route_details(trip["trip_id"])

    assert details["trip_id"] == trip["trip_id"]
    assert len(details["stops"]) == len(trip["stops"])

    sequences = [
        stop["sequence"] for stop in details["stops"]
    ]

    assert sequences == sorted(sequences)


def test_unknown_trip_raises_error(engine):
    with pytest.raises(ValueError, match="Unknown trip"):
        engine.get_route_details("INVALID_TRIP")
