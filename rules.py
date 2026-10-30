"""
rules.py - Stage 1 of FASTR: rule-based filtering by forward chaining.

Implements Eq. (1) of the paper:
    Premises(R_k) is a subset of F  =>  add Conclusion(R_k) to F
and the budget rule of Eq. (6):
    Fare(a) > Budget(x)  =>  Infeasible(a, x)

Rule base (five rules per mode):
    R1  HasBudget AND ExceedsBudget(a)      => Infeasible(a)   budget limit        (Eq. 6)
    R2  Unavailable(a)                      => Infeasible(a)   mode not operating
    R3  Closed(a)                           => Infeasible(a)   outside service hours
    R4  TooFar(a)                           => Infeasible(a)   trip longer than the mode's limit
    R5  HasWaitLimit AND ExceedsMaxWait(a)  => Infeasible(a)   waiting time limit
A mode dictionary may contain the optional keys open, too_far, wait, closed_note and far_note.
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
    max_wait = commuter.get("max_wait")
    if budget is not None:
        facts.add("HasBudget")
        notes["HasBudget"] = f"commuter set a budget limit of PHP {budget:g}"
    if max_wait is not None:
        facts.add("HasWaitLimit")
        notes["HasWaitLimit"] = f"commuter accepts at most {max_wait:g} min of waiting"
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
            notes[f"ExceedsBudget({n})"] = f"fare PHP {m['fare']:g} > budget PHP {budget:g}"
        if not m.get("open", True):
            facts.add(f"Closed({n})")
            notes[f"Closed({n})"] = m.get("closed_note", "mode is not operating at this hour")
        if m.get("too_far", False):
            facts.add(f"TooFar({n})")
            notes[f"TooFar({n})"] = m.get("far_note", "trip is too long for this mode")
        if max_wait is not None and m.get("wait") is not None and m["wait"] > max_wait:
            facts.add(f"ExceedsMaxWait({n})")
            notes[f"ExceedsMaxWait({n})"] = f"waiting time {m['wait']:g} min > limit {max_wait:g} min"
    return facts, notes


def build_rules(modes):
    """Create the rule base (see the module docstring)."""
    rules = []
    for m in modes:
        n = m["name"]
        out = f"Infeasible({n})"
        rules.append(Rule(f"R1_budget[{n}]", frozenset({"HasBudget", f"ExceedsBudget({n})"}), out))
        rules.append(Rule(f"R2_unavailable[{n}]", frozenset({f"Unavailable({n})"}), out))
        rules.append(Rule(f"R3_closed[{n}]", frozenset({f"Closed({n})"}), out))
        rules.append(Rule(f"R4_too_far[{n}]", frozenset({f"TooFar({n})"}), out))
        rules.append(Rule(f"R5_max_wait[{n}]", frozenset({"HasWaitLimit", f"ExceedsMaxWait({n})"}), out))
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
