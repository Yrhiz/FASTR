"""
plots.py - Figures for the paper (saved as PNG files in the results folder).
"""
import matplotlib
matplotlib.use("Agg")                      # draw to files, no window needed
import matplotlib.pyplot as plt
import numpy as np

from analysis import critical_weight, set_weight, vary_weight
from config import COST, CRITERIA, WEIGHTS
from rules import rule_filter
from wsm import r3, score

plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
C_OK, C_BAD = "#66c2a5", "#d95f5f"          # feasible / excluded
PAL = plt.cm.Set2.colors


def fig_rule_filtering(res, modes, budget, out):
    """Fares against the budget; excluded modes in red."""
    names = [m["name"] for m in modes]
    fares = [m["fare"] for m in modes]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    colors = [C_BAD if m in res["excluded"] else C_OK for m in modes]
    bars = ax.bar(names, fares, color=colors, edgecolor="black", lw=0.6)
    if budget is not None:
        ax.axhline(budget, color="black", ls="--", lw=1.2)
        ax.text(-0.45, budget + 1, f"Budget = PHP {budget:g}", ha="left")
    for b, m in zip(bars, modes):
        label = "Excluded" if m in res["excluded"] else "Feasible"
        ax.text(b.get_x() + b.get_width() / 2, m["fare"] + 1.5, f"PHP {m['fare']:g}\n{label}",
                ha="center", fontsize=9)
    ax.set_ylim(0, max(fares + [budget or 0]) * 1.25)
    ax.set_ylabel("Fare (PHP)")
    ax.set_title("Stage 1: rule-based budget filtering")
    fig.tight_layout(); fig.savefig(out / "fig1_rule_filtering.png"); plt.close(fig)


def fig_normalized(res, out):
    """Heatmap of the normalized values r_ij."""
    names = [m["name"] for m in res["feasible"]]
    R = res["R"]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    im = ax.imshow(R, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(CRITERIA))); ax.set_xticklabels(CRITERIA)
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names)
    for i in range(R.shape[0]):
        for j in range(len(CRITERIA)):
            ax.text(j, i, f"{r3(R[i, j]):.3f}", ha="center", va="center",
                    color="white" if R[i, j] > 0.45 else "black")
    ax.set_title("Normalized criterion values $r_{ij}$ (1 = best)")
    ax.spines[:].set_visible(False)
    fig.colorbar(im, ax=ax, shrink=0.9)
    fig.tight_layout(); fig.savefig(out / "fig2_normalized_values.png"); plt.close(fig)


def fig_scores(res, out, w=WEIGHTS):
    """Weighted scores, stacked by criterion."""
    names = [m["name"] for m in res["feasible"]]
    R, S = res["R"], res["S"]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    contrib, left = R * w, np.zeros(len(names))
    for j, c in enumerate(CRITERIA):
        ax.barh(names, contrib[:, j], left=left, label=f"{c} (w = {w[j]:.2f})",
                color=PAL[j], edgecolor="black", lw=0.5)
        left += contrib[:, j]
    for i, s in enumerate(S):
        ax.text(s + 0.01, i, f"S = {r3(s):.3f}  (rank {res['ranks'][i]})", va="center")
    ax.set_xlim(0, 1.25)
    ax.invert_yaxis()
    ax.set_xlabel("Weighted score $S_i$ (stacked by criterion)")
    ax.set_title("Stage 2: weighted scores of the feasible alternatives")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(out / "fig3_weighted_scores.png"); plt.close(fig)


def fig_sensitivity(res, out, w=WEIGHTS):
    """Scores while each weight changes by -20 % ... +20 %."""
    names = [m["name"] for m in res["feasible"]]
    X = res["X"]
    fig, axs = plt.subplots(1, len(CRITERIA), figsize=(15, 3.6), sharey=True)
    grid = np.linspace(-0.20, 0.20, 9)
    for j, (ax, c) in enumerate(zip(axs, CRITERIA)):
        traj = np.array([score(X, vary_weight(w, j, p), COST) for p in grid])
        for i, n in enumerate(names):
            ax.plot(grid * 100, traj[:, i], marker="o", ms=3, color=PAL[i], label=n)
        ax.axvline(0, color="gray", ls=":", lw=1)
        ax.set_title(f"Vary $w_{j+1}$ ({c})")
        ax.set_xlabel("Change in weight (%)")
    axs[0].set_ylabel("Weighted score $S_i$")
    axs[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out / "fig4_sensitivity.png"); plt.close(fig)


