"""
Run the FASTR demonstration used in the paper and produce all tables and figures.

    python main.py

Outputs go to ./results/ (PNG figures + CSV tables) and a summary prints to the console.
All numbers are ILLUSTRATIVE (as stated in the paper), not real-time transport data.
"""

import csv
import math
import os

import numpy as np

import fastr as F
import visualize as V

OUT = "results"
WEIGHTS = [0.35, 0.25, 0.25, 0.15]       # Time, Fare, Traffic, Availability  (paper, Eq. 7)

# Paper's scenario: BulSU -> Barasoain Church, budget PHP 50.
# Time/traffic/availability of the special-trip tricycle are NOT given in the paper;
# the values below are assumed (they never affect Scenario A because it is excluded).
MODES = [
    F.Mode("Jeepney",                30, 13, 4, 4),
    F.Mode("Shared tricycle",        24, 20, 3, 5),
    F.Mode("Special-trip tricycle",  15, 80, 2, 3),
]


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    V.ensure_dir(OUT)

    # ------------------------------------------------------------------ #
    # Scenario A (paper): budget = PHP 50
    # ------------------------------------------------------------------ #
    commuter = F.Commuter(budget=50, is_student=True)
    rec = F.recommend(MODES, commuter, WEIGHTS)

    print(F.explain(rec, commuter, MODES))
    print()

    # Tables 3, 5, 6
    write_csv(f"{OUT}/table3_filtering.csv", ["Alternative", "Fare", "Budget", "Decision"],
              [[m.name, m.fare, commuter.budget,
                "Excluded" if m.name in rec.filtering.excluded else "Feasible"] for m in MODES])
    write_csv(f"{OUT}/table5_normalized.csv", ["Alternative", *F.CRITERIA],
              [[m.name, *np.round(r, 4)] for m, r in zip(rec.filtering.feasible, rec.normalized)])
    write_csv(f"{OUT}/table6_scores.csv", ["Alternative", *F.CRITERIA, "Score", "Rank"],
              [[rec.filtering.feasible[i].name, *np.round(rec.normalized[i], 4),
                round(rec.scores[i], 4), pos + 1] for pos, i in enumerate(rec.ranking)])

    V.plot_scores(rec, f"{OUT}/fig1_scores.png")
    V.plot_contributions(rec, f"{OUT}/fig2_contributions.png")

    # ------------------------------------------------------------------ #
    # Error estimation 1: floating-point check against an independent loop version
    # ------------------------------------------------------------------ #
    pure = F.scores_pure_python(rec.raw.tolist(), WEIGHTS)
    fp_err = np.max(np.abs(np.array(pure) - rec.scores))
    paper = {"Jeepney": 0.8375, "Shared tricycle": 0.9125}   # hand computation in paper
    paper_err = max(abs(rec.scores[i] - paper[m.name])
                    for i, m in enumerate(rec.filtering.feasible))
    print("=== ERROR ESTIMATION ===")
    print(f"Max |NumPy - pure-Python| score difference : {fp_err:.2e}   (floating-point error)")
    print(f"Max |code - paper's hand calculation|      : {paper_err:.2e}")
    print(f"Rounding error when reporting 3 decimals   : <= {0.5e-3:.1e}")

    # ------------------------------------------------------------------ #
    # Sensitivity analysis: sweep each weight, step size 0.01 (101 points)
    # ------------------------------------------------------------------ #
    STEP, TOL, MAXIT = 0.01, 1e-8, 100
    R = rec.normalized
    names = [m.name for m in rec.filtering.feasible]
    a, b = rec.ranking[0], rec.ranking[1]            # leader vs runner-up
    sweeps, crossovers, cross_rows = {}, {}, []
    best_hist = None
    print(f"\n=== SENSITIVITY (step = {STEP}, bisection tol = {TOL:g}) ===")
    for j, crit in enumerate(F.CRITERIA):
        ts, S = F.sweep_weight(R, WEIGHTS, j, step=STEP)
        sweeps[crit] = (ts, S)
        t_bis, iters, hist = F.bisect_crossover(R, WEIGHTS, j, a, b, tol=TOL, max_iter=MAXIT)
        t_ex = F.exact_crossover(R, WEIGHTS, j, a, b)
        crossovers[crit] = t_bis
        if t_bis is None:
            print(f"  {crit:<13}: no ranking change for any weight in [0,1]")
            cross_rows.append([crit, "none", "", "", ""])
        else:
            err = abs(t_bis - t_ex)
            print(f"  {crit:<13}: tie at w = {t_bis:.6f} after {iters} iterations "
                  f"(exact {t_ex:.6f}, error {err:.1e})")
            cross_rows.append([crit, f"{t_bis:.8f}", iters, f"{t_ex:.8f}", f"{err:.2e}"])
            if best_hist is None:
                best_hist = (hist, t_ex)
    print(f"  Theory: bisection needs ceil(log2(1/tol)) = {math.ceil(math.log2(1 / TOL))} iterations.")
    write_csv(f"{OUT}/table7_crossovers.csv",
              ["Criterion varied", "Tie weight (bisection)", "Iterations", "Exact", "Abs error"],
              cross_rows)
    V.plot_sensitivity(sweeps, names, crossovers, f"{OUT}/fig3_sensitivity.png")
    if best_hist:
        V.plot_bisection(best_hist[0], best_hist[1], f"{OUT}/fig4_bisection.png")

    # ------------------------------------------------------------------ #
    # Error estimation 2: Monte Carlo robustness to random weights
    # ------------------------------------------------------------------ #
    N = 10000
    p, se = F.monte_carlo_win_rates(R, n=N, seed=42)
    print(f"\n=== MONTE CARLO (N = {N}, seed = 42) ===")
    for n_, pi, si in zip(names, p, se):
        print(f"  {n_:<18}: ranked 1st in {pi:.1%} of draws  (SE {si:.2%}, 95% CI ±{1.96 * si:.2%})")
    V.plot_monte_carlo(names, p, se, f"{OUT}/fig5_monte_carlo.png")
    write_csv(f"{OUT}/table8_monte_carlo.csv", ["Alternative", "Win rate", "Std error"],
              [[n_, round(pi, 4), round(si, 4)] for n_, pi, si in zip(names, p, se)])

    # ------------------------------------------------------------------ #
    # Scenario B: larger budget, all three modes feasible (shows the filter's role)
    # ------------------------------------------------------------------ #
    print("\n=== SCENARIO B: budget = PHP 100 (no exclusion) ===")
    commuter_b = F.Commuter(budget=100)
    rec_b = F.recommend(MODES, commuter_b, WEIGHTS)
    for pos, i in enumerate(rec_b.ranking, 1):
        print(f"  #{pos} {rec_b.filtering.feasible[i].name:<22} S = {rec_b.scores[i]:.4f}")

    # Scenario C: a mode out of service
    print("\n=== SCENARIO C: shared tricycle not in service ===")
    modes_c = [F.Mode("Jeepney", 30, 13, 4, 4),
               F.Mode("Shared tricycle", 24, 20, 3, 5, in_service=False),
               F.Mode("Special-trip tricycle", 15, 80, 2, 3)]
    rec_c = F.recommend(modes_c, F.Commuter(budget=50), WEIGHTS)
    print(F.explain(rec_c, F.Commuter(budget=50), modes_c))

    print(f"\nFiles written to ./{OUT}/")


if __name__ == "__main__":
    main()
