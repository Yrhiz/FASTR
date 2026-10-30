"""
traffic.py - Congestion level and peak flag for a trip, from the traffic-volume dataset.

Data: data/malolos_hourly_traffic.csv (hourly vehicles per hour at the 9 counting nodes of the
Malolos traffic study, both directions, four seasons) and data/traffic_nodes.csv (node coordinates).

How a trip gets its congestion level (1 = free flow ... 5 = heavy):
  1. direction  : northbound if the destination is north of the origin, southbound if south
                  (east-west trips use both directions).
  2. nodes      : counting nodes within CORRIDOR_KM of the straight line origin -> destination.
                  If there is none, the nearest node is used when it is within FALLBACK_NODE_KM.
  3. level      : mean of `traffic_level_1to5` of those nodes at the departure hour and season.
                  If no node applies, the city-wide mean of all nodes at that hour is used.
  4. peak flag  : the hour is a peak hour when the dataset marks it am_peak (6-9) or pm_peak (16-19).
"""
import csv
import math
from functools import lru_cache

from config import (CORRIDOR_KM, FALLBACK_NODE_KM, NODES_FILE, SEASONS, TRAFFIC_FILE)

PEAK_PERIODS = {"am_peak", "pm_peak"}
SEASON_KEYS = [k for k, _ in SEASONS]


@lru_cache(maxsize=4)
def _table(path=str(TRAFFIC_FILE)):
    """{(node, direction, season, hour): {"level", "vph", "period", "confidence"}}"""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["node"], r["direction"], r["season"], int(r["hour"]))] = {
                "level": float(r["traffic_level_1to5"]), "vph": float(r["vph"]),
                "period": r["period"], "confidence": r["confidence"]}
    return out


@lru_cache(maxsize=4)
def load_nodes(path=str(NODES_FILE)):
    with open(path, newline="", encoding="utf-8") as f:
        return [{"node": r["node"].strip(), "lat": float(r["lat"]), "lon": float(r["lon"]),
                 "basis": r["coord_basis"].strip()} for r in csv.DictReader(f)]


def check_season(season):
    if season not in SEASON_KEYS:
        raise ValueError(f"Unknown season '{season}'. Choose one of: {', '.join(SEASON_KEYS)}.")
    return season


def _xy(lat, lon, lat0):
    """Local flat-earth coordinates in km (accurate enough inside one city)."""
    return lon * 111.32 * math.cos(math.radians(lat0)), lat * 110.57


def point_segment_km(p, a, b):
    """Distance in km from point p to the segment a-b; each point is a (lat, lon) pair."""
    lat0 = (a[0] + b[0]) / 2
    px, py = _xy(*p, lat0); ax, ay = _xy(*a, lat0); bx, by = _xy(*b, lat0)
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def trip_direction(origin, destination, min_dlat=0.002):
    """'NB', 'SB' or None (mostly east-west trip, about 220 m of latitude change or less)."""
    dlat = destination["lat"] - origin["lat"]
    if abs(dlat) < min_dlat:
        return None
    return "NB" if dlat > 0 else "SB"


def citywide_by_hour(season="regular"):
    """{hour: (mean congestion level over all nodes, is_peak)} - used when no trip is given."""
    check_season(season)
    t = _table()
    out = {}
    for h in range(24):
        rows = [v for (n, d, s, hh), v in t.items() if s == season and hh == h]
        out[h] = (round(sum(r["level"] for r in rows) / len(rows), 2),
                  any(r["period"] in PEAK_PERIODS for r in rows))
    return out


def traffic_for_trip(origin, destination, hour, season="regular"):
    """Congestion information for one trip. origin/destination are dicts with lat and lon."""
    check_season(season)
    t, nodes = _table(), load_nodes()
    direction = trip_direction(origin, destination)
    a, b = (origin["lat"], origin["lon"]), (destination["lat"], destination["lon"])
    dist = {n["node"]: point_segment_km((n["lat"], n["lon"]), a, b) for n in nodes}

    chosen = [n["node"] for n in nodes if dist[n["node"]] <= CORRIDOR_KM]
    basis = f"counting nodes within {CORRIDOR_KM:g} km of the route"
    if not chosen:
        nearest = min(dist, key=dist.get)
        if dist[nearest] <= FALLBACK_NODE_KM:
            chosen = [nearest]
            basis = f"nearest counting node ({dist[nearest]:.1f} km from the route)"

    def collect(use_direction):
        found = []
        for node in chosen:
            for d in ("NB", "SB"):
                if use_direction and direction and d != direction:
                    continue
                row = t.get((node, d, season, hour))
                if row:
                    found.append((node, d, row))
        return found

    rows = collect(True) or collect(False)
    if not rows:                                          # no counting node near the route
        level, peak = citywide_by_hour(season)[hour]
        return {"level": level, "is_peak": peak, "nodes": [], "direction": direction,
                "basis": "city-wide average of all counting nodes (no node near the route)",
                "season": season, "low_confidence": False}
    return {"level": round(sum(r["level"] for _, _, r in rows) / len(rows), 2),
            "is_peak": any(r["period"] in PEAK_PERIODS for _, _, r in rows),
            "nodes": sorted({n for n, _, _ in rows}), "direction": direction, "basis": basis,
            "season": season, "low_confidence": any(r["confidence"] == "low" for _, _, r in rows)}
