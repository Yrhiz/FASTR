"""Unit tests. Run with:  python -m unittest -v"""

import unittest

import numpy as np

import fastr as F

WEIGHTS = [0.35, 0.25, 0.25, 0.15]
JEEP = F.Mode("Jeepney", 30, 13, 4, 4)
SHARED = F.Mode("Shared tricycle", 24, 20, 3, 5)
SPECIAL = F.Mode("Special-trip tricycle", 15, 80, 2, 3)


class TestFiltering(unittest.TestCase):
    def test_budget_rule_excludes_special_trip(self):
        res = F.rule_filter(F.Commuter(budget=50), [JEEP, SHARED, SPECIAL])
        self.assertEqual([m.name for m in res.feasible], ["Jeepney", "Shared tricycle"])
        self.assertIn("Special-trip tricycle", res.excluded)

    def test_fare_equal_to_budget_is_feasible(self):
        res = F.rule_filter(F.Commuter(budget=80), [SPECIAL])
        self.assertEqual(len(res.feasible), 1)          # rule uses strict '>'

    def test_no_budget_means_no_budget_rule(self):
        res = F.rule_filter(F.Commuter(budget=None), [JEEP, SPECIAL])
        self.assertEqual(len(res.feasible), 2)

    def test_out_of_service_and_time_limit(self):
        down = F.Mode("Down", 10, 10, 1, 1, in_service=False)
        res = F.rule_filter(F.Commuter(budget=50, max_time=25), [JEEP, SHARED, down])
        self.assertEqual([m.name for m in res.feasible], ["Shared tricycle"])

    def test_forward_chaining_terminates_and_counts_passes(self):
        res = F.rule_filter(F.Commuter(budget=50), [JEEP, SHARED, SPECIAL])
        self.assertEqual(res.passes, 2)    # pass 1 fires a rule, pass 2 finds nothing new


class TestWSM(unittest.TestCase):
    def setUp(self):
        self.rec = F.recommend([JEEP, SHARED, SPECIAL], F.Commuter(budget=50), WEIGHTS)

    def test_matches_paper_normalized_values(self):
        expected = np.array([[0.800, 1.000, 0.750, 0.800],
                             [1.000, 0.650, 1.000, 1.000]])
        np.testing.assert_allclose(self.rec.normalized, expected, atol=1e-12)

    def test_matches_paper_scores(self):
        np.testing.assert_allclose(self.rec.scores, [0.8375, 0.9125], atol=1e-12)

    def test_best_is_shared_tricycle(self):
        self.assertEqual(self.rec.best.name, "Shared tricycle")

    def test_normalized_values_in_unit_interval(self):
        self.assertTrue(np.all(self.rec.normalized > 0) and np.all(self.rec.normalized <= 1))

    def test_vectorised_equals_pure_python(self):
        pure = F.scores_pure_python(self.rec.raw.tolist(), WEIGHTS)
        np.testing.assert_allclose(self.rec.scores, pure, atol=1e-14)

    def test_invalid_weights_rejected(self):
        for bad in ([0.5, 0.5, 0.5, 0.5], [-0.1, 0.5, 0.3, 0.3], [0.5, 0.5]):
            with self.assertRaises(ValueError):
                F.validate_weights(bad)

    def test_nonpositive_data_rejected(self):
        with self.assertRaises(ValueError):
            F.normalize(np.array([[0, 1, 1, 1], [1, 1, 1, 1]], dtype=float))

    def test_empty_feasible_set(self):
        rec = F.recommend([SPECIAL], F.Commuter(budget=10), WEIGHTS)
        self.assertIsNone(rec.best)

    def test_single_mode_scores_one(self):
        rec = F.recommend([JEEP], F.Commuter(budget=50), WEIGHTS)
        self.assertAlmostEqual(rec.scores[0], 1.0, places=12)


class TestSensitivity(unittest.TestCase):
    def setUp(self):
        rec = F.recommend([JEEP, SHARED], F.Commuter(budget=50), WEIGHTS)
        self.R = rec.normalized

    def test_reweight_sums_to_one(self):
        for j in range(4):
            for t in (0.0, 0.3, 1.0):
                self.assertAlmostEqual(F.reweight(WEIGHTS, j, t).sum(), 1.0, places=12)

    def test_reweight_at_original_value_is_identity(self):
        np.testing.assert_allclose(F.reweight(WEIGHTS, 1, WEIGHTS[1]), WEIGHTS, atol=1e-12)

    def test_bisection_matches_exact_and_scores_tie(self):
        # Fare weight: jeepney (index 0) beats shared (index 1) when fare matters most
        t, iters, _ = F.bisect_crossover(self.R, WEIGHTS, 1, a=1, b=0, tol=1e-10)
        exact = F.exact_crossover(self.R, WEIGHTS, 1, 1, 0)
        self.assertAlmostEqual(t, exact, places=9)
        s = self.R @ F.reweight(WEIGHTS, 1, t)
        self.assertAlmostEqual(s[0], s[1], places=8)
        self.assertLessEqual(iters, 34)

    def test_no_crossover_returns_none(self):
        t, iters, _ = F.bisect_crossover(self.R, WEIGHTS, 0, a=1, b=0)   # shared always wins on time
        self.assertIsNone(t)

    def test_monte_carlo_rates_sum_to_one(self):
        p, _ = F.monte_carlo_win_rates(self.R, n=2000, seed=1)
        self.assertAlmostEqual(p.sum(), 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
