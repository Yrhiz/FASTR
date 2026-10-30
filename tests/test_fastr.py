"""
Checks of the FASTR method itself (rules, normalization, scoring, break-even).
All expected values are worked out by hand from a small decision matrix, not copied from results/.
Run from the repository folder:   python tests/test_fastr.py     (or: pytest)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from analysis import critical_weight, vary_weight
from config import COST, KEYS, WEIGHTS
from rules import build_facts, build_rules, forward_chain, rule_filter
from wsm import hybrid_recommend, normalize, r3

# A (cheap, slow), B (balanced), C (fast, expensive). Keys follow config.KEYS: time, fare, traffic, wait.
MODES = [
    {"name": "A", "time": 20.0, "fare": 10.0, "traffic": 2.0, "wait": 8.0, "available": True},
    {"name": "B", "time": 10.0, "fare": 20.0, "traffic": 1.0, "wait": 4.0, "available": True},
    {"name": "C", "time": 5.0, "fare": 80.0, "traffic": 1.0, "wait": 2.0, "available": True},
]


def test_weights_sum_to_one():
    assert abs(WEIGHTS.sum() - 1) < 1e-9 and len(WEIGHTS) == len(KEYS) == len(COST)


def test_budget_rule_excludes_expensive_mode():
    res = rule_filter({"budget": 50}, MODES)
    assert [m["name"] for m in res["excluded"]] == ["C"]
    assert [m["name"] for m in res["feasible"]] == ["A", "B"]


def test_no_budget_limit_keeps_all_modes():
    assert len(rule_filter({"budget": None}, MODES)["feasible"]) == 3


def test_forward_chaining_reaches_fixed_point():
    facts0, _ = build_facts({"budget": 50}, MODES)
    facts, trace, passes = forward_chain(facts0, build_rules(MODES))
    assert "Infeasible(C)" in facts and passes == 2 and len(trace) == 1


def test_wait_limit_rule():
    res = rule_filter({"budget": None, "max_wait": 5}, MODES)
    assert [m["name"] for m in res["feasible"]] == ["B", "C"]


def test_normalization_of_cost_criteria():
    # every criterion is a cost criterion: r = min / x
    X = np.array([[20, 10, 2, 8], [10, 20, 1, 4]], dtype=float)
    assert np.allclose(normalize(X, COST), [[0.5, 1.0, 0.5, 0.5], [1.0, 0.5, 1.0, 1.0]])


def test_scores_by_hand():
    res = hybrid_recommend({"budget": 50}, MODES, WEIGHTS, KEYS, COST)
    # A: .35*.5 + .25*1 + .25*.5 + .15*.5 = 0.625 ; B: .35*1 + .25*.5 + .25*1 + .15*1 = 0.875
    assert np.allclose(res["S"], [0.625, 0.875])
    assert res["best"] == "B" and list(res["ranks"]) == [2, 1]


def test_rounding_half_up():
    assert r3(0.8375) == 0.838 and r3(0.9125) == 0.913


def test_vary_weight_keeps_sum_one():
    assert abs(vary_weight(WEIGHTS, 1, 0.2).sum() - 1) < 1e-9


def test_break_even_is_a_tie():
    from analysis import set_weight
    from wsm import score
    res = hybrid_recommend({"budget": 50}, MODES, WEIGHTS, KEYS, COST)
    w_star, _, exact = critical_weight(res["X"], WEIGHTS, 1, 1, 0, COST)   # fare weight, B vs A
    assert w_star is None or abs(w_star - exact) < 1e-8
    if w_star is not None:
        s = score(res["X"], set_weight(WEIGHTS, 1, w_star), COST)
        assert abs(s[0] - s[1]) < 1e-6


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"{len(tests)} tests passed")
