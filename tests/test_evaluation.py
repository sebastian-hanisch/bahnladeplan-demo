import pytest

import bahn_constants as C
import bahn_evaluation as E
import bahn_exact as X
import bahn_rules as R
import bahn_scenario as SC
from bahn_evaluation import ListResult

F_, D_, B_, X_ = C.STRAT_FIFO, C.STRAT_FFD, C.STRAT_BLOCKS, C.STRAT_EXACT


def lr(seed, fifo=40, ffd=42, blocks=46, exact=46, mixed=48, valid=None, proven=True, offered=58):
    v = dict({k: True for k in C.STRATEGY_KEYS}, **(valid or {}))
    return ListResult(seed, offered, {F_: fifo, D_: ffd, B_: blocks, X_: exact}, v, proven, "optimal" if proven else "feasible", mixed)


# ---------------------------------------------------------------------------------------------------
# ein Zug
# ---------------------------------------------------------------------------------------------------
def test_run_methods_returns_four_outcomes_in_order_with_valid_plans():
    inst = SC.make_instance(16, 4, 120, 50, 60, 35)
    outs = E.run_methods(inst, 2)
    assert [o.key for o in outs] == list(C.STRATEGY_KEYS) and [o.label for o in outs] == [C.STRATEGY_LABELS[k] for k in C.STRATEGY_KEYS]
    assert all(o.valid and o.violations == () for o in outs)
    assert [o.loaded for o in outs] == [46, 47, 48, 48]
    assert outs[3].exact.proven and E.outcome_of(outs, B_) is outs[2]


def test_exact_outcome_matches_direct_solve():
    inst = SC.make_instance(10, 5, 120, 50, 60, 2)
    o = E.exact_outcome(inst, 5)
    direct = X.solve_exact(inst, 5)
    assert o.loaded == direct.value and o.exact.proven == direct.proven and R.evaluate(inst, o.plan).loaded == o.loaded


def test_utilization_and_leftover():
    inst = SC.make_instance(16, 4, 120, 50, 60, 35)
    assert E.utilization(inst, 24) == 50.0 and E.utilization(inst, 48) == 100.0
    assert E.leftover(inst, 47) == 58 - 47


def test_comparison_rows_delta_is_mine_minus_reference_and_counts_used_wagons():
    inst = SC.make_instance(16, 4, 120, 50, 60, 35)
    outs = E.run_methods(inst, 2)
    rows = E.comparison_rows(inst, outs)
    assert [r.delta_vs_baseline for r in rows] == [0, 1, 2, 2]
    assert [r.loaded for r in rows] == [46, 47, 48, 48] and all(r.valid for r in rows)
    assert rows[0].n_used_wagons == sum(1 for w in outs[0].plan if w) and rows[0].leftover == 12 and rows[0].max_load <= 60
    assert abs(rows[2].utilization - 100.0) < 1e-9


def test_mixed_bound_is_an_upper_bound_of_the_pure_optimum():
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    upper, proven = E.mixed_bound(inst, 3)
    assert upper >= E.exact_outcome(inst, 3).loaded and upper <= SC.upper_bound(inst) and isinstance(proven, bool)


def test_exact_interval_reports_value_upper_and_proof():
    inst = SC.make_instance(16, 4, 120, 50, 60, 35)
    assert E.exact_interval(E.exact_outcome(inst, 2)) == (48, 48, True)


# ---------------------------------------------------------------------------------------------------
# Stichprobe
# ---------------------------------------------------------------------------------------------------
def test_run_list_is_consistent_with_a_direct_run_and_uses_the_given_seed():
    r = E.run_list(16, 4, 120, 50, 60, 35, 2)
    inst = SC.make_instance(16, 4, 120, 50, 60, 35)
    assert r.seed == 35 and r.offered == SC.offered(inst) == 58
    assert r.loaded == {F_: 46, D_: 47, B_: 48, X_: 48} and all(r.valid.values()) and r.proven and r.mixed_upper >= 48


def test_sample_uses_seeds_from_zero_and_reports_progress():
    seen = []
    res = E.sample(8, 3, 120, 50, 60, n_lists=3, exact_limit=1, progress=seen.append)
    assert [r.seed for r in res] == [0, 1, 2] and seen == [1 / 3, 2 / 3, 1.0]


