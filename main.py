"""
main.py - Runs the whole FASTR pipeline for the report trip and writes tables and figures to ./results/

    python main.py

The trip, hour, day type, budget and weights are set in config.py (REPORT_TRIP). The numbers come from
service.evaluate_trip(), the same function the web app uses, so results/ and the app agree.

Steps: A rule-based filtering -> B weighted scoring -> C explanations ->
       D budget scenarios -> E weight sensitivity -> F computational cost -> G figures
"""
import numpy as np
import pandas as pd

import plots
from analysis import budget_scenarios, critical_weight, runtime_test, sensitivity_table
from config import COST, CRITERIA, KEYS, REPORT_ONLINE, REPORT_TRIP, RESULTS_DIR
from explain import explain_exclusion, explain_ranking
from rules import rule_filter
from service import evaluate_trip, options_rows
from wsm import r3


def section(title):
    print("\n" + "=" * 74 + f"\n{title}\n" + "=" * 74)


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    t = REPORT_TRIP
    ctx = evaluate_trip(t["origin"], t["destination"], t["hour"], t["budget"], t["max_wait"],
                        None, online=REPORT_ONLINE, season=t["season"])
    modes, res, W, budget = ctx["modes"], ctx["res"], ctx["weights"], t["budget"]
    if res["best"] is None:
        raise SystemExit("The report trip has no feasible alternative; change REPORT_TRIP in config.py.")

    print(f"Trip: {ctx['origin']['name']} -> {ctx['destination']['name']} | {t['hour']}:00 | day type: {ctx['season']}")
    print(f"Distance: {ctx['distance']:.2f} km ({ctx['distance_source']}) | congestion level "
          f"{ctx['trip_traffic']['level']:g}/5 ({ctx['trip_traffic']['basis']})")

    # ---- A. Stage 1: rule-based filtering ---------------------------------
    section("A. Stage 1 - Rule-based filtering (forward chaining)")
    print(f"Commuter: budget = PHP {budget:g}" + ("" if t["max_wait"] is None else f", max waiting = {t['max_wait']:g} min"))
    print(f"Rule base: {res['n_rules']} rules | forward-chaining passes until fixed point: {res['passes']}"
          f" | facts derived: {len(res['trace'])}\n")
    filt = pd.DataFrame([{"Alternative": m["name"], "Fare (PHP)": int(m["fare"]),
                          "Budget (PHP)": "none" if budget is None else budget,
                          "Decision": "Excluded" if m in res["excluded"] else "Feasible"} for m in modes])
    print(filt.to_string(index=False))
    filt.to_csv(RESULTS_DIR / "table_filtering.csv", index=False)
    pd.DataFrame(res["trace"]).to_csv(RESULTS_DIR / "table_proof_trace.csv", index=False)

    # ---- B. Stage 2: weighted scoring --------------------------------------
    section("B. Stage 2 - Weighted scoring of the feasible alternatives")
    feasible, X, R, S = res["feasible"], res["X"], res["R"], res["S"]
    names = [m["name"] for m in feasible]
    print("Raw data of the feasible alternatives:")
    print(pd.DataFrame(X, index=names, columns=CRITERIA).round(2).to_string())
    table = pd.DataFrame(np.vectorize(r3)(R), index=names, columns=CRITERIA)
    print("\nNormalized values (all criteria are cost criteria: min / x):")
    print(table.to_string(float_format=lambda v: f"{v:.3f}"))
    table["Score"] = [r3(s) for s in S]
    table["Rank"] = res["ranks"]
    print("\nScores and ranking, weights", np.round(W, 3).tolist(), ":")
    print(table.to_string(float_format=lambda v: f"{v:.3f}"))
    table.to_csv(RESULTS_DIR / "table_scores.csv")
    order = np.argsort(-S)
    print(f"\nScore difference: {r3(S[order[0]])} - {r3(S[order[1]]) if len(S) > 1 else 0} = "
          f"{r3(S[order[0]] - (S[order[1]] if len(S) > 1 else 0)):.3f}")

    # the options table exactly as the web app shows it
    rows, _ = options_rows(modes, res)
    opts = pd.DataFrame([{"Option": r["name"], "Fare (PHP)": r["fare"], "Travel time (min)": r["time"],
                          "Waiting (min)": r["wait"], "Traffic (1-5)": r["traffic"],
                          "Status": "Excluded" if r["excluded"] else "Feasible",
                          "Score": r["score"], "Rank": r["rank"]} for r in rows])
    opts["Rank"] = opts["Rank"].astype("Int64")
    opts.to_csv(RESULTS_DIR / "table_trip_options.csv", index=False)
    print("\nAll options (same table as the web app):")
    print(opts.to_string(index=False))

    # ---- C. Explanation facility -------------------------------------------
    section("C. Explanation facility (proof traces)")
    for m in res["excluded"]:
        print(explain_exclusion(m["name"], res))
        print()
    print(explain_ranking(res, W))

    # ---- D. Budget scenarios -------------------------------------------------
    section("D. Effect of the budget rule: feasible set vs. budget")
    fares = sorted({int(m["fare"]) for m in modes})
    budgets = sorted({b for f in fares for b in (f - 1, f) if b >= 0} | {fares[-1] + 20})
    budget_df = budget_scenarios(modes, budgets, W, KEYS, COST)
    print(budget_df.to_string(index=False))
    budget_df.to_csv(RESULTS_DIR / "table_budget_scenarios.csv", index=False)
    no_limit = rule_filter({"budget": None}, modes)["feasible"]
    print("\nNo budget limit (budget rule not triggered):", [m["name"] for m in no_limit])

    # ---- E. Weight sensitivity ------------------------------------------------
    section("E. Sensitivity of the ranking to the weights")
    if len(feasible) < 2:
        print("Only one feasible alternative: no sensitivity analysis.")
        top = second = 0
    else:
        top, second = int(order[0]), int(order[1])               # best and runner-up
        sens = sensitivity_table(X, names, top, second, W, COST)
        print(sens.to_string(index=False))
        print(f"\nRuns where the ranking changed: {sens['Ranking changed?'].sum()} / {len(sens)}")
        sens.to_csv(RESULTS_DIR / "table_sensitivity.csv", index=False)

        print(f"\nBreak-even weights ({names[second]} ties with {names[top]}; other weights rescaled):")
        rows_be = []
        for j, c in enumerate(CRITERIA):
            w_star, its, exact = critical_weight(X, W, j, top, second, COST)
            if w_star is None:
                msg = f"none in [0, 1]  ({names[top]} stays first for every value of this weight)"
            else:
                msg = (f"w* = {w_star:.4f} (base {W[j]:.2f}) | bisection iterations = {its} | "
                       f"|bisection - exact| = {abs(w_star - exact):.1e}")
            print(f"  {c:<13}: {msg}")
            rows_be.append({"Criterion": c, "Base weight": round(float(W[j]), 4),
                            "Break-even weight": None if w_star is None else round(w_star, 4)})
        pd.DataFrame(rows_be).to_csv(RESULTS_DIR / "table_break_even.csv", index=False)

    # ---- F. Computational cost -------------------------------------------------
    section("F. Computational cost (rule filtering + WSM) vs. number of modes")
    sizes, t_rules, t_wsm = runtime_test()
    for n, tr, tw in zip(sizes, t_rules, t_wsm):
        print(f"  m = {n:>7,d}   rule filtering = {tr*1000:10.3f} ms   WSM = {tw*1000:9.3f} ms")
    slope = np.polyfit(np.log(sizes[2:]), np.log(np.array(t_rules[2:]) + np.array(t_wsm[2:])), 1)[0]
    print(f"Empirical log-log slope (m >= 1000): {slope:.2f}  (1 = linear growth, 2 = quadratic growth)")
    print("(Timings depend on the computer; every other number above is deterministic.)")

    # ---- G. Figures ------------------------------------------------------------
    plots.fig_rule_filtering(res, modes, budget, RESULTS_DIR)
    plots.fig_normalized(res, RESULTS_DIR)
    plots.fig_scores(res, RESULTS_DIR, W)
    if len(feasible) >= 2:
        plots.fig_sensitivity(res, RESULTS_DIR, W)
        plots.fig_break_even(res, RESULTS_DIR, top, second, W)
    plots.fig_budget(modes, budget, RESULTS_DIR)
    plots.fig_runtime(sizes, t_rules, t_wsm, RESULTS_DIR)
    print("\nDone. Tables and figures saved in results/")


if __name__ == "__main__":
    main()