def fig_break_even(res, out, a, b, w=WEIGHTS):
    """Scores as the fare weight goes from 0 to 1; marks where modes a and b tie."""
    names = [m["name"] for m in res["feasible"]]
    X = res["X"]
    v = np.linspace(0, 1, 201)
    curves = np.array([score(X, set_weight(w, 1, x), COST) for x in v])
    w_star, _, _ = critical_weight(X, w, 1, a, b, COST)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for i, n in enumerate(names):
        ax.plot(v, curves[:, i], color=PAL[i], lw=2, label=n)
    ax.axvline(w[1], color="gray", ls=":", lw=1)
    right = w_star is None or w[1] >= w_star            # put the two labels on opposite sides
    ax.text(w[1] + (0.01 if right else -0.01), 0.04, f"current\nweight = {w[1]:.2f}", fontsize=8, color="gray",
            ha="left" if right else "right", transform=ax.get_xaxis_transform())
    if w_star is not None:
        ax.axvline(w_star, color="black", ls="--", lw=1)
        ax.text(w_star + (-0.01 if right else 0.01), 0.04, f"break-even\n$w_2$ = {w_star:.3f}", fontsize=8,
                ha="right" if right else "left", transform=ax.get_xaxis_transform())
    ax.set_xlabel("Fare weight $w_2$ (other weights rescaled proportionally)")
    ax.set_ylabel("Weighted score $S_i$")
    ax.set_title(f"Break-even fare weight: {names[a].lower()} vs. {names[b].lower()}")
    ax.legend(loc="upper center", ncol=2)
    fig.tight_layout(); fig.savefig(out / "fig5_fare_weight_break_even.png"); plt.close(fig)


def fig_budget(modes, budget, out):
    """Number of feasible modes as the budget grows."""
    top = int(max(m["fare"] for m in modes) * 1.5) + 1
    budgets = np.arange(0, top + 1)
    counts = [len(rule_filter({"budget": b}, modes)["feasible"]) for b in budgets]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.step(budgets, counts, where="post", color=PAL[2], lw=2)
    for m in modes:
        ax.axvline(m["fare"], color="gray", ls=":", lw=1)
        ax.text(m["fare"] + 0.5, 0.15, f"{m['name']} (PHP {m['fare']:g})", rotation=90, fontsize=8, va="bottom")
    if budget is not None:
        ax.axvline(budget, color="black", ls="--", lw=1)
        ax.text(budget + 0.5, len(modes) - 0.5, f"budget\nPHP {budget:g}", fontsize=8)
    ax.set_yticks(range(0, len(modes) + 1))
    ax.set_xlabel("Budget (PHP)")
    ax.set_ylabel("Number of feasible alternatives")
    ax.set_title("Effect of the budget rule on the feasible set")
    fig.tight_layout(); fig.savefig(out / "fig6_budget_vs_feasible.png"); plt.close(fig)


def fig_runtime(sizes, t_rules, t_wsm, out):
    """Running time against the number of modes (log-log)."""
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.loglog(sizes, np.array(t_rules) * 1000, "o-", color=PAL[0], label="Rule filtering (forward chaining)")
    ax.loglog(sizes, np.array(t_wsm) * 1000, "s-", color=PAL[1], label="WSM scoring")
    ref = np.array(sizes) / sizes[-1] * t_rules[-1] * 1000
    ax.loglog(sizes, ref, "k--", lw=1, label="Linear reference")
    ax.set_xlabel("Number of transportation modes $m$")
    ax.set_ylabel("Running time (ms)")
    ax.set_title("Computational cost of the hybrid pipeline")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout(); fig.savefig(out / "fig7_computational_cost.png"); plt.close(fig)
