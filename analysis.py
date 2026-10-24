"""
analysis.py - Analysis tools: budget scenarios, weight sensitivity,
break-even weights (bisection) and computational cost.
"""
import time

import numpy as np
import pandas as pd

from config import CRITERIA, TOL, WEIGHTS
from rules import rule_filter
from wsm import decision_matrix, hybrid_recommend, r3, score


# ---------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------
def set_weight(w, j, value):
    """Set weight j to `value` and rescale the other weights proportionally (sum stays 1)."""
    w = np.asarray(w, float).copy()
    others = np.arange(len(w)) != j
    w[others] *= (1 - value) / w[others].sum()
    w[j] = value
    return w


def vary_weight(w, j, pct):
    """Change weight j by pct (e.g. +0.10 = +10 %); the others are rescaled proportionally."""
    return set_weight(w, j, np.asarray(w, float)[j] * (1 + pct))


def sensitivity_table(X, names, a, b, w=WEIGHTS, steps=(-0.20, -0.10, 0.10, 0.20)):
    """Change each weight by the given percentages and record the scores of modes a and b.
    The ranking 'changes' when mode b overtakes mode a."""
    rows = []
    for j, c in enumerate(CRITERIA):
        for p in steps:
            wv = vary_weight(w, j, p)
            s = score(X, wv)
            rows.append({"Criterion": c, "Change": f"{p:+.0%}", "Weights": np.round(wv, 3).tolist(),
                         f"S_{names[a]}": r3(s[a]), f"S_{names[b]}": r3(s[b]),
                         "Best": names[int(np.argmax(s))], "Ranking changed?": bool(s[b] > s[a])})
    return pd.DataFrame(rows)


def critical_weight(X, w_base, j, a, b, tol=TOL, max_iter=200):
    """Weight w_j at which modes a and b have equal scores (the break-even point).
    Bisection on f(v) = S_a - S_b over v in [0, 1].
    Returns (w*, iterations, exact). Because f is linear in v, the closed form
    v* = f(0) / (f(0) - f(1)) is also available and serves as an error check.
    Returns (None, 0, None) if the ranking never reverses."""
    def f(v):
        s = score(X, set_weight(w_base, j, v))
        return s[a] - s[b]
    lo, hi = 0.0, 1.0
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None, 0, None
    exact = flo / (flo - fhi)
    it = 0
    while (hi - lo) / 2 > tol and it < max_iter:
        it += 1
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2, it, exact


# ---------------------------------------------------------------------
# Budget scenarios
# ---------------------------------------------------------------------
def budget_scenarios(modes, budgets):
    """For each budget, list the feasible modes and the recommendation."""
    rows = []
    for b in budgets:
        commuter = {"student": True, "budget": b}
        feasible = [m["name"] for m in rule_filter(commuter, modes)["feasible"]]
        if not feasible:
            rec = "No feasible alternative"
        else:
            try:
                rec = hybrid_recommend(commuter, modes)["best"]
            except ValueError:
                rec = "needs data for all feasible modes"
        rows.append({"Budget (PHP)": b, "Feasible alternatives": ", ".join(feasible) or "none", "Recommended": rec})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Computational cost
# ---------------------------------------------------------------------
def synthetic_modes(n, rng):
    """Random modes for the computational-cost test."""
    return [{"name": f"Mode{i}", "time": float(rng.uniform(5, 90)), "fare": float(rng.uniform(5, 300)),
             "traffic": int(rng.integers(1, 6)), "availability": int(rng.integers(1, 6)),
             "available": bool(rng.random() > 0.1)} for i in range(n)]


def runtime_test(sizes=(10, 100, 1_000, 10_000, 100_000), repeats=3, seed=42):
    """Time the rule filtering and the WSM for an increasing number of modes (best of `repeats`)."""
    rng = np.random.default_rng(seed)
    t_rules, t_wsm = [], []
    for n in sizes:
        modes_n = synthetic_modes(n, rng)
        best_r, best_w = np.inf, np.inf
        for _ in range(repeats):
            t0 = time.perf_counter()
            stage1 = rule_filter({"student": True, "budget": 150}, modes_n)
            t1 = time.perf_counter()
            score(decision_matrix(stage1["feasible"]))
            t2 = time.perf_counter()
            best_r, best_w = min(best_r, t1 - t0), min(best_w, t2 - t1)
        t_rules.append(best_r)
        t_wsm.append(best_w)
    return list(sizes), t_rules, t_wsm