def test_sample_differs_from_the_set_seed_and_repeats():
    a = E.sample(8, 3, 120, 50, 60, n_lists=2, exact_limit=1)
    b = E.sample(8, 3, 120, 50, 60, n_lists=2, exact_limit=1)
    assert [r.loaded for r in a] == [r.loaded for r in b]


def test_curve_plan_shrinks_for_long_trains():
    assert E.curve_plan(16) == (C.CURVE_POINTS, C.CURVE_LISTS)
    assert E.curve_plan(C.CURVE_LARGE_WAGONS - 1) == (C.CURVE_POINTS, C.CURVE_LISTS)
    assert E.curve_plan(C.CURVE_LARGE_WAGONS) == (C.CURVE_POINTS_LARGE, C.CURVE_LISTS_LARGE)
    assert E.curve_plan(30) == (C.CURVE_POINTS_LARGE, C.CURVE_LISTS_LARGE)


def test_curve_over_dests_equals_direct_runs_and_uses_the_same_seeds_at_every_point():
    cv = E.curve_over_dests(8, 120, 50, 60, exact_limit=1, points=(1, 3), n_lists=2)
    assert cv.points == (1, 3) and cv.n_lists == 2
    for d in (1, 3):
        assert [r.loaded for r in cv.lists[d]] == [E.run_list(8, d, 120, 50, 60, s, 1).loaded for s in range(2)]
        assert [r.seed for r in cv.lists[d]] == [0, 1]


def test_curve_over_dests_progress_counts_every_solve():
    seen = []
    E.curve_over_dests(8, 120, 50, 60, exact_limit=1, points=(1, 2), n_lists=2, progress=seen.append)
    assert seen == [0.25, 0.5, 0.75, 1.0]


# ---------------------------------------------------------------------------------------------------
# Statistik (mit künstlichen Ergebnissen)
# ---------------------------------------------------------------------------------------------------
def test_values_mean_median_valid_share():
    rs = [lr(0, fifo=40), lr(1, fifo=42), lr(2, fifo=44, valid={F_: False}), lr(3, fifo=50)]
    assert E.values(rs, F_) == [40, 42, 50] and E.mean_loaded(rs, F_) == pytest.approx(44.0) and E.median_loaded(rs, F_) == 42 and E.valid_share(rs, F_) == 0.75
    assert E.mean_loaded([lr(0, valid={F_: False})], F_) is None and E.median_loaded([lr(0, valid={F_: False})], F_) is None


def test_unproven_count_and_paired_only_over_jointly_valid_lists():
    rs = [lr(0, proven=False), lr(1), lr(2, valid={B_: False}), lr(3, proven=False)]
    assert E.unproven_count(rs) == 2
    assert E.paired(rs, B_, F_) == [6, 6, 6] and E.paired(rs, X_, B_) == [0, 0, 0]


def test_purity_price_is_mixed_bound_minus_exact_over_valid_lists():
    rs = [lr(0, mixed=48, exact=46), lr(1, mixed=47, exact=47), lr(2, mixed=48, exact=45, valid={X_: False})]
    assert E.purity_price(rs) == [2, 0] and E.mean_price(rs) == 1.0
    assert E.mean_price([lr(0, valid={X_: False})]) is None


def test_distribution_counts_better_equal_worse_and_positive_gain_is_more_loaded():
    rs = [lr(0, blocks=46), lr(1, blocks=40), lr(2, blocks=38), lr(3, blocks=46)]                 # fifo 40: +6, 0, -2, +6
    d = E.distribution(rs, B_, F_)
    assert (d.n, d.better, d.equal, d.worse) == (4, 0.5, 0.25, 0.25) and d.mean_gain == pytest.approx(2.5) and d.median_gain == 3.0
    empty = E.distribution([lr(0, valid={B_: False})], B_, F_)
    assert empty.n == 0 and empty.better == 0 and empty.mean_gain == 0


def test_verdict_three_states_and_none():
    better = [lr(i, blocks=46 + i % 2) for i in range(10)]
    v = E.verdict(better, B_, F_)
    assert v.kind == "better" and v.diff > 0 and v.pct > 0 and v.worse_share == 0 and v.n == 10
    worse = [lr(i, blocks=34 + i % 2) for i in range(10)]
    w = E.verdict(worse, B_, F_)
    assert w.kind == "worse" and w.diff < 0 and w.pct < 0 and w.worse_share == 1.0
    unclear = [lr(i, blocks=40 + (i % 2) * 2 - 1) for i in range(10)]
    assert E.verdict(unclear, B_, F_).kind == "unclear"
    none = E.verdict([lr(0, valid={B_: False})], B_, F_)
    assert none.kind == "none" and none.n == 0 and none.pct is None


