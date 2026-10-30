"""
trip.py - Estimate fare, travel time, traffic and waiting time of every mode for one trip.

Inputs are the distance of the trip, the hour of departure, a mode profile table
(data/mode_profiles.csv) and the congestion level of the route (traffic.py, from
data/malolos_hourly_traffic.csv). The mode profiles are the group's fare/speed/wait assumptions;
the congestion comes from the Malolos traffic study.

Model
-----
  fare         = base_fare                                  if distance <= base_km
               = base_fare + (distance - base_km) * fare_per_km   otherwise  (rounded to PHP)
  traffic      T = 1 + (congestion_level - 1) * traffic_exposure       (1 = free, 5 = heavy)
  speed        v = free_speed * (1 - K * (T - 1))
  travel time  = distance / v * 60                                   (minutes)
  waiting time = wait_peak or wait_offpeak, depending on the hour
"""
import csv
import math

from config import MIN_DISTANCE_KM, PROFILES_FILE, TRAFFIC_K
from traffic import citywide_by_hour


def _num(text):
    text = (text or "").strip()
    return float(text) if text else None


def load_profiles(path=PROFILES_FILE):
    with open(path, newline="", encoding="utf-8") as f:
        return [{"name": r["mode"].strip(), "base_fare": float(r["base_fare"]), "base_km": float(r["base_km"]),
                 "fare_per_km": float(r["fare_per_km"]), "speed": float(r["free_speed_kmh"]),
                 "wait_peak": float(r["wait_peak_min"]), "wait_off": float(r["wait_offpeak_min"]),
                 "exposure": float(r["traffic_exposure"]), "max_km": _num(r["max_distance_km"]),
                 "open_hour": int(r["open_hour"]), "close_hour": int(r["close_hour"])}
                for r in csv.DictReader(f)]


def load_traffic(season="regular"):
    """City-wide {hour: (congestion_level, is_peak)} from the Malolos traffic dataset.
    For a real trip use traffic.traffic_for_trip(), which picks the nodes along the route."""
    return citywide_by_hour(season)


def round_half_up(x):
    return int(math.floor(x + 0.5))


def hour_label(h):
    return f"{(h % 12) or 12}:00 {'AM' if h < 12 else 'PM'}"


def build_trip_modes(profiles, distance_km, hour, traffic, k=TRAFFIC_K):
    """Create one mode dictionary per profile for this trip (keys used by rules.py and wsm.py)."""
    if distance_km < MIN_DISTANCE_KM:
        raise ValueError("The origin and the destination are too close to compare transport modes.")
    level, is_peak = traffic[hour]
    modes = []
    for p in profiles:
        extra = max(0.0, distance_km - p["base_km"])
        fare = max(p["base_fare"], round_half_up(p["base_fare"] + extra * p["fare_per_km"]))
        t_eff = 1 + (level - 1) * p["exposure"]
        speed = p["speed"] * (1 - k * (t_eff - 1))
        modes.append({
            "name": p["name"], "fare": float(fare), "traffic": round(t_eff, 2),
            "time": distance_km / speed * 60, "wait": p["wait_peak"] if is_peak else p["wait_off"],
            "available": True,
            "open": p["open_hour"] <= hour < p["close_hour"],
            "closed_note": f"not operating at {hour_label(hour)} (service {hour_label(p['open_hour'] % 24)}"
                           f" to {hour_label(p['close_hour'] % 24)})",
            "too_far": p["max_km"] is not None and distance_km > p["max_km"],
            "far_note": f"trip of {distance_km:.1f} km exceeds the {p['max_km']:g} km limit of this mode"
                        if p["max_km"] is not None else "",
        })
    return modes
