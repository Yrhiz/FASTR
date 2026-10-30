"""
service.py - Connects everything for one request: places -> distance -> mode estimates
-> rule filtering -> weighted scoring -> explanations. Used by the web app (app.py).
"""
import numpy as np

from config import APP_CRITERIA, APP_COST, APP_KEYS, APP_WEIGHTS
from explain import explain_exclusion, explain_ranking
from places import PlaceError, load_places, osrm_route_km, resolve_place, road_distance_km
from roads import roads_on_route
from traffic import check_season, traffic_for_trip
from trip import build_trip_modes, hour_label, load_profiles
from wsm import hybrid_recommend, r3


def normalize_weights(raw):
    """Turn slider values into weights that sum to 1."""
    raw = np.asarray(raw, dtype=float)
    if (raw < 0).any() or raw.sum() <= 0:
        raise ValueError("Set at least one criterion weight above zero.")
    return raw / raw.sum()


def _reason(res, name):
    """Short reason why a mode was excluded, taken from the proof trace."""
    for t in res["trace"]:
        if t["conclusion"] == f"Infeasible({name})":
            facts = [p for p in t["premises"] if p not in ("HasBudget", "HasWaitLimit")]
            return "; ".join(res["notes"].get(p, p) for p in facts)
    return ""


def recommend_trip(origin_text, destination_text, hour, budget=None, max_wait=None,
                   raw_weights=None, online=True, season="regular"):
    """Run the whole pipeline. Raises PlaceError / ValueError with user-readable messages."""
    weights = normalize_weights(APP_WEIGHTS if raw_weights is None else raw_weights)
    if not 0 <= hour <= 23:
        raise ValueError("The departure hour must be between 0 and 23.")
    if budget is not None and budget < 0:
        raise ValueError("The budget cannot be negative.")
    if max_wait is not None and max_wait < 0:
        raise ValueError("The waiting-time limit cannot be negative.")

    season = check_season(season or "regular")
    places = load_places()
    origin = resolve_place(origin_text, places, online)
    destination = resolve_place(destination_text, places, online)
    distance, distance_source = None, "straight-line distance x 1.3 (estimate)"
    if online:
        distance = osrm_route_km(origin["lat"], origin["lon"], destination["lat"], destination["lon"])
        if distance is not None:
            distance_source = "road route (OpenStreetMap / OSRM)"
    if distance is None:
        distance = road_distance_km(origin, destination)
    trip_traffic = traffic_for_trip(origin, destination, hour, season)     # route-specific congestion
    traffic = {hour: (trip_traffic["level"], trip_traffic["is_peak"])}
    modes = build_trip_modes(load_profiles(), distance, hour, traffic)

    commuter = {"student": False, "budget": budget, "max_wait": max_wait}
    res = hybrid_recommend(commuter, modes, weights, keys=APP_KEYS, cost=APP_COST)

    scores = {}
    if res["S"] is not None:
        for m, s, rk in zip(res["feasible"], res["S"], res["ranks"]):
            scores[m["name"]] = (r3(s), int(rk))
    rows = []
    for m in modes:
        excluded = any(e["name"] == m["name"] for e in res["excluded"])
        score, rank_ = scores.get(m["name"], (None, None))
        rows.append({"name": m["name"], "fare": int(m["fare"]), "time": round(m["time"], 1),
                     "wait": round(m["wait"], 1), "traffic": m["traffic"],
                     "excluded": excluded, "reason": _reason(res, m["name"]) if excluded else "",
                     "score": score, "rank": rank_})
    rows.sort(key=lambda r: (r["excluded"], r["rank"] or 99))

    explanations = [explain_exclusion(m["name"], res) for m in res["excluded"]]
    if res["S"] is not None:
        explanations.append(explain_ranking(res, weights))

    hint = None
    over = [m for m in res["excluded"] if f"ExceedsBudget({m['name']})" in res["facts"]]
    if over and budget is not None:
        cheapest = min(over, key=lambda m: m["fare"])
        hint = f"A budget of at least PHP {cheapest['fare']:.0f} would make the {cheapest['name'].lower()} feasible."

    best_row = next((r for r in rows if r["name"] == res["best"]), None)
    return {"origin": origin, "destination": destination, "distance_km": round(distance, 2),
            "distance_source": distance_source, "best_row": best_row,
            "hour_label": hour_label(hour), "congestion": trip_traffic["level"], "traffic": trip_traffic,
            "roads": roads_on_route(origin, destination), "season": season, "rows": rows,
            "best": res["best"], "best_score": scores[res["best"]][0] if res["best"] else None,
            "weights": [(c, round(float(w) * 100)) for c, w in zip(APP_CRITERIA, weights)],
            "explanations": explanations, "hint": hint, "n_feasible": len(res["feasible"]),
            "passes": res["passes"], "n_rules": res["n_rules"]}
