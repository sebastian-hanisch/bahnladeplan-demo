"""Exaktes Verfahren (CP-SAT): die größte Zahl geladener TEU.

Variablen x[i,w,p] (Container i liegt in Wagen w, beginnend auf Platz p) und y[w,d] (Wagen w fährt zu Ziel d). Jeder Container höchstens einmal, jeder Platz höchstens einmal (ein
40-Fuß-Container belegt p und p+1), ein Ziel je Wagen, Wagenlast; maximiert werden die geladenen TEU. Ohne Zielreinheit (`purity=False`) fällt y weg: die Schranke, was gemischte Wagen brächten.

Ergebnisse tragen ihre Beweislage: `optimal` (bewiesen) oder `feasible` (Plan da, Optimum nicht bewiesen: Intervall [value, upper]). Startlösung und Rückfall ist die Regel Wagenblöcke;
erreicht sie schon die triviale Schranke (alles Angebotene oder alle Plätze), ist sie ohne Löser optimal."""

import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

import bahn_constants as C
import bahn_rules as R
import bahn_scenario as SC
from bahn_scenario import teu

NUM_SEARCH_WORKERS = 8


@dataclass(frozen=True)
class ExactResult:
    status: str             # "optimal" | "feasible"
    plan: object            # Plan oder None (nur bei purity=False ohne Startlösung)
    value: int              # geladene TEU des Plans (untere Schranke des Optimums)
    upper: int              # obere Schranke des Optimums
    source: str             # "Löser" | "Regel"
    wall_ms: float

    @property
    def proven(self):
        return self.status == "optimal"


def _solve_model(inst, time_limit, hint_plan, purity, workers):
    W, D = inst.n_wagons, inst.n_dests
    m = cp_model.CpModel()
    x, cell, load = {}, {(w, q): [] for w in range(W) for q in range(C.PLACES)}, {w: [] for w in range(W)}
    y = {(w, d): m.NewBoolVar(f"y{w}_{d}") for w in range(W) for d in (range(D) if purity else [0])}
    if purity:
        for w in range(W):
            m.Add(sum(y[w, d] for d in range(D)) <= 1)
    for i, b in enumerate(inst.boxes):
        n = teu(b)
        for w in range(W):
            for p in range(C.PLACES - n + 1):
                v = m.NewBoolVar(f"x{i}_{w}_{p}")
                x[i, w, p] = v
                if purity:
                    m.AddImplication(v, y[w, b[2]])
                for q in range(p, p + n):
                    cell[w, q].append(v)
                load[w].append((b[1], v))
        m.Add(sum(x[i, w, p] for w in range(W) for p in range(C.PLACES - n + 1)) <= 1)
    for v in cell.values():
        m.Add(sum(v) <= 1)
    for w in range(W):
        m.Add(sum(wt * v for wt, v in load[w]) <= inst.payload)
    m.Maximize(sum(teu(inst.boxes[i]) * v for (i, w, p), v in x.items()))
    if hint_plan is not None:
        used = {(i, w, p) for w, wagon in enumerate(hint_plan) for p, i in wagon}
        for k, v in x.items():
            m.AddHint(v, 1 if k in used else 0)
        if purity:
            for w, wagon in enumerate(hint_plan):
                dest = R.wagon_dest(inst, wagon)
                for d in range(D):
                    m.AddHint(y[w, d], 1 if dest == d else 0)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = time_limit
    s.parameters.num_workers = workers
    s.parameters.log_search_progress = False
    status = s.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return status, None, None, None
    wagons = [[] for _ in range(W)]
    for (i, w, p), v in x.items():
        if s.Value(v):
            wagons[w].append((p, i))
    plan = tuple(tuple(sorted(wg)) for wg in wagons)
    return status, plan, int(round(s.ObjectiveValue())), int(s.BestObjectiveBound() + 1e-6)


def solve_exact(inst, time_limit=C.EXACT_LIVE_LIMIT_SECONDS, use_hint=True, purity=True, workers=NUM_SEARCH_WORKERS):
    """Größte Zahl geladener TEU mit Zeitlimit. Mit `purity=False` die Schranke ohne Zielreinheit (dann ohne Regel-Rückfall)."""
    t0 = time.perf_counter()
    trivial = SC.upper_bound(inst)
    rule_plan, rule_value = None, 0
    if purity:
        rule_plan = R.blocks(inst)
        rule_value = R.evaluate(inst, rule_plan).loaded
        if rule_value >= trivial:
            return ExactResult("optimal", rule_plan, rule_value, trivial, "Regel", (time.perf_counter() - t0) * 1000)
    status, plan, value, bound = _solve_model(inst, time_limit, rule_plan if use_hint else None, purity, workers)
    upper = trivial if bound is None else min(trivial, max(bound, value))
    if plan is None or (purity and value < rule_value):
        # der Löser fand nichts oder etwas Schlechteres als die Regel: die Regel bleibt der Plan (nie bewiesen, außer die Schranke trifft sie)
        upper = trivial if bound is None else min(trivial, bound)
        if purity:
            return ExactResult("optimal" if rule_value >= upper else "feasible", rule_plan, rule_value, max(upper, rule_value), "Regel", (time.perf_counter() - t0) * 1000)
        return ExactResult("feasible", None, 0, upper, "Regel", (time.perf_counter() - t0) * 1000)
    proven = status == cp_model.OPTIMAL or value >= upper
    return ExactResult("optimal" if proven else "feasible", plan, value, upper if not proven else value, "Löser", (time.perf_counter() - t0) * 1000)
