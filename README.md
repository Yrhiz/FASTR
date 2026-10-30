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
| `main.py` |**Results and analysis.** Runs the same pipeline as the web app for one report trip (BulSU to Barasoain Church, set in `config.py` as `REPORT_TRIP`) and writes the tables and figures in `results/`. |

## Repository structure

| File / folder | Purpose |
|---|---|
| `app.py`, `templates/index.html` | Web app (Flask) |
| `service.py` | Connects places, trip estimates, rules, scoring and explanations for one request (`evaluate_trip` is used by both the web app and `main.py`) |
| `places.py` | Converts typed places to coordinates and estimates road distance |
| `traffic.py` | Picks the congestion level of a trip from the traffic dataset (counting nodes near the route, direction, hour, day type) |
| `roads.py` | Lists the main roads (speed limit, lanes) along a trip from `road_segments.csv` |
| `trip.py` | Estimates fare, travel time, traffic, and waiting time of each mode for a trip |
| `rules.py` | Stage 1: facts, rules, forward chaining, filtering |
| `wsm.py` | Stage 2: normalization, weighted score, ranking, full pipeline |
| `explain.py` | Explanation facility (proof traces) |
| `analysis.py`, `plots.py`, `main.py` | Sensitivity, break-even weights, runtime test, figures, report |
| `config.py` | Criteria, weights, report trip and settings |
| `data/` | Input data (see below) |
| `results/` | Generated tables (CSV), figures (PNG) and console output |
| `tests/` | Checks of the method (hand-computed values), of the app, and that `results/` matches what the app returns |

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


How the app estimates a trip (`trip.py`):

- fare = base fare, plus the per-km rate for distance beyond the base distance (rounded to pesos)
- congestion of the route = average level of the counting nodes within 1 km of the straight line origin-destination, for the trip direction (northbound/southbound), hour and day type chosen in the app; if no node is near, the nearest node (within 2.5 km) or the city-wide average is used (`traffic.py`)
- traffic level of a mode = 1 + (congestion level - 1) x traffic exposure
- speed = free-flow speed x (1 - 0.12 x (traffic level - 1)); travel time = distance / speed
- road distance = the road route from OSRM (OpenStreetMap data) when online, otherwise straight-line distance x 1.3 (assumed)

The factors 0.12 and 1.3 are assumptions in `config.py` and should be calibrated with your own measurements.

## Results and how they match the web app (`python main.py`)

`main.py` does not use separate data. It calls `service.evaluate_trip()` - the function behind the web app - for the report trip in `config.py`:

> Bulacan State University to Barasoain Church, 8:00 AM, regular day, budget PHP 30, default weights 35 / 25 / 25 / 15, offline distance estimate (straight line x 1.3 = 1.67 km).

Result (`results/table_trip_options.csv`, identical to the web app's "All options" table):

| Option | Fare (PHP) | Travel (min) | Waiting (min) | Traffic | Status | Score | Rank |
|---|---|---|---|---|---|---|---|
| Jeepney | 13 | 5.7 | 7.0 | 2.0 | Feasible | 0.911 | 1 |
| Shared tricycle | 18 | 6.2 | 4.0 | 1.8 | Feasible | 0.904 | 2 |
| Special-trip tricycle | 37 | 5.0 | 2.0 | 1.8 | Excluded (rule R1: fare 37 > budget 30) | - | - |

The margin between the two feasible options is small (0.007), and 6 of the 16 sensitivity runs change the ranking, so the recommendation depends on the weights. To see the same numbers in the app, start it with `FASTR_ONLINE=0 python app.py` and enter the trip above; with online mode on, the road distance comes from OSRM and the numbers change slightly. `tests/test_app.py` fails if `results/` and the app ever disagree. Run `python main.py` again after changing any data file or setting.

Timings in section F and `fig7_computational_cost.png` depend on the computer; everything else is deterministic.


