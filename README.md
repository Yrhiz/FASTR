# FASTR: A Smart Commuter Recommendation System

Python implementation for the mini research and exposition paper
*FASTR: A Smart Commuter Recommendation System*
(MCS 306, Bulacan State University, Academic Year 2026-2027).

FASTR is a hybrid decision support system for commuters in Malolos, Bulacan. It works in two stages:

1. **Rule-based filtering (Expert System).** Production rules and forward chaining remove alternatives that break a hard constraint: budget limit, mode not operating at that hour, trip too long for the mode, waiting time above the commuter's limit (Eqs. 1, 5 and 6 of the paper).
2. **Weighted Scoring Model (MCDM).** The remaining alternatives are scored with ratio normalization and a weighted sum (Eqs. 2-4).

An explanation facility shows why an alternative was excluded or ranked first.

The repository contains two programs:

| Program | What it does |
|---|---|
| `app.py` | **Interactive web app.** The commuter types any origin and destination in Malolos, chooses the departure time, budget and criterion weights, and gets a recommendation with an explanation. |
| `main.py` | **Paper reproduction and analysis.** Reproduces the BulSU to Barasoain Church example (Tables 3-6) and generates the tables and figures in `results/`. |

## Repository structure

| File / folder | Purpose |
|---|---|
| `app.py`, `templates/index.html` | Web app (Flask) |
| `service.py` | Connects places, trip estimates, rules, scoring and explanations for one request |
| `places.py` | Converts typed places to coordinates and estimates road distance |
| `traffic.py` | Picks the congestion level of a trip from the traffic dataset (counting nodes near the route, direction, hour, day type) |
| `roads.py` | Lists the main roads (speed limit, lanes) along a trip from `road_segments.csv` |
| `trip.py` | Estimates fare, travel time, traffic and waiting time of each mode for a trip |
| `rules.py` | Stage 1: facts, rules, forward chaining, filtering |
| `wsm.py` | Stage 2: normalization, weighted score, ranking, full pipeline |
| `explain.py` | Explanation facility (proof traces) |
| `analysis.py`, `plots.py`, `main.py` | Sensitivity, break-even weights, runtime test, figures, report |
| `config.py` | Criteria, weights and settings |
| `plots.py` | Generating plots |
| `data/` | Input data (see below) |
| `results/` | Generated tables (CSV), figures (PNG) and console output |
| `tests/` | Checks that the code reproduces the paper's tables and that the app works |

## How to run

Requires Python 3.9 or newer.

```bash
git clone <repository-url>
cd <repository-folder>
pip install -r requirements.txt

python app.py        # web app: open http://127.0.0.1:5000 in a browser
python main.py       # paper example, analysis tables and figures in results/
python tests/test_fastr.py
python tests/test_app.py
```

## Using the web app

1. Type the **From** and **To** places. You can pick a suggestion, type any place name, or paste coordinates such as `14.8465, 120.8128` copied from Google Maps.
2. Choose the **departure time**, the **budget** (or tick "No budget limit") and, optionally, the **longest waiting time** you accept.
3. Move the **sliders** to set how important travel time, fare, traffic and waiting time are. The values are converted to percentages that add up to 100%.
4. Press **Recommend**. The page shows the recommended option, all options with their scores, the reason for every excluded option, and the explanation.

The page shows an **interactive map** (OpenStreetMap through Leaflet). Click the map to set the starting point and the destination, or use the "Pick on map" buttons; drag a marker to adjust it. After you press **Recommend**, the app draws the road route, colors it by the congestion level at your departure time (green, amber or red), and shows the recommended option on the map. The map, the route and the road distance need an internet connection; the rest of the app works without it.

Place lookup works in this order: typed coordinates, then places in `data/places.csv` (names and aliases), then an **online lookup with OpenStreetMap Nominatim** (needs internet; restricted to Malolos). Set `FASTR_ONLINE=0` to switch the online place lookup and OSRM distance off. The public Nominatim and OSRM servers are free services meant for light use, which is fine for a class demonstration. Trips outside the Malolos area are rejected.

## Input data (`data/`)

The place, road and traffic files were built for this project from OpenStreetMap, PhilAtlas, Wikipedia and the Malolos traffic-volume thesis. The traffic curves are **approximations rebuilt from the GIS**, not raw counts. Fares, speeds and waiting times in `mode_profiles.csv` are the group's assumptions and should be confirmed.

| File | Content | What to replace |
|---|---|---|
| `places.csv` | 1,743 places: 51 barangays, landmarks, streets and OSM places (columns name, lat, lon, aliases, source, type, category, barangay). Map data (c) OpenStreetMap contributors (ODbL) | Add places or fix coordinates |
| `road_segments.csv` | OSM main-road segments with lanes and speed limit | - |
| `traffic_nodes.csv` | Coordinates of the 9 counting nodes of the thesis | Check the coordinates |
| `mode_profiles.csv` | Fare formula, free-flow speed, waiting time (peak / off-peak), traffic exposure, distance limit and service hours of each mode | Your gathered fares, waiting times and service hours |
| `malolos_hourly_traffic.csv` | Vehicles/hour, speed and congestion level (1-5) for each node, direction, hour and day type (regular, pre-holiday, holiday, post-holiday) | The output of the traffic study |
| `modes.csv` | The three alternatives of the paper's example (used by `main.py`) | - |

How the app estimates a trip (`trip.py`):

- fare = base fare, plus the per-km rate for distance beyond the base distance (rounded to pesos)
- congestion of the route = average level of the counting nodes within 1 km of the straight line origin-destination, for the trip direction (northbound/southbound), hour and day type chosen in the app; if no node is near, the nearest node (within 2.5 km) or the city-wide average is used (`traffic.py`)
- traffic level of a mode = 1 + (congestion level - 1) x traffic exposure
- speed = free-flow speed x (1 - 0.12 x (traffic level - 1)); travel time = distance / speed
- road distance = the road route from OSRM (OpenStreetMap data) when online, otherwise straight-line distance x 1.3 (assumed)

The factors 0.12 and 1.3 are assumptions in `config.py` and should be calibrated with your own measurements.

## Main results of the paper example (`python main.py`)

- The special-trip tricycle (PHP 80) exceeds the student's PHP 50 budget and is excluded by rule `R1`.
- Jeepney: score 0.838 (rank 2). Shared tricycle: score 0.913 (rank 1).
- The ranking did not change in any of the 16 weight-sensitivity runs. The jeepney overtakes only if the fare weight rises above about 0.382 (currently 0.25).


