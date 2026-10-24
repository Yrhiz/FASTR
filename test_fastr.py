"""
Simple checks that the code reproduces the values in the paper.
Run from the repository folder:   python tests/test_fastr.py     (or: pytest)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from analysis import critical_weight, vary_weight
from config import COMMUTER, WEIGHTS, load_modes
from rules import build_facts, build_rules, forward_chain, rule_filter
from wsm import hybrid_recommend, normalize, r3


def test_weights_sum_to_one():
    assert abs(WEIGHTS.sum() - 1) < 1e-9


def test_budget_rule_excludes_special_trip():
    res = rule_filter(COMMUTER, load_modes())
    assert [m["name"] for m in res["excluded"]] == ["Special-trip tricycle"]
    assert [m["name"] for m in res["feasible"]] == ["Jeepney", "Shared tricycle"]


def test_non_student_keeps_all_modes():
    res = rule_filter({"student": False, "budget": 50}, load_modes())
    assert len(res["feasible"]) == 3


def test_forward_chaining_reaches_fixed_point():
    modes = load_modes()
    facts0, _ = build_facts(COMMUTER, modes)
    facts, trace, passes = forward_chain(facts0, build_rules(modes))
    assert "Infeasible(Special-trip tricycle)" in facts and passes == 2 and len(trace) == 1


def test_normalized_values_match_table_5():
    res = hybrid_recommend(COMMUTER, load_modes())
    expected = np.array([[0.800, 1.000, 0.750, 0.800], [1.000, 0.650, 1.000, 1.000]])
    assert np.allclose(res["R"], expected)


def test_scores_match_table_6():
    res = hybrid_recommend(COMMUTER, load_modes())
    assert np.allclose(res["S"], [0.8375, 0.9125])
    assert [r3(s) for s in res["S"]] == [0.838, 0.913]
    assert res["best"] == "Shared tricycle"


def test_vary_weight_keeps_sum_one():
    assert abs(vary_weight(WEIGHTS, 1, 0.2).sum() - 1) < 1e-9


def test_fare_break_even():
    res = hybrid_recommend(COMMUTER, load_modes())
    w_star, _, exact = critical_weight(res["X"], WEIGHTS, 1, 1, 0)
    assert abs(w_star - exact) < 1e-8 and abs(w_star - 0.3824) < 1e-3


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"{len(tests)} tests passed")
