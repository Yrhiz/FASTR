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
