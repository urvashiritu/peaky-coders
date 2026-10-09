import streamlit as st
import folium
from streamlit_folium import st_folium

from nammakannu.route_engine import RouteEngine
from nammakannu.gemma_reader import read_bus_board


st.set_page_config(
    page_title="NammaKannu | BMTC Companion",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Visual system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root { --ink:#eaf2f4; --muted:#9eb1bd; --panel:#111e2a; --panel2:#162635;
        --line:#263b4a; --teal:#43e0c0; --lime:#c7f36b; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background: radial-gradient(ellipse at 10% 0%, #163346 0%, #0a131d 43%, #08111a 100%); color:var(--ink); }
.block-container { max-width: 1320px; padding-top: 1rem; padding-bottom: 2rem; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; color:var(--ink); letter-spacing:-.035em; }
p, label, .stMarkdown { color:var(--ink); }
[data-testid="stMetric"] { background:linear-gradient(145deg,#172a38,#101c27); border:1px solid #29404e; border-radius:16px; padding:15px 18px; }
[data-testid="stMetricLabel"] { color:#9eb1bd !important; }
[data-testid="stMetricValue"] { color:#eaf2f4 !important; }
[data-testid="stFileUploader"] { background:#111e2a; border:1px dashed #3c6974; border-radius:18px; padding:12px; }
.stTextInput input, .stSelectbox div[data-baseweb="select"] > div { background:#101e2a; color:#eaf2f4; border-color:#304756; border-radius:12px; }
.stButton button { border-radius:12px; min-height:44px; font-weight:700; border:1px solid #35515f; background:#172a38; color:#edf7f8; transition:all .15s ease; }
.stButton button:hover { border-color:#43e0c0; color:#43e0c0; }
.stButton button[kind="primary"] { background:linear-gradient(100deg,#43e0c0,#bdf36b); color:#07151a; border:0; }
div[data-testid="stAlert"] { border-radius:14px; }
hr { border-color:#263b4a; }
.nk-hero { padding:20px 24px; border-radius:24px; border:1px solid #294655;
 background:linear-gradient(115deg,rgba(28,67,79,.95),rgba(15,30,43,.96) 65%,rgba(24,43,51,.95));
 margin-bottom:20px; }
.nk-eyebrow { color:#43e0c0; font-size:.75rem; font-weight:700; text-transform:uppercase; letter-spacing:.16em; }
.nk-title { font-family:'Space Grotesk',sans-serif; font-size:clamp(2rem,4vw,3.1rem); line-height:1.05; font-weight:700; margin:.45rem 0 .6rem; color:#f2fbfc; }
.nk-sub { color:#b7c9d0; font-size:1.02rem; max-width:760px; }
.nk-pill { display:inline-block; border:1px solid #355a63; background:#142d37; color:#b5f9e9; border-radius:999px; padding:6px 11px; font-size:.78rem; margin:5px 5px 0 0; }
.nk-card { background:linear-gradient(145deg,rgba(20,36,49,.98),rgba(14,26,37,.98)); border:1px solid #263e4d; border-radius:19px; padding:20px; margin-bottom:14px; }
.nk-section { color:#43e0c0; font-size:.74rem; font-weight:700; text-transform:uppercase; letter-spacing:.13em; margin-bottom:5px; }
.nk-muted { color:#9eb1bd; font-size:.9rem; }
.nk-stop { display:flex; gap:13px; padding:11px 0; border-bottom:1px solid #263b4a; align-items:flex-start; }
.nk-stop:last-child { border-bottom:0; }
.nk-dot { flex:0 0 29px; height:29px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:.78rem; font-weight:700; color:#07151a; background:#43e0c0; }
.nk-dot.mid { background:#203b49; border:1px solid #527180; color:#d8e6ea; }
.nk-stopname { color:#eaf2f4; font-weight:600; }
.nk-stoptime { color:#92a9b4; font-size:.8rem; margin-top:2px; }
.nk-result { border-radius:18px; padding:18px 20px; margin:10px 0 18px; border:1px solid #2d6c61; background:linear-gradient(110deg,#123b36,#142a32); }
.nk-result.warn { border-color:#7c6534; background:linear-gradient(110deg,#3b3019,#242a2b); }
.nk-result.bad { border-color:#79454a; background:linear-gradient(110deg,#3b2027,#24232c); }
.nk-verdict { font-family:'Space Grotesk',sans-serif; font-size:clamp(2.8rem,6vw,4.5rem); font-weight:700; line-height:1; letter-spacing:-.06em; color:#c7f36b; margin:0 0 8px; }
.nk-result.bad .nk-verdict { color:#ff8e98; }
.nk-result.warn .nk-verdict { color:#ffd479; }
.nk-result-title { font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:700; color:#f2fbfc; margin-bottom:4px; }
.nk-small { color:#adc0c8; font-size:.85rem; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


DEMO_BOARDING_STOP_ID = "21042"  # Mysore Road Bus Station for verified K-2 demo


@st.cache_resource
def load_engine():
    return RouteEngine()


try:
    engine = load_engine()
except Exception as exc:
    st.error(f"Could not load route data: {exc}")
    st.stop()


defaults = {
    "route_results": None,
    "search_pair": None,
    "search_error": None,
    "board_result": None,
    "suitability_result": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def search_stops(query, limit=30):
    if not query or not query.strip():
        return []
    return engine.search_stops(query.strip(), limit=limit)


def stop_label(stop):
    label = f'{stop.get("name", "Unknown stop")} · ID {stop.get("stop_id", "")}'
    if stop.get("description"):
        label += f' · {stop["description"]}'
    return label


def save_search(boarding_id, destination_id):
    boarding_id, destination_id = str(boarding_id), str(destination_id)
    st.session_state["route_results"] = None
    st.session_state["search_pair"] = None
    st.session_state["search_error"] = None
    if boarding_id == destination_id:
        st.session_state["search_error"] = "Choose two different stops."
        return
    try:
        results = engine.find_direct_routes(boarding_id, destination_id, limit=20)
        st.session_state["route_results"] = results
        st.session_state["search_pair"] = (boarding_id, destination_id)
    except ValueError as exc:
        st.session_state["search_error"] = str(exc)


def find_route_ids(route_number):
    wanted = str(route_number).strip().casefold()
    return [
        route_id for route_id, route in engine.routes.items()
        if str(route.get("route_short_name", "")).strip().casefold() == wanted
    ]


def check_bus_suitability(route_number, destination_stop_id, boarding_stop_id):
    route_ids = find_route_ids(route_number)
    if not route_ids:
        return {"status": "unknown", "message": f"Route {route_number} was not found in the loaded dataset."}

    boarding_id, destination_id = str(boarding_stop_id), str(destination_stop_id)
    matching_trips = []
    route_has_boarding = False
    route_has_destination = False

    for trip in engine.trips:
        if trip.get("route_id") not in route_ids:
            continue
        stops = sorted(trip.get("stops", []), key=lambda item: item["sequence"])
        boarding_positions = [i for i, s in enumerate(stops) if str(s.get("stop_id")) == boarding_id]
        destination_positions = [i for i, s in enumerate(stops) if str(s.get("stop_id")) == destination_id]
        route_has_boarding |= bool(boarding_positions)
        route_has_destination |= bool(destination_positions)
        if any(b < d for b in boarding_positions for d in destination_positions):
            matching_trips.append(trip)

    if matching_trips:
        return {
            "status": "suitable",
            "message": f"The dataset contains {len(matching_trips)} scheduled trip(s) on route {route_number} from this boarding stop to your destination.",
            "trip_id": str(matching_trips[0].get("trip_id")),
        }
    if not route_has_boarding:
        return {"status": "unknown", "message": f"No scheduled trip for route {route_number} was found serving {engine.stops.get(boarding_id, {}).get('name', 'the selected boarding stop')}."}
    if not route_has_destination:
        return {"status": "not_suitable", "message": f"No trip for route {route_number} in the loaded data serves the selected destination."}
    return {"status": "not_suitable", "message": f"No scheduled trip for route {route_number} was found travelling from the selected boarding stop to this destination in that order."}


def get_stop_coords(stop):
    try:
        lat, lon = stop.get("lat"), stop.get("lon")
        if lat is None or lon is None:
            return None
        return [float(lat), float(lon)]
    except (TypeError, ValueError):
        return None


def render_timeline(stops):
    for i, stop in enumerate(stops):
        name = stop.get("name", "Unknown stop")
        time = stop.get("departure_time") or stop.get("arrival_time") or "Time unavailable"
        is_endpoint = i == 0 or i == len(stops) - 1
        dot_class = "" if is_endpoint else "mid"
        label = "Board here" if i == 0 else ("Destination" if i == len(stops) - 1 else "Stop")
        st.markdown(
            f'<div class="nk-stop"><div class="nk-dot {dot_class}">{i+1}</div>'
            f'<div><div class="nk-stopname">{name}</div>'
            f'<div class="nk-stoptime">{label} · {time}</div></div></div>',
            unsafe_allow_html=True,
        )


# ---------- Hero ----------
st.markdown("""
<div class="nk-hero">
  <div class="nk-eyebrow">Bengaluru · AI transit companion</div>
  <div class="nk-title">Your bus. Your destination.<br>Less guesswork.</div>
  <div class="nk-sub">Scan a BMTC destination board, verify the route against available schedule data, and follow your journey stop by stop.</div>
  <div style="margin-top:12px">
    <span class="nk-pill">✦ Gemma vision</span>
    <span class="nk-pill">↗ Route verification</span>
    <span class="nk-pill">◎ Interactive maps</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="nk-card" style="display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap;padding:12px 16px;margin-top:-5px">
  <span class="nk-pill">1 · Choose stops</span><span style="color:#6f8996">→</span>
  <span class="nk-pill">2 · Scan bus board</span><span style="color:#6f8996">→</span>
  <span class="nk-pill">3 · Read YES / NO</span><span style="color:#6f8996">→</span>
  <span class="nk-pill">4 · Map + stops</span>
</div>
""", unsafe_allow_html=True)

boarding_options = list(engine.stops.values())
default_boarding = engine.stops.get(DEMO_BOARDING_STOP_ID)
if not default_boarding:
    st.error(f"Default boarding stop {DEMO_BOARDING_STOP_ID} was not found in the dataset.")
    st.stop()

with st.container():
    st.markdown('<div class="nk-section">01 / Your journey</div>', unsafe_allow_html=True)
    board_col, dest_col = st.columns([1, 1.25], gap="large")
    with board_col:
        st.markdown("### 📍 Boarding stop")
        st.caption("Demo location, not live device GPS.")
        boarding_search = st.text_input("Find a boarding stop", placeholder="e.g. Mysore Road Bus Station", key="boarding_search")
        boarding_matches = search_stops(boarding_search, limit=20) if boarding_search else [default_boarding]
        if not any(str(s.get("stop_id")) == str(default_boarding["stop_id"]) for s in boarding_matches):
            boarding_matches = [default_boarding] + boarding_matches
        boarding_stop = st.selectbox(
            "Choose where you board",
            boarding_matches,
            index=next((i for i, s in enumerate(boarding_matches) if str(s.get("stop_id")) == str(st.session_state.get("boarding_choice", DEMO_BOARDING_STOP_ID))), 0),
            format_func=stop_label,
            key="boarding_choice",
        )
    with dest_col:
        st.markdown("### 🎯 Where are you going?")
        destination_query = st.text_input("Find your destination", placeholder="Try Hebbala, Tata Institute, Yeshwanthapura…", key="destination_query")
        destination_matches = search_stops(destination_query, limit=30)
        selected_destination = None
        if destination_matches:
            selected_destination = st.selectbox("Choose destination stop", destination_matches, format_func=stop_label, key="destination_choice")
        elif destination_query.strip():
            st.warning("No matching stops found. Try a shorter name or another spelling.")
        else:
            st.caption("Search for a stop to see matching options.")

st.divider()

# ---------- Scan and identify ----------
left, right = st.columns([1.05, .95], gap="large")
with left:
    st.markdown('<div class="nk-section">02 / AI bus scanner</div>', unsafe_allow_html=True)
    st.markdown("## What does the bus board say?")
    st.markdown('<div class="nk-muted">Upload a clear photo. Gemma reads the visible route number and board text. Your destination comes from your selection.</div>', unsafe_allow_html=True)
    uploaded_image = st.file_uploader("Drop a bus-board photo here", type=["jpg", "jpeg", "png", "webp"], key="bus_board_upload")
    if uploaded_image:
        st.image(uploaded_image, caption="Uploaded bus photo", use_container_width=True)
        if st.button("✦ Analyse bus board", type="primary", use_container_width=True):
            try:
                with st.spinner("Reading the board…"):
                    st.session_state["board_result"] = read_bus_board(
                        uploaded_image.getvalue(), uploaded_image.type or "image/jpeg"
                    )
                st.session_state["suitability_result"] = None
            except Exception as exc:
                st.error(f"Could not analyse the image: {exc}")
    elif not st.session_state.get("board_result"):
        st.info("Upload a JPG, PNG, or WebP photo to start scanning.")

with right:
    st.markdown('<div class="nk-section">03 / Recognition</div>', unsafe_allow_html=True)
    st.markdown("## Scan result")
    board_result = st.session_state.get("board_result")
    detected_route = board_result.get("route_number") if board_result else None
    if board_result:
        if not board_result.get("is_bus_board", False):
            st.warning("This image may not contain a bus destination board.")
        m1, m2 = st.columns(2)
        m1.metric("Detected route", detected_route or "Not detected")
        m2.metric("Confidence", str(board_result.get("confidence", "unknown")).title())
        st.markdown('<div class="nk-card">', unsafe_allow_html=True)
        st.markdown("**Text detected on board**")
        st.write(" · ".join(board_result.get("visible_text") or []) or "No text detected")
        st.markdown("**Languages**")
        st.write(", ".join(board_result.get("language") or []) or "Unknown")
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("AI recognition can be wrong. Check the physical display before boarding.")
    else:
        st.markdown('<div class="nk-card"><div class="nk-muted">Your detected route number and board text will appear here after scanning.</div></div>', unsafe_allow_html=True)

# ---------- Check journey ----------
st.divider()
st.markdown('<div class="nk-section">04 / Route verification</div>', unsafe_allow_html=True)
st.markdown("## Can this bus take you there?")
check_col, info_col = st.columns([1, 1.6], gap="large")
with check_col:
    st.markdown('<div class="nk-card">', unsafe_allow_html=True)
    st.markdown(f'**Boarding from**  \n{boarding_stop.get("name", "Unknown stop")}')
    st.markdown(f'**Destination**  \n{selected_destination.get("name", "Choose a destination") if selected_destination else "Choose a destination above"}')
    if st.button("Check this bus →", type="primary", use_container_width=True):
        if not board_result:
            st.warning("Scan a bus-board photo first.")
        elif not board_result.get("is_bus_board", False):
            st.warning("The image was not identified as a bus board.")
        elif not detected_route:
            st.warning("The route number could not be read. Check the sign and try again.")
        elif selected_destination is None:
            st.warning("Search for and select your destination first.")
        else:
            result = check_bus_suitability(detected_route, selected_destination["stop_id"], boarding_stop["stop_id"])
            st.session_state["suitability_result"] = result
            if result["status"] == "suitable":
                save_search(boarding_stop["stop_id"], selected_destination["stop_id"])
            else:
                st.session_state["route_results"] = None
                st.session_state["search_pair"] = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with info_col:
    result = st.session_state.get("suitability_result")
    if result:
        status = result.get("status")
        cls = "" if status == "suitable" else ("bad" if status == "not_suitable" else "warn")
        verdict = "YES" if status == "suitable" else ("NO" if status == "not_suitable" else "NOT SURE")
        title = "You can consider this bus" if status == "suitable" else ("Do NOT board based on this result" if status == "not_suitable" else "We could not verify this bus")
        st.markdown(
            f'<div class="nk-result {cls}">'
            f'<div class="nk-verdict">{verdict}</div>'
            f'<div class="nk-result-title">{title}</div>'
            f'<div class="nk-small">{result.get("message", "")}</div></div>',
            unsafe_allow_html=True,
        )
        if status == "suitable":
            st.caption("This confirms a matching scheduled trip in the loaded dataset only. It does not confirm the identity or live location of the physical bus.")
    else:
        st.markdown('<div class="nk-card"><div class="nk-muted">Your route verdict will appear here. We check the detected route against the selected boarding stop and destination in the schedule data.</div></div>', unsafe_allow_html=True)

# ---------- Journey details and map ----------
results = st.session_state.get("route_results")
search_pair = st.session_state.get("search_pair")
if results is not None and search_pair is not None:
    boarding_id, destination_id = search_pair
    result_boarding = engine.stops.get(str(boarding_id))
    result_destination = engine.stops.get(str(destination_id))
    st.divider()
    st.markdown('<div class="nk-section">05 / Your trip</div>', unsafe_allow_html=True)
    st.markdown("## Journey overview")
    st.markdown(f'<div class="nk-card"><div class="nk-muted">FROM</div><h3>{result_boarding.get("name", boarding_id) if result_boarding else boarding_id}</h3><div style="color:#43e0c0;font-size:1.2rem">↓</div><div class="nk-muted">TO</div><h3>{result_destination.get("name", destination_id) if result_destination else destination_id}</h3></div>', unsafe_allow_html=True)

    if not results:
        st.warning("No direct trip was found in this dataset. That does not prove that BMTC has no suitable service.")
    else:
        st.success(f"Found {len(results)} matching scheduled trip(s).")
        trip_options = {
            str(item["trip_id"]): f'{item["route_number"]} · {item["departure_time"] or "Time unavailable"} · {item["headsign"] or item["route_name"]}'
            for item in results
        }
        selected_trip_id = st.selectbox(
            "Select a scheduled trip",
            options=list(trip_options.keys()),
            format_func=lambda trip_id: trip_options[trip_id],
            key=f'trip_{boarding_id}_{destination_id}',
        )
        selected_trip = next(item for item in results if str(item["trip_id"]) == selected_trip_id)
        m1, m2, m3 = st.columns(3)
        m1.metric("Route", selected_trip["route_number"])
        m2.metric("Departure", selected_trip["departure_time"] or "Unavailable")
        m3.metric("Stops between", selected_trip["stops_between"])
        st.caption(f'Direction: {selected_trip["headsign"] or "Unavailable"} · Trip ID: {selected_trip["trip_id"]}')

        try:
            details = engine.get_route_details(selected_trip_id)
            all_stops = details.get("stops", [])
            # Keep the timeline focused on the selected journey segment, including endpoints.
            start_idx = next((i for i, s in enumerate(all_stops) if str(s.get("stop_id")) == str(boarding_id)), None)
            end_idx = next((i for i, s in enumerate(all_stops) if str(s.get("stop_id")) == str(destination_id) and (start_idx is None or i > start_idx)), None)
            journey_stops = all_stops[start_idx:end_idx + 1] if start_idx is not None and end_idx is not None else all_stops

            map_col, timeline_col = st.columns([1.25, .85], gap="large")
            with map_col:
                st.markdown("### 🗺️ Route map")
                shape_id = details.get("shape_id")
                shape_points = engine.shapes.get(shape_id, []) if shape_id else []
                coordinates = [
                    [float(point[0]), float(point[1])]
                    for point in shape_points
                    if isinstance(point, (list, tuple)) and len(point) >= 2
                ]
                if not coordinates:
                    coordinates = [get_stop_coords(s) for s in journey_stops]
                    coordinates = [point for point in coordinates if point]
                valid_stops = [(s, get_stop_coords(s)) for s in journey_stops]
                valid_stops = [(s, c) for s, c in valid_stops if c]
                if coordinates and valid_stops:
                    route_map = folium.Map(location=coordinates[len(coordinates)//2], zoom_start=12, tiles="OpenStreetMap")
                    folium.PolyLine(coordinates, color="#43e0c0", weight=5, opacity=.9, tooltip=f'Route {selected_trip["route_number"]}').add_to(route_map)
                    for idx, (stop, coord) in enumerate(valid_stops):
                        is_first = str(stop.get("stop_id")) == str(boarding_id)
                        is_last = str(stop.get("stop_id")) == str(destination_id)
                        color = "green" if is_first else ("red" if is_last else "cadetblue")
                        label = "BOARD" if is_first else ("DESTINATION" if is_last else f'STOP {idx+1}')
                        folium.CircleMarker(
                            location=coord, radius=8 if (is_first or is_last) else 5,
                            color=color, fill=True, fill_opacity=.95,
                            tooltip=f'{label}: {stop.get("name", "Unknown")}',
                            popup=f'{stop.get("sequence", idx+1)}. {stop.get("name", "Unknown")}',
                        ).add_to(route_map)
                    route_map.fit_bounds(coordinates)
                    st_folium(route_map, use_container_width=True, height=430, key=f"map_{selected_trip_id}")
                else:
                    st.warning("No coordinates are available for this trip.")
                st.caption("OpenStreetMap tiles need no API key. Route and stop positions come from the loaded GTFS data, not live bus tracking.")

            with timeline_col:
                st.markdown("### 📍 Stop-by-stop")
                st.caption(f"{len(journey_stops)} stops in this journey segment")
                with st.container(height=390, border=True):
                    render_timeline(journey_stops)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            st.error(f"Could not display trip details: {exc}")

# ---------- Quick demo and manual search ----------
with st.expander("⚡ Quick demo: verified K-2 journey", expanded=False):
    st.write("K-2 · Mysore Road Bus Station (21042) → Hebbala (20817)")
    if st.button("Load verified K-2 journey", use_container_width=True):
        save_search("21042", "20817")
        st.session_state["suitability_result"] = {
            "status": "suitable",
            "message": "Trip 31294 in the loaded dataset visits Mysore Road Bus Station before Hebbala."
        }
        st.rerun()

with st.expander("🔎 Find a direct bus manually", expanded=False):
    st.caption("Use this when you want to explore the dataset without scanning a bus image.")
    a, b = st.columns(2)
    with a:
        manual_boarding_query = st.text_input("Search boarding stop", placeholder="e.g. Mysore Road", key="manual_boarding_query")
        manual_boarding_matches = search_stops(manual_boarding_query)
        manual_boarding = st.selectbox("Select boarding stop", manual_boarding_matches, format_func=stop_label, key="manual_boarding_stop") if manual_boarding_matches else None
    with b:
        manual_destination_query = st.text_input("Search destination", placeholder="e.g. Hebbala", key="manual_destination_query")
        manual_destination_matches = search_stops(manual_destination_query)
        manual_destination = st.selectbox("Select destination", manual_destination_matches, format_func=stop_label, key="manual_destination_stop") if manual_destination_matches else None
    if st.button("Find direct trips", use_container_width=True):
        if manual_boarding and manual_destination:
            save_search(manual_boarding["stop_id"], manual_destination["stop_id"])
            st.rerun()
        else:
            st.warning("Search for and select both stops first.")
    if st.session_state.get("search_error"):
        st.error(st.session_state["search_error"])

st.markdown("---")
st.markdown('<div class="nk-muted">NammaKannu prototype · Limited unofficial GTFS data · Confirm the route number and direction before boarding. Scheduled route checks are not live vehicle tracking.</div>', unsafe_allow_html=True)
