"""
rules.py - Stage 1 of FASTR: rule-based filtering by forward chaining.

Implements Eq. (1) of the paper:
    Premises(R_k) is a subset of F  =>  add Conclusion(R_k) to F
and the budget rule of Eq. (6):
    Fare(a) > Budget(x)  =>  Infeasible(a, x)
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    """Production rule: IF all premises are in working memory THEN add the conclusion."""
    name: str
    premises: frozenset
    conclusion: str


def build_facts(commuter, modes):
    """Create the initial working memory F from the commuter and mode data.
    Returns (facts, notes). `notes` says where each fact came from; it is used
    later by the explanation facility."""
    facts, notes = set(), {}
    if commuter.get("student"):
        facts.add("Student")
        notes["Student"] = "commuter is a student"
    budget = commuter.get("budget")
    for m in modes:
        n = m["name"]
        if m["available"]:
            facts.add(f"ModeAvailable({n})")
            notes[f"ModeAvailable({n})"] = "mode is operating"
        else:
            facts.add(f"Unavailable({n})")
            notes[f"Unavailable({n})"] = "mode is not operating"
        if budget is not None and m["fare"] > budget:
            facts.add(f"ExceedsBudget({n})")
            notes[f"ExceedsBudget({n})"] = f"fare PHP {m['fare']} > budget PHP {budget}"
    return facts, notes


def build_rules(modes):
    """Two rules per mode:
         R1: Student AND ExceedsBudget(a)  =>  Infeasible(a)      (Eq. 6)
         R2: Unavailable(a)                =>  Infeasible(a)
    """
    rules = []
    for m in modes:
        n = m["name"]
        rules.append(Rule(f"R1_budget[{n}]", frozenset({"Student", f"ExceedsBudget({n})"}), f"Infeasible({n})"))
        rules.append(Rule(f"R2_unavailable[{n}]", frozenset({f"Unavailable({n})"}), f"Infeasible({n})"))
    return rules


def forward_chain(initial_facts, rules):
    """Forward chaining (Eq. 1). Make repeated passes over the rule base until a
    full pass adds no new fact (a fixed point).
    Returns (facts, trace, passes): the final facts, the proof trace and the number of passes."""
    facts, trace = set(initial_facts), []
    passes, changed = 0, True
    while changed:
        changed = False
        passes += 1
        for rule in rules:
            if rule.premises <= facts and rule.conclusion not in facts:   # premises subset of F
                facts.add(rule.conclusion)
                trace.append({"pass": passes, "rule": rule.name,
                              "premises": sorted(rule.premises), "conclusion": rule.conclusion})
                changed = True
    return facts, trace, passes


def rule_filter(commuter, modes):
    """Stage 1: remove infeasible modes. Returns the feasible set A_f (Eq. 5)
    together with the information needed for explanations."""
    facts0, notes = build_facts(commuter, modes)
    rules = build_rules(modes)
    facts, trace, passes = forward_chain(facts0, rules)
    feasible = [m for m in modes if f"Infeasible({m['name']})" not in facts]
    excluded = [m for m in modes if f"Infeasible({m['name']})" in facts]
    return {"feasible": feasible, "excluded": excluded, "facts": facts,
            "trace": trace, "passes": passes, "notes": notes, "n_rules": len(rules)}
