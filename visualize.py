"""Plotting helpers for FASTR results (matplotlib)."""

import os

import matplotlib
matplotlib.use("Agg")  # save to file; no display needed
import matplotlib.pyplot as plt
import numpy as np

from fastr import CRITERIA


def plot_scores(rec, path):
    """Bar chart of final WSM scores."""
    names = [m.name for m in rec.filtering.feasible]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(names, rec.scores, color=["#2e7d32" if i == rec.ranking[0] else "#90a4ae"
                                           for i in range(len(names))])
    for b, s in zip(bars, rec.scores):
        ax.text(b.get_x() + b.get_width() / 2, s + 0.01, f"{s:.3f}", ha="center")
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("WSM score $S_i$")
    ax.set_title("Final weighted scores (best in green)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_contributions(rec, path):
    """Stacked bars: each criterion's contribution w_j * r_ij to the score."""
    names = [m.name for m in rec.filtering.feasible]
    contrib = rec.normalized * rec.weights            # (m, 4)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    bottom = np.zeros(len(names))
    for j, c in enumerate(CRITERIA):
        ax.bar(names, contrib[:, j], bottom=bottom, label=c)
        bottom += contrib[:, j]
    ax.set_ylabel("Contribution to $S_i$")
    ax.set_title("Score decomposition by criterion")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_sensitivity(sweeps, names, crossovers, path):
    """
    sweeps: {criterion: (ts, scores)}; crossovers: {criterion: t* or None}.
    One panel per criterion; vertical dashed line marks where the top two modes tie.
    """
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
    for ax, (crit, (ts, S)) in zip(axes.ravel(), sweeps.items()):
        for i, n in enumerate(names):
            ax.plot(ts, S[:, i], label=n)
        t_star = crossovers.get(crit)
        if t_star is not None:
            ax.axvline(t_star, ls="--", color="k", lw=1)
            ax.text(t_star, 0.02, f" tie at {t_star:.3f}", fontsize=8)
        ax.set_title(f"Varying weight of {crit}")
        ax.set_xlabel(f"$w$ ({crit})")
        ax.grid(alpha=0.3)
    axes[0, 0].set_ylabel("Score")
    axes[1, 0].set_ylabel("Score")
    axes[0, 0].legend()
    fig.suptitle("Weight sensitivity (other weights rescaled proportionally)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_bisection(history, exact, path):
    """Convergence of bisection: absolute error vs. iteration (log scale)."""
    its = [h[0] for h in history]
    err = [max(abs(h[1] - exact), 1e-17) for h in history]
    width = [h[2] for h in history]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(its, err, "o-", label="|midpoint − exact root|")
    ax.semilogy(its, width, "s--", label="bracket width (error bound)")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Error")
    ax.set_title("Bisection convergence (linear rate, halves each step)")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_monte_carlo(names, p, se, path):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(names, p, yerr=1.96 * se, capsize=5, color="#5c6bc0")
    for i, v in enumerate(p):
        ax.text(i, v + 0.03, f"{v:.1%}", ha="center")
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Share of random weight vectors ranked 1st")
    ax.set_title("Robustness to weights (error bars = 95% CI)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
