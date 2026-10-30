"""
explain.py - Explanation facility (Section 4.5 of the paper).

Turns the proof trace and the score calculation into readable text.
"""
import numpy as np

from config import WEIGHTS
from wsm import r3


def explain_exclusion(name, result):
    """Proof trace: which rule removed a mode, in which pass, and from which facts."""
    steps = [t for t in result["trace"] if t["conclusion"] == f"Infeasible({name})"]
    if not steps:
        return f"'{name}' was not excluded by any rule."
    lines = [f"WHY was '{name}' excluded?"]
    for t in steps:
        lines.append(f"  Rule {t['rule']} fired in pass {t['pass']}:")
        for p in t["premises"]:
            note = result["notes"].get(p, "")
            lines.append(f"    - fact {p}" + (f"  [{note}]" if note else ""))
        lines.append(f"    => {t['conclusion']}  (removed before scoring, not given a low score)")
    return "\n".join(lines)


def explain_ranking(result, w=WEIGHTS):
    """Show the weighted-score calculation of every feasible mode."""
    feasible, R, S = result["feasible"], result["R"], result["S"]
    order = np.argsort(-S)
    lines = [f"WHY is '{feasible[order[0]]['name']}' ranked first?"]
    for i in order:
        terms = " + ".join(f"({wj:.3g})({r:.3f})" for wj, r in zip(w, R[i]))
        lines.append(f"  {feasible[i]['name']:<22} S = {terms} = {r3(S[i]):.3f}   (rank {result['ranks'][i]})")
    return "\n".join(lines)
