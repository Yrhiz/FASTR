# FASTR
FASTR: A Decision Support System for Commuter Route Selection


Hybrid system: **rule-based forward chaining** (hard constraints) + **Weighted Scoring Model** (MCDM ranking) + **explanation facility**.
Python 3.9+, `numpy`, `matplotlib`.

## Run

```bash
pip install -r requirements.txt
python -m unittest -v     # 19 tests
python main.py            # prints results, writes ./results/*.png and *.csv
```

## Files

| File | Purpose |
|---|---|
| `fastr.py` | Core: rules, forward chaining, normalization, WSM, explanation, sensitivity, bisection, Monte Carlo |
| `visualize.py` | Figures (matplotlib) |
| `main.py` | Reproduces the paper's example and produces all tables and figures |
| `test_fastr.py` | Unit tests (paper values, edge cases, numerical checks) |

## (a) Model

- Criteria: Time (C1, cost), Fare (C2, cost), Traffic (C3, cost), Availability (C4, benefit).
- Stage 1, forward chaining: a rule fires when `Premises(R) ⊆ F` and adds its conclusion to `F` (Eq. 1). Example rule: `HasBudgetLimit ∧ ExceedsBudget(a) → Infeasible(a)`.
- Stage 2, normalization: `r_ij = min_i x_ij / x_ij` (cost), `r_ij = x_ij / max_i x_ij` (benefit).
- Score: `S_i = Σ_j w_j r_ij`, `Σ w_j = 1`. Highest score wins.
- Excluded modes are **removed**, not given a low score.

## (b) Implementation notes

Numerical parameters used:

| Component | Parameter | Value |
|---|---|---|
| Forward chaining | Iteration count | passes until no new fact; at most `#rules + 1` (guarded). Demo: 2 passes |
| Weight validation | Tolerance | `|Σw − 1| ≤ 1e-9` |
| Weight sweep | Step size | `0.01` (101 points per criterion) |
| Bisection (tie weight) | Tolerance / max iterations | `1e-8` / `100`; needs `⌈log2(1/1e-8)⌉ = 27` iterations |
| Monte Carlo | Sample size / seed | `N = 10000` / `42`; standard error `√(p(1−p)/N)` |
| Ranking ties | Tolerance | `1e-12` |

Error estimation:

1. **Floating-point error**: vectorised NumPy scores vs. an independent pure-Python loop version, max difference ≈ `1.1e-16`.
2. **Agreement with the paper**: code vs. hand-computed 0.8375 and 0.9125, max difference ≈ `1.1e-16`.
3. **Rounding error**: reporting 3 decimals gives at most `5e-4`.
4. **Bisection error**: compared to the closed-form root (scores are linear in the weight), error ≈ `4e-10`, below the tolerance.
5. **Sampling error**: Monte Carlo standard error ≈ 0.43%.

## (c) Results (illustrative data, as in the paper)

| Alternative | Time | Fare | Traffic | Avail. | Score | Rank |
|---|---|---|---|---|---|---|
| Shared tricycle | 1.000 | 0.650 | 1.000 | 1.000 | 0.9125 | 1 |
| Jeepney | 0.800 | 1.000 | 0.750 | 0.800 | 0.8375 | 2 |

Special-trip tricycle (PHP 80 > PHP 50) is excluded by rule R1.

Figures in `results/`: `fig1_scores.png`, `fig2_contributions.png`, `fig3_sensitivity.png`, `fig4_bisection.png`, `fig5_monte_carlo.png`. Tables: `table3`, `table5`, `table6`, `table7`, `table8` (CSV).

## (d) Discussion points

- **Accuracy**: arithmetic agrees with the hand calculation to machine precision.
- **Stability**: the shared tricycle stays first unless the fare weight exceeds ≈ 0.382 (exactly 13/34). It also wins about 76% of random weight vectors.
- **Cost**: filtering is O(passes × rules); WSM is O(m·n). Negligible at this scale.
- **Limitations**: illustrative inputs, assumed weights, ratio normalization is sensitive to the best value in the feasible set, no weather, safety, or real-time data. The special-trip tricycle's time, traffic, and availability values are **assumed** (not in the paper); they only matter in Scenario B.
