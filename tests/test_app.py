"""
Tests for the interactive app (places, trip estimator, rules and the Flask pages).
Run from the repository folder:   python tests/test_app.py     (or: pytest)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["FASTR_ONLINE"] = "0"                      # never use the internet in tests

import numpy as np

from app import app
from places import PlaceError, haversine_km, load_places, resolve_place, suggested_places
from roads import roads_on_route
from traffic import SEASON_KEYS, citywide_by_hour, traffic_for_trip
from service import normalize_weights, recommend_trip
from trip import build_trip_modes, load_profiles, load_traffic

PLACES = load_places()
BULSU, BARASOAIN = "Bulacan State University", "Barasoain Church"


def test_resolve_by_name_alias_and_spelling():
    assert resolve_place("Barasoain Church", PLACES, online=False)["name"] == "Barasoain Church"
    assert resolve_place("BulSU", PLACES, online=False)["name"].startswith("Bulacan State University")
    assert resolve_place("barasoain chrch", PLACES, online=False)["name"] == "Barasoain Church"


def test_resolve_typed_coordinates():
    p = resolve_place("14.8465, 120.8128", PLACES, online=False)
    assert abs(p["lat"] - 14.8465) < 1e-9 and p["source"] == "typed coordinates"


def test_place_errors():
    for bad in ["", "Nowhere Land", "Qwertyuiop Plaza", "14.60, 120.98"]:   # unknown places are not guessed offline
        try:
            resolve_place(bad, PLACES, online=False)
        except PlaceError:
            continue
        raise AssertionError(f"expected PlaceError for {bad!r}")


def test_places_dataset_is_used():
    assert len(PLACES) > 1500                                              # barangays + landmarks + streets + OSM places
    assert resolve_place("Malolos Cathedral", PLACES, online=False)["type"] in ("landmark", "place")
    assert resolve_place("Pamarawan", PLACES, online=False)["type"] == "barangay"   # inside the widened bounds
    names = suggested_places(PLACES)
    assert "Barasoain Church" in names and 50 < len(names) < len(PLACES) and len(names) == len(set(n.casefold() for n in names))
    assert resolve_place("7-Eleven", PLACES, online=False)["name"]       # chain stores share a name: first match is used


def test_distance_is_reasonable():
    d = haversine_km(14.8580, 120.8138, 14.8465, 120.8128)
    assert 1.2 < d < 1.4                              # about 1.3 km straight line


def test_traffic_dataset():
    for season in SEASON_KEYS:
        city = citywide_by_hour(season)
        assert len(city) == 24 and all(1 <= lv <= 5 for lv, _ in city.values())
    city = citywide_by_hour("regular")
    assert city[8][0] > city[3][0] and city[8][1] and not city[3][1]      # morning peak vs 3 AM
    o, d = (resolve_place(x, PLACES, online=False) for x in (BULSU, BARASOAIN))
    t = traffic_for_trip(o, d, 8)
    assert t["nodes"] and 1 <= t["level"] <= 5 and t["direction"] == "SB"   # Barasoain is south of BulSU
    far = traffic_for_trip(resolve_place("Pamarawan", PLACES, online=False), resolve_place("Mambog", PLACES, online=False), 8)
    assert far["nodes"] == [] and "city-wide" in far["basis"]               # no counting node near this route
    try:
        traffic_for_trip(o, d, 8, "monsoon")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown season must be rejected")
    names = [r["name"] for r in roads_on_route(o, d)]
    assert "MacArthur Highway" in names


def test_trip_estimates():
    modes = build_trip_modes(load_profiles(), 1.67, 8, load_traffic())
    by = {m["name"]: m for m in modes}
    # fares from data/mode_profiles.csv: jeepney PHP 13 (first 4 km); tricycle matrix PHP 15 / PHP 30 first km + PHP 5 / PHP 10 per km
    assert by["Jeepney"]["fare"] == 13 and by["Shared tricycle"]["fare"] == 18 and by["Special-trip tricycle"]["fare"] == 37
    assert all(m["time"] > 0 and m["wait"] > 0 for m in modes)


def test_weights_normalized():
    w = normalize_weights([35, 25, 25, 15])
    assert abs(w.sum() - 1) < 1e-12 and np.allclose(w, [0.35, 0.25, 0.25, 0.15])


def test_budget_rule_in_app():
    r = recommend_trip(BULSU, BARASOAIN, 8, budget=30, online=False)
    excluded = [x["name"] for x in r["rows"] if x["excluded"]]
    assert excluded == ["Special-trip tricycle"] and r["best"] in ("Jeepney", "Shared tricycle")   # PHP 37 > PHP 30
    assert "37" in r["hint"]
    r = recommend_trip(BULSU, BARASOAIN, 8, budget=10, online=False)
    assert r["best"] is None and r["hint"]


def test_service_hours_and_wait_rules():
    r = recommend_trip(BULSU, BARASOAIN, 3, budget=None, online=False)       # 3 AM
    assert [x["name"] for x in r["rows"] if not x["excluded"]] == ["Special-trip tricycle"]
    r = recommend_trip(BULSU, BARASOAIN, 8, budget=None, max_wait=3, online=False)
    assert [x["name"] for x in r["rows"] if not x["excluded"]] == ["Special-trip tricycle"]


def test_weights_change_the_recommendation():
    fare = recommend_trip(BULSU, BARASOAIN, 8, budget=30, raw_weights=[5, 90, 5, 0], online=False)
    time_ = recommend_trip(BULSU, BARASOAIN, 8, budget=None, raw_weights=[90, 5, 0, 5], online=False)
    assert fare["best"] == "Jeepney" and time_["best"] == "Special-trip tricycle"


def test_season_and_hour_change_congestion():
    peak = recommend_trip(BULSU, BARASOAIN, 8, budget=None, online=False)
    night = recommend_trip(BULSU, BARASOAIN, 3, budget=None, online=False)
    assert peak["congestion"] > night["congestion"] and peak["season"] == "regular"
    for season in SEASON_KEYS:
        assert recommend_trip(BULSU, BARASOAIN, 17, budget=None, online=False, season=season)["season"] == season


def test_osrm_distance_is_used_when_online():
    import io, json, urllib.request
    import places

    class Fake(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    real = urllib.request.urlopen
    urllib.request.urlopen = lambda req, timeout=0: Fake(json.dumps({"routes": [{"distance": 2150.0}]}).encode())
    places.osrm_route_km.cache_clear()
    try:
        r = recommend_trip(BULSU, BARASOAIN, 8, budget=30, online=True)
        assert r["distance_km"] == 2.15 and "OSRM" in r["distance_source"]
        urllib.request.urlopen = lambda req, timeout=0: (_ for _ in ()).throw(OSError("offline"))
        places.osrm_route_km.cache_clear()
        r = recommend_trip(BULSU, BARASOAIN, 8, budget=30, online=True)      # falls back to the estimate
        assert "estimate" in r["distance_source"]
    finally:
        urllib.request.urlopen = real
        places.osrm_route_km.cache_clear()


def test_web_pages():
    c = app.test_client()
    assert c.get("/").status_code == 200
    page = c.post("/", data={"origin": BULSU, "destination": BARASOAIN, "hour": "8", "budget": "30", "season": "holiday",
                             "w0": "35", "w1": "25", "w2": "25", "w3": "15"}).get_data(as_text=True)
    assert "Recommended: " in page and "Traffic data used" in page and 'id="map"' in page and "var TRIP = {" in page
    bad = c.post("/", data={"origin": BULSU, "destination": "Nowhere Land", "hour": "8", "budget": "50",
                            "w0": "35", "w1": "25", "w2": "25", "w3": "15"}).get_data(as_text=True)
    assert "Could not find" in bad
    api = c.post("/api/recommend", json={"origin": BULSU, "destination": BARASOAIN, "hour": 8, "budget": 30, "season": "regular"})
    assert api.status_code == 200 and api.get_json()["best"] in ("Jeepney", "Shared tricycle")


def test_results_folder_matches_the_web_app():
    """The CSV tables written by main.py must equal what the web app returns for the same trip."""
    import pandas as pd
    from config import REPORT_TRIP as T, RESULTS_DIR
    r = recommend_trip(T["origin"], T["destination"], T["hour"], T["budget"], T["max_wait"],
                       online=False, season=T["season"])
    opts = pd.read_csv(RESULTS_DIR / "table_trip_options.csv")
    assert len(opts) == len(r["rows"])
    for (_, o), row in zip(opts.iterrows(), r["rows"]):
        assert o["Option"] == row["name"] and o["Fare (PHP)"] == row["fare"]
        assert abs(o["Travel time (min)"] - row["time"]) < 1e-9 and abs(o["Waiting (min)"] - row["wait"]) < 1e-9
        assert abs(o["Traffic (1-5)"] - row["traffic"]) < 1e-9
        assert (o["Status"] == "Excluded") == row["excluded"]
        if not row["excluded"]:
            assert abs(o["Score"] - row["score"]) < 1e-9 and int(o["Rank"]) == row["rank"]
    scores = pd.read_csv(RESULTS_DIR / "table_scores.csv", index_col=0)
    assert scores["Score"].idxmax() == r["best"] and abs(scores["Score"].max() - r["best_score"]) < 1e-9
    filt = pd.read_csv(RESULTS_DIR / "table_filtering.csv")
    assert set(filt[filt["Decision"] == "Excluded"]["Alternative"]) == {x["name"] for x in r["rows"] if x["excluded"]}
    page = app.test_client().post("/", data={"origin": T["origin"], "destination": T["destination"], "hour": str(T["hour"]),
            "budget": str(T["budget"]), "season": T["season"], "w0": "35", "w1": "25", "w2": "25", "w3": "15"}).get_data(as_text=True)
    assert f"Recommended: {r['best']}" in page and f"{r['best_score']:.3f}" in page


def test_api_rejects_bad_input():
    c = app.test_client()
    assert c.post("/api/recommend", json={"origin": BULSU, "destination": BARASOAIN, "weights": [1, 2]}).status_code == 400
    assert c.post("/api/recommend", json={"origin": BULSU, "destination": BARASOAIN, "budget": "abc"}).status_code == 400
    ok = c.post("/api/recommend", json={"origin": BULSU, "destination": BARASOAIN, "budget": "30"})
    assert ok.status_code == 200


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"{len(tests)} tests passed")
