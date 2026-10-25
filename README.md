# FASTR
FASTR: A Smart Commuter Recommendation System

FASTR is a hybrid decision support system for commuters in Malolos, Bulacan. It works in two stages:

1. **Rule-based filtering (Expert System).** Production rules and forward chaining remove alternatives that break a hard constraint, such as a student's budget (Eqs. 1, 5 and 6 of the paper).
2. **Weighted Scoring Model (MCDM).** The remaining alternatives are scored on travel time, fare, traffic and availability using ratio normalization and a weighted sum (Eqs. 2-4).

An explanation facility shows why an alternative was excluded or ranked first.

## Repository structure

| File / folder | Purpose |
|---|---|
| `main.py` | Runs the whole program and saves all results |
| `config.py` | Criteria, weights, commuter profile and data loading |
| `rules.py` | Stage 1: facts, rules, forward chaining, filtering |
| `wsm.py` | Stage 2: normalization, weighted score, ranking, full pipeline |
| `explain.py` | Explanation facility (proof traces) |
| `analysis.py` | Budget scenarios, weight sensitivity, break-even weights, runtime test |
| `plots.py` | All figures |
| `modes.csv` | Input data (illustrative values from the paper) |
| `results/` | figures (PNG) |
| `test_fastr.py` | Checks that the code reproduces the paper's Tables 5 and 6 |

## How to run

Requires Python 3.9 or newer.

```bash
git clone <repository-url>
cd <repository-folder>
pip install -r requirements.txt
python main.py
```

The program prints a report and writes the tables and figures to `results/`.
To check the results against the paper:

```bash
python test_fastr.py
```

## Input data

`modes.csv` has one row per transportation alternative:

| Column | Meaning |
|---|---|
| `name` | Alternative name |
| `time` | Estimated travel time (minutes) |
| `fare` | Estimated fare (PHP) |
| `traffic` | Congestion rating, 1 (light) to 5 (heavy) |
| `availability` | Ease of getting the mode, 1 (rare) to 5 (frequent) |
| `available` | `True` if the mode is operating |

The values are **illustrative** (see Section 4 of the paper) and are not real-time observations.
The special-trip tricycle has only a fare because the budget rule removes it before scoring. The program stops with a clear message if a mode with missing values reaches the scoring stage.

To use other data, edit `data/modes.csv`. The student's budget and the criterion weights are set in `config.py`.

## Output files (`results/`)

| File | Content |
|---|---|
| `fig1_rule_filtering.png` | Fares against the budget |
| `fig2_normalized_values.png` | Normalized criterion values |
| `fig3_weighted_scores.png` | Weighted scores by criterion |
| `fig4_sensitivity.png` | Scores while each weight varies by ±20 % |
| `fig5_fare_weight_break_even.png` | Fare weight at which the jeepney overtakes the shared tricycle |
| `fig6_budget_vs_feasible.png` | Number of feasible alternatives against budget |
| `fig7_computational_cost.png` | Running time against number of alternatives |

## Main results (illustrative example)

- The special-trip tricycle (PHP 80) exceeds the student's PHP 50 budget and is excluded by rule `R1`.
- Jeepney: score 0.838 (rank 2). Shared tricycle: score 0.913 (rank 1).
- The ranking did not change in any of the 16 weight-sensitivity runs. The jeepney overtakes only if the fare weight rises above about 0.382 (currently 0.25).

