"""
config.py - Settings, constants and data loading for FASTR.

All numbers that define the study (criteria, weights, commuter profile) are
kept here so they can be changed in one place.
"""
import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "modes.csv"
RESULTS_DIR = ROOT / "results"

# ---- Criteria (Table 2 of the paper) ---------------------------------
CRITERIA = ["Time", "Fare", "Traffic", "Availability"]
KEYS = ["time", "fare", "traffic", "availability"]      # column names of a mode
COST = np.array([True, True, True, False])              # C1-C3 are cost, C4 is benefit

# ---- Weights (Eq. 7): time, fare, traffic, availability -------------
WEIGHTS = np.array([0.35, 0.25, 0.25, 0.15])
TOL = 1e-9                                              # tolerance for sum(w) = 1 and bisection

# ---- Commuter profile used in the illustrative example (Section 4.2) --
COMMUTER = {"student": True, "budget": 50}              # student with a PHP 50 budget


def _number(text):
    """Convert a CSV cell to int/float; an empty cell becomes None (value not given)."""
    text = text.strip()
    if text == "":
        return None
    value = float(text)
    return int(value) if value.is_integer() else value


def load_modes(path=DATA_FILE):
    """Read the transportation alternatives from a CSV file.
    Returns a list of dictionaries with keys name, time, fare, traffic, availability, available."""
    modes = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            modes.append({
                "name": row["name"].strip(),
                "time": _number(row["time"]),
                "fare": _number(row["fare"]),
                "traffic": _number(row["traffic"]),
                "availability": _number(row["availability"]),
                "available": row["available"].strip().lower() == "true",
            })
    return modes


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

# Criteria used by the app. Traffic enters the travel-time estimate and is also
# shown as a congestion rating; availability is measured as waiting time (minutes).
APP_CRITERIA = ["Travel time", "Fare", "Traffic", "Waiting time"]
APP_KEYS = ["time", "fare", "traffic", "wait"]
APP_COST = np.array([True, True, True, True])           # all four are cost criteria
APP_WEIGHTS = np.array([0.35, 0.25, 0.25, 0.15])        # default weights (the user may change them)

# Assumptions of the trip estimator - replace them with your gathered data
CIRCUITY = 1.3        # road distance = straight-line distance x 1.3 (assumed)
TRAFFIC_K = 0.12      # each congestion level above 1 lowers speed by 12 % of free-flow speed (assumed)
MIN_DISTANCE_KM = 0.1

# Approximate bounding box of Malolos (lat_min, lat_max, lon_min, lon_max). FASTR covers trips inside it.
MALOLOS_BOUNDS = (14.74, 14.90, 120.77, 120.88)
