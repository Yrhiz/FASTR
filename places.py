"""
places.py - Turn a typed place into coordinates and estimate the trip distance.

A place can be given in three ways (tried in this order):
  1. coordinates typed as "lat, lon"  (for example copied from Google Maps): works offline
  2. a name found in data/places.csv  (exact, partial or close spelling): works offline
  3. any other name, looked up online with OpenStreetMap Nominatim, limited to Malolos
     (needs an internet connection; used only if online lookup is enabled)
Every place must lie inside the Malolos bounding box (config.MALOLOS_BOUNDS).
"""
import csv
import difflib
import json
import math
import re
import urllib.parse
import urllib.request
from functools import lru_cache

from config import CIRCUITY, MALOLOS_BOUNDS, PLACES_FILE

_COORD = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*$")


class PlaceError(ValueError):
    """Raised with a message that can be shown to the user."""


def load_places(path=PLACES_FILE):
    with open(path, newline="", encoding="utf-8") as f:
        return [{"name": r["name"].strip(), "lat": float(r["lat"]), "lon": float(r["lon"]),
                 "aliases": [a.strip() for a in (r.get("aliases") or "").split("|") if a.strip()],
                 "source": r.get("source", "").strip(), "type": (r.get("type") or "").strip(),
                 "category": (r.get("category") or "").strip(), "barangay": (r.get("barangay") or "").strip()}
                for r in csv.DictReader(f)]


_TYPE_RANK = {"barangay": 0, "landmark": 1, "street": 2, "place": 3}
# OSM categories of places a commuter is likely to travel to; they appear in the suggestion list
_SUGGEST = ("amenity=school", "amenity=college", "amenity=university", "amenity=hospital", "amenity=townhall",
            "amenity=bus_station", "amenity=police", "amenity=place_of_worship", "shop=mall",
            "shop=supermarket", "shop=department_store", "historic=building", "historic=memorial")


def suggested_places(places):
    """Names for the drop-down list: barangays, landmarks, streets and important places (no duplicates)."""
    out, seen = [], set()
    for p in sorted(places, key=lambda p: _TYPE_RANK.get(p.get("type"), 3)):
        keep = p.get("type") in ("barangay", "landmark", "street") or p.get("category") in _SUGGEST
        if keep and p["name"].casefold() not in seen:
            seen.add(p["name"].casefold())
            out.append(p["name"])
    return out


def in_malolos(lat, lon, bounds=MALOLOS_BOUNDS):
    lat_min, lat_max, lon_min, lon_max = bounds
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle (straight-line) distance in kilometres."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlam = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def road_distance_km(a, b, circuity=CIRCUITY):
    """Estimated road distance = straight-line distance x circuity factor."""
    return haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) * circuity


@lru_cache(maxsize=256)
def geocode_online(query, timeout=6):
    """Look a place up with OpenStreetMap Nominatim (restricted to the Malolos box).
    Returns (lat, lon, display_name) or None. Needs internet access."""
    lat_min, lat_max, lon_min, lon_max = MALOLOS_BOUNDS
    params = {"q": f"{query}, Malolos, Bulacan", "format": "jsonv2", "limit": 1, "countrycodes": "ph",
              "viewbox": f"{lon_min},{lat_max},{lon_max},{lat_min}", "bounded": 1}
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "FASTR-student-project/1.0 (BulSU MCS 306)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except Exception:
        return None
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", query)


@lru_cache(maxsize=256)
def osrm_route_km(lat1, lon1, lat2, lon2, timeout=6):
    """Road distance in km along the real road network, from the public OSRM demo server
    (OpenStreetMap data). Returns None if the server cannot be reached."""
    url = (f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
           "?overview=false")
    req = urllib.request.Request(url, headers={"User-Agent": "FASTR-student-project/1.0 (BulSU MCS 306)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        return float(data["routes"][0]["distance"]) / 1000
    except Exception:
        return None


def resolve_place(text, places, online=True):
    """Return {"name", "lat", "lon", "source"} for the typed text or raise PlaceError."""
    text = (text or "").strip()
    if not text:
        raise PlaceError("Please type an origin and a destination.")

    m = _COORD.match(text)                                           # 1. typed coordinates
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
        place = {"name": f"({lat:.5f}, {lon:.5f})", "lat": lat, "lon": lon, "source": "typed coordinates"}
    else:
        place = _match_known(text, places)                           # 2. known places
        if place is None and online:                                 # 3. online lookup
            found = geocode_online(text)
            if found:
                place = {"name": found[2].split(",")[0], "lat": found[0], "lon": found[1],
                         "source": "OpenStreetMap (Nominatim)"}
        if place is None:
            raise PlaceError(
                f"Could not find '{text}'. Choose a suggested place, type coordinates such as "
                f"14.8465, 120.8128 (copy them from Google Maps), or add the place to data/places.csv.")

    if not in_malolos(place["lat"], place["lon"]):
        raise PlaceError(f"'{text}' is outside the Malolos coverage area of FASTR.")
    return place


def _match_known(text, places):
    """Match a typed name against place names and aliases: exact, then partial, then close spelling."""
    key = text.casefold()
    labels = {}                                    # lower-case label -> place
    # barangays, landmarks and streets win over shops when several places share a name
    for p in sorted(places, key=lambda p: _TYPE_RANK.get(p.get("type"), 3)):
        for label in [p["name"]] + p.get("aliases", []):
            labels.setdefault(label.casefold(), p)
    if key in labels:                                                # exact name or alias
        return labels[key]
    partial = [lab for lab in labels if len(key) >= 3 and key in lab]   # partial name
    if partial:
        return labels[min(partial, key=lambda lab: (_TYPE_RANK.get(labels[lab].get("type"), 3), len(lab)))]
    close = difflib.get_close_matches(key, list(labels), n=1, cutoff=0.85)  # close spelling
    return labels[close[0]] if close else None
