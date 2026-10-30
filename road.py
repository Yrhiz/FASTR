"""
roads.py - Main roads near a trip, from data/road_segments.csv (OpenStreetMap road segments with
lanes and posted speed limit). Used to tell the commuter which roads the trip runs along.
This is information only: it does not change the scores.
"""
import csv
from collections import Counter, defaultdict
from functools import lru_cache

from config import ROAD_CORRIDOR_KM, ROADS_FILE
from traffic import point_segment_km

MAIN_ROADS = {"trunk", "primary", "secondary", "tertiary"}


@lru_cache(maxsize=2)
def load_roads(path=str(ROADS_FILE)):
    def num(x):
        x = (x or "").strip()
        return int(float(x)) if x else None
    with open(path, newline="", encoding="utf-8") as f:
        return [{"name": r["name"].strip(), "highway": r["highway"], "lanes": num(r["lanes"]),
                 "maxspeed": num(r["maxspeed_kph"]), "lat": float(r["lat"]), "lon": float(r["lon"])}
                for r in csv.DictReader(f) if r["name"].strip()]


def roads_on_route(origin, destination, corridor_km=ROAD_CORRIDOR_KM, limit=4):
    """Main roads whose segments lie within `corridor_km` of the straight line origin -> destination."""
    a, b = (origin["lat"], origin["lon"]), (destination["lat"], destination["lon"])
    near = defaultdict(list)
    for s in load_roads():
        if s["highway"] in MAIN_ROADS and point_segment_km((s["lat"], s["lon"]), a, b) <= corridor_km:
            near[s["name"]].append(s)
    out = []
    for name, segs in sorted(near.items(), key=lambda kv: -len(kv[1]))[:limit]:
        speeds = [s["maxspeed"] for s in segs if s["maxspeed"]]
        lanes = [s["lanes"] for s in segs if s["lanes"]]
        out.append({"name": name,
                    "speed_limit": Counter(speeds).most_common(1)[0][0] if speeds else None,
                    "lanes": (str(min(lanes)) if min(lanes) == max(lanes) else f"{min(lanes)}-{max(lanes)}") if lanes else None})
    return out