def test_verdict_threshold_is_two_standard_errors_and_equal_lists_are_unclear():
    same = [lr(i, blocks=40) for i in range(6)]
    v = E.verdict(same, B_, F_)
    assert v.kind == "unclear" and v.diff == 0 and v.se == 0
    constant = [lr(i, blocks=41) for i in range(6)]                                            # gleiche Differenz überall: se = 0, klar
    assert E.verdict(constant, B_, F_).kind == "better"
    # Differenzen 0, 2 ...: Mittel 1, se = sd/sqrt(n); bei n=4: sd = 1.155, se = 0.577, 2 se = 1.155 > 1 -> unklar; bei n=16 klar
    few = [lr(i, blocks=40 + (i % 2) * 2) for i in range(4)]
    many = [lr(i, blocks=40 + (i % 2) * 2) for i in range(16)]
    assert E.verdict(few, B_, F_).kind == "unclear" and E.verdict(many, B_, F_).kind == "better"


def test_verdict_pct_is_none_when_the_reference_loads_nothing():
    rs = [lr(i, fifo=0, blocks=2) for i in range(6)]
    v = E.verdict(rs, B_, F_)
    assert v.kind == "better" and v.pct is None


def test_curve_means_mixed_price_proven_and_kante():
    pts = (1, 2, 3)
    cv = E.Curve(pts, {1: (lr(0, exact=48, mixed=48), lr(1, exact=48, mixed=48)), 2: (lr(0, exact=47, mixed=48, proven=False), lr(1, exact=48, mixed=48)),
                       3: (lr(0, exact=46, mixed=48), lr(1, exact=47, mixed=48))}, 2)
    assert E.curve_means(cv, X_) == (48.0, 47.5, 46.5) and E.curve_mixed(cv) == (48.0, 48.0, 48.0)
    assert E.curve_price(cv) == (0.0, 0.5, 1.5) and E.curve_proven(cv) == (1.0, 0.5, 1.0)
    assert E.kante(cv) == 3 and E.kante(cv, threshold=0.4) == 2 and E.kante(cv, threshold=5) is None


def test_kante_needs_a_price_strictly_above_the_threshold_and_skips_points_without_valid_lists():
    cv = E.Curve((1, 2), {1: (lr(0, exact=47, mixed=48),), 2: (lr(0, exact=46, mixed=48, valid={X_: False}),)}, 1)
    assert E.kante(cv, threshold=1.0) is None and E.kante(cv, threshold=0.99) == 1
    assert E.curve_means(cv, X_)[1] is None and E.curve_price(cv)[1] is None


# ---------------------------------------------------------------------------------------------------
# Feinheiten (aus dem Fehler-Einbau-Test)
# ---------------------------------------------------------------------------------------------------
def test_verdict_exactly_at_two_standard_errors_is_still_unclear():
    rs = [lr(0, fifo=40, blocks=41), lr(1, fifo=40, blocks=43)]                               # Differenzen 1 und 3: Mittel 2, Standardfehler 1, also genau 2 Standardfehler
    v = E.verdict(rs, B_, F_)
    assert v.diff == 2.0 and v.se == pytest.approx(1.0) and v.kind == "unclear"


def test_comparison_rows_count_only_wagons_with_cargo():
    inst = SC.make_instance(30, 1, 80, 0, 70, 3)                                              # viel Platz: nicht alle Wagen werden gebraucht
    outs = E.run_methods(inst, 1)
    rows = E.comparison_rows(inst, outs)
    assert all(r.n_used_wagons < 30 for r in rows) and all(r.n_used_wagons == sum(1 for w in o.plan if w) for r, o in zip(rows, outs))


def test_run_list_mixed_bound_is_never_below_the_exact_value(monkeypatch):
    monkeypatch.setattr(E, "mixed_bound", lambda inst, limit: (10, False))
    r = E.run_list(8, 3, 120, 50, 60, 0, 1)
    assert r.mixed_upper == r.loaded[X_] > 10
