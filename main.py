python main.py

Steps: A rule-based filtering -> B weighted scoring -> C explanations ->
       D budget scenarios -> E weight sensitivity -> F computational cost -> G figures
"""
import numpy as np
import pandas as pd

import plots
from analysis import budget_scenarios, critical_weight, runtime_test, sensitivity_table
from config import COMMUTER, CRITERIA, RESULTS_DIR, WEIGHTS, load_modes
from explain import explain_exclusion, explain_ranking
from rules import rule_filter
from wsm import hybrid_recommend, r3


def section(title):
    print("\n" + "=" * 74 + f"\n{title}\n" + "=" * 74)


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    modes = load_modes()

    # ---- A. Stage 1: rule-based filtering ---------------------------------
    section("A. Stage 1 - Rule-based filtering (forward chaining)")
    res = hybrid_recommend(COMMUTER, modes)
    print(f"Commuter: student = {COMMUTER['student']}, budget = PHP {COMMUTER['budget']}")
    print(f"Rule base: {res['n_rules']} rules | forward-chaining passes until fixed point: {res['passes']}"
          f" | facts derived: {len(res['trace'])}\n")
    filt = pd.DataFrame([{"Alternative": m["name"], "Fare (PHP)": m["fare"], "Budget (PHP)": COMMUTER["budget"],
                          "Decision": "Excluded" if m in res["excluded"] else "Feasible"} for m in modes])
    print(filt.to_string(index=False))
    filt.to_csv(RESULTS_DIR / "table_filtering.csv", index=False)
    pd.DataFrame(res["trace"]).to_csv(RESULTS_DIR / "table_proof_trace.csv", index=False)

    # ---- B. Stage 2: weighted scoring --------------------------------------
    section("B. Stage 2 - Weighted scoring of the feasible alternatives")
    feasible, X, R, S = res["feasible"], res["X"], res["R"], res["S"]
    names = [m["name"] for m in feasible]
    print("Raw data (Table 4):")
    print(pd.DataFrame(X, index=names, columns=CRITERIA).to_string())
    table = pd.DataFrame(np.vectorize(r3)(R), index=names, columns=CRITERIA)
    print("\nNormalized values (Table 5):")
    print(table.to_string(float_format=lambda v: f"{v:.3f}"))
    table["Score"] = [r3(s) for s in S]
    table["Rank"] = res["ranks"]
    print("\nScores and ranking (Table 6), weights", WEIGHTS.tolist(), ":")
    print(table.to_string(float_format=lambda v: f"{v:.3f}"))
    table.to_csv(RESULTS_DIR / "table_scores.csv")
    print(f"\nScore difference: {r3(S.max())} - {r3(S.min())} = {r3(S.max() - S.min()):.3f}")

    # ---- C. Explanation facility -------------------------------------------
    section("C. Explanation facility (proof traces)")
    for m in res["excluded"]:
        print(explain_exclusion(m["name"], res))
        print()
    print(explain_ranking(res))

    # ---- D. Budget scenarios -------------------------------------------------
    section("D. Effect of the budget rule: feasible set vs. budget")
    budget_df = budget_scenarios(modes, [10, 13, 15, 20, 50, 80, 100])
    print(budget_df.to_string(index=False))
    budget_df.to_csv(RESULTS_DIR / "table_budget_scenarios.csv", index=False)
    non_student = rule_filter({"student": False, "budget": 50}, modes)["feasible"]
    print("\nNon-student commuter (budget rule not applicable):", [m["name"] for m in non_student])

    # ---- E. Weight sensitivity ------------------------------------------------
    section("E. Sensitivity of the ranking to the weights")
    top, second = int(np.argmax(S)), int(np.argsort(S)[-2])      # best and runner-up
    sens = sensitivity_table(X, names, top, second)
    print(sens.to_string(index=False))
    print(f"\nRuns where the ranking changed: {sens['Ranking changed?'].sum()} / {len(sens)}")
    sens.to_csv(RESULTS_DIR / "table_sensitivity.csv", index=False)

    print(f"\nBreak-even weights ({names[second]} ties with {names[top]}; other weights rescaled):")
    rows = []
    for j, c in enumerate(CRITERIA):
        w_star, its, exact = critical_weight(X, WEIGHTS, j, top, second)
        if w_star is None:
            msg = f"none in [0, 1]  ({names[top]} stays first for every value of this weight)"
        else:
            msg = (f"w* = {w_star:.4f} (base {WEIGHTS[j]:.2f}) | bisection iterations = {its} | "
                   f"|bisection - exact| = {abs(w_star - exact):.1e}")
        print(f"  {c:<13}: {msg}")
        rows.append({"Criterion": c, "Base weight": WEIGHTS[j],
                     "Break-even weight": None if w_star is None else round(w_star, 4)})
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "table_break_even.csv", index=False)

    # ---- F. Computational cost -------------------------------------------------
    section("F. Computational cost (rule filtering + WSM) vs. number of modes")
    sizes, t_rules, t_wsm = runtime_test()
    for n, tr, tw in zip(sizes, t_rules, t_wsm):
        print(f"  m = {n:>7,d}   rule filtering = {tr*1000:10.3f} ms   WSM = {tw*1000:9.3f} ms")
    slope = np.polyfit(np.log(sizes[2:]), np.log(np.array(t_rules[2:]) + np.array(t_wsm[2:]), 1))[0]
    print(f"Empirical log-log slope (m >= 1000): {slope:.2f}  (1 = linear growth, 2 = quadratic growth)")

    # ---- G. Figures ------------------------------------------------------------
    plots.fig_rule_filtering(res, modes, RESULTS_DIR)
    plots.fig_normalized(res, RESULTS_DIR)
    plots.fig_scores(res, RESULTS_DIR)
    plots.fig_sensitivity(res, RESULTS_DIR)
    plots.fig_break_even(res, RESULTS_DIR, top, second)
    plots.fig_budget(modes, RESULTS_DIR)
    plots.fig_runtime(sizes, t_rules, t_wsm, RESULTS_DIR)
    print(f"\nDone. Tables and figures saved in {RESULTS_DIR}")


if __name__ == "__main__":
    main()
