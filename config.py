"""
config.py - Settings and constants for FASTR.

All numbers that define the study (criteria, weights, report trip) are
kept here so they can be changed in one place.
"""
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"

# ---- Criteria: the SAME four criteria are used by the web app and by main.py -------
# Travel time, fare and waiting time are minutes/pesos (smaller is better); traffic is the
# congestion exposure of the mode (1 = free flow ... 5 = heavy, smaller is better).
CRITERIA = ["Travel time", "Fare", "Traffic", "Waiting time"]
KEYS = ["time", "fare", "traffic", "wait"]              # keys of a mode dictionary (see trip.py)
COST = np.array([True, True, True, True])               # all four are cost criteria (min / x)

# ---- Default weights (Eq. 7): time, fare, traffic, waiting; the web app lets the user change them
WEIGHTS = np.array([0.35, 0.25, 0.25, 0.15])
TOL = 1e-9                                              # tolerance for sum(w) = 1 and bisection

# ---- The trip reproduced in results/ (main.py).  The web app, started with these same inputs
# ---- and FASTR_ONLINE=0, returns exactly the numbers written to results/ (tests/test_app.py checks it).
REPORT_TRIP = {"origin": "Bulacan State University", "destination": "Barasoain Church",
               "hour": 8, "season": "regular", "budget": 30, "max_wait": None}
REPORT_ONLINE = False       # results use the offline distance estimate so they are reproducible


# =====================================================================
# Settings for the interactive app (app.py)
# =====================================================================
PLACES_FILE = ROOT / "data" / "places.csv"
PROFILES_FILE = ROOT / "data" / "mode_profiles.csv"
TRAFFIC_FILE = ROOT / "data" / "malolos_hourly_traffic.csv"   # hourly traffic per counting node, direction, season
NODES_FILE = ROOT / "data" / "traffic_nodes.csv"             # coordinates of the 9 counting nodes
ROADS_FILE = ROOT / "data" / "road_segments.csv"             # OSM road segments (name, lanes, speed limit)

# Seasons available in the traffic dataset: (key, label shown in the app)
SEASONS = [("regular", "Regular day"), ("pre_holiday", "Before a holiday"),
           ("holiday", "Holiday"), ("post_holiday", "After a holiday")]

# How a trip is matched to the counting nodes (see traffic.py)
CORRIDOR_KM = 1.0          # nodes within 1 km of the straight line origin -> destination are used
FALLBACK_NODE_KM = 2.5     # if none, the nearest node is used when it is within 2.5 km
ROAD_CORRIDOR_KM = 0.15    # road segments within 150 m of the route are listed in the result

# Assumptions of the trip estimator - replace them with your gathered data
CIRCUITY = 1.3        # road distance = straight-line distance x 1.3 (assumed)
TRAFFIC_K = 0.12      # each congestion level above 1 lowers speed by 12 % of free-flow speed (assumed)
MIN_DISTANCE_KM = 0.1

# Approximate bounding box of Malolos (lat_min, lat_max, lon_min, lon_max). FASTR covers trips inside it.
MALOLOS_BOUNDS = (14.74, 14.90, 120.77, 120.88)
