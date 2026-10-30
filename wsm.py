"""
wsm.py - Stage 2 of FASTR: Weighted Scoring Model (WSM).

Ratio normalization (Eqs. 2-3) and weighted score (Eqs. 4 and 8).
The two stages are joined in hybrid_recommend().
"""
from decimal import Decimal, ROUND_HALF_UP

import numpy as np

from config import COST, KEYS, TOL, WEIGHTS
from rules import rule_filter


def r3(x):
    """Round half-up to 3 decimals (0.8375 -> 0.838, as written in the paper)."""
    return float(Decimal(str(round(float(x), 10))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def normalize(X, cost=COST):
    """Ratio normalization: min/x for cost criteria (Eq. 2), x/max for the benefit
    criterion (Eq. 3). All values must be positive."""
    X = np.asarray(X, dtype=float)
    assert (X > 0).all(), "ratio normalization requires positive values"
    return np.where(cost, X.min(axis=0) / X, X / X.max(axis=0))


def score(X, w=WEIGHTS, cost=COST):
    """Weighted score S_i = sum_j w_j * r_ij (Eq. 4 / Eq. 8)."""
    w = np.asarray(w, dtype=float)
    assert abs(w.sum() - 1) < TOL, "weights must sum to 1"
    return normalize(X, cost) @ w


def rank(s):
    """Rank 1 = highest score."""
    return (-np.asarray(s)).argsort().argsort() + 1


def decision_matrix(modes, keys=KEYS):
    """Build X (rows = modes; columns follow `keys`: travel time, fare, traffic, waiting time)."""
    for m in modes:
        missing = [k for k in keys if m[k] is None]
        if missing:
            raise ValueError(f"'{m['name']}' reached the scoring stage but has no value for {missing}")
    return np.array([[m[k] for k in keys] for m in modes], dtype=float)


def hybrid_recommend(commuter, modes, w=WEIGHTS, keys=KEYS, cost=COST):
    """Full pipeline: rules first, then WSM on the feasible modes only."""
    stage1 = rule_filter(commuter, modes)
    feasible = stage1["feasible"]
    if not feasible:
        return {**stage1, "X": None, "R": None, "S": None, "ranks": None, "best": None}
    X = decision_matrix(feasible, keys)
    R = normalize(X, cost)
    w = np.asarray(w, dtype=float)
    assert abs(w.sum() - 1) < TOL, "weights must sum to 1"
    S = R @ w
    return {**stage1, "X": X, "R": R, "S": S, "ranks": rank(S),
            "best": feasible[int(np.argmax(S))]["name"]}
