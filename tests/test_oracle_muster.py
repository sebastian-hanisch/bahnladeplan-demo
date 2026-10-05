"""Orakel auf anderem Rechenweg: Wagenmuster-Dynamik (Teilmengen je Wagen, Bitmasken über die Container) statt Platz-für-Platz-Aufzählung und CP-SAT.

Ein Wagen mit drei Plätzen trägt höchstens drei Plätze Container; mit höchstens drei Plätzen ist die Nachbarschaft nie bindend (40 Fuß plus 20 Fuß passen in jeder Reihenfolge), zulässig
ist also jede Teilmenge mit Platzsumme <= 3, Gewichtssumme <= Wagenlast und (mit Zielreinheit) einem Ziel. Das Optimum ist die beste Auswahl überschneidungsfreier Muster."""
import itertools
import random
import statistics

import pytest

import bahn_constants as C
import bahn_evaluation as E
import bahn_exact as X
import bahn_rules as R
import bahn_scenario as SC
from bahn_scenario import teu


def _patterns(inst, purity):
    out = []
    for k in (1, 2, 3):
        for sub in itertools.combinations(range(len(inst.boxes)), k):
            if sum(teu(inst.boxes[i]) for i in sub) > C.PLACES or sum(inst.boxes[i][1] for i in sub) > inst.payload:
                continue
            if purity and len({inst.boxes[i][2] for i in sub}) > 1:
                continue
            out.append((sum(1 << i for i in sub), sum(teu(inst.boxes[i]) for i in sub)))
    return out


def pattern_optimum(inst, purity=True):
    pats = _patterns(inst, purity)
    best = {0: 0}
    for _ in range(inst.n_wagons):
        new = dict(best)
        for mask, v in best.items():
            for pm, pv in pats:
                if not mask & pm and new.get(mask | pm, -1) < v + pv:
                    new[mask | pm] = v + pv
        best = new
    return max(best.values())


def _instance(seed):
    rng = random.Random(seed)
    d = rng.randint(1, 3)
    boxes = []
    for _ in range(rng.randint(1, 9)):
        is40 = rng.random() < 0.45
        boxes.append((40 if is40 else 20, rng.randint(*(C.WEIGHT_40 if is40 else C.WEIGHT_20)), rng.randrange(d)))
    return SC.custom_instance(rng.randint(1, 3), d, rng.choice([25, 30, 40, 45, 60, 70]), boxes)


def test_hand_example_for_the_pattern_oracle():
    # zwei Wagen, Last 30: 40-Fuß (20 t, Ziel 0) + 20-Fuß (10 t, Ziel 0) passt in einen Wagen; der zweite Wagen nimmt mit Reinheit nur die beiden Container des Ziels 1 (25 t), gemischt auch den vom Ziel 2 (30 t)
    inst = SC.custom_instance(2, 3, 30, [(40, 20, 0), (20, 10, 0), (20, 20, 1), (20, 5, 1), (20, 5, 2)])
    assert pattern_optimum(inst) == 5 and pattern_optimum(inst, purity=False) == 6


@pytest.mark.parametrize("seed", range(60))
def test_exact_and_rules_against_the_pattern_oracle(seed):
    inst = _instance(seed)
    opt, opt_mixed = pattern_optimum(inst), pattern_optimum(inst, purity=False)
    res = X.solve_exact(inst, 10)
    assert res.proven and res.value == res.upper == opt
    assert R.evaluate(inst, res.plan).valid and R.evaluate(inst, res.plan).loaded == opt
    mixed = X.solve_exact(inst, 10, purity=False)
    assert mixed.proven and mixed.upper == opt_mixed >= opt
    for rule in (R.fifo, R.ffd, R.blocks):
        ev = R.evaluate(inst, rule(inst))
        assert ev.valid and ev.loaded <= opt


@pytest.mark.parametrize("seed", range(20))
def test_verdict_and_distribution_against_numpy_free_hand_statistics(seed):
    rng = random.Random(seed)
    res = []
    for s in range(rng.randint(2, 12)):
        loaded = {k: rng.randint(0, 48) for k in C.STRATEGY_KEYS}
        res.append(E.ListResult(s, 50, loaded, {k: rng.random() < 0.85 for k in C.STRATEGY_KEYS}, True, "optimal", loaded["exact"] + rng.randint(0, 3)))
    for key in C.STRATEGY_KEYS:
        d = [r.loaded[key] - r.loaded["fifo"] for r in res if r.valid[key] and r.valid["fifo"]]
        v, dist = E.verdict(res, key), E.distribution(res, key)
        if not d:
            assert v.kind == "none" and dist.n == 0
            continue
        mean = sum(d) / len(d)
        se = (sum((x - mean) ** 2 for x in d) / (len(d) - 1) / len(d)) ** 0.5 if len(d) > 1 else 0.0
        assert abs(v.diff - mean) < 1e-9 and abs(v.se - se) < 1e-9 and v.n == len(d)
        kind = ("unclear" if mean == 0 else "better" if mean > 0 else "worse") if se == 0 else ("unclear" if abs(mean) <= 2 * se else "better" if mean > 0 else "worse")
        assert v.kind == kind
        assert abs(dist.better - sum(x > 0 for x in d) / len(d)) < 1e-12 and abs(dist.worse - sum(x < 0 for x in d) / len(d)) < 1e-12
        assert abs(dist.median_gain - statistics.median(d)) < 1e-12
