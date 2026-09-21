import pytest
from ortools.sat.python import cp_model

import bahn_constants as C
import bahn_exact as X
import bahn_rules as R
import bahn_scenario as SC
from helpers import brute_force, tiny_instance


def valid_plan(inst, res):
    ev = R.evaluate(inst, res.plan)
    return ev.valid and ev.loaded == res.value


# ---------------------------------------------------------------------------------------------------
# gegen Brute Force
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(120))
def test_cp_sat_equals_brute_force_on_tiny_instances(seed):
    inst = tiny_instance(seed, n_wagons=2 if seed % 3 else 3, max_boxes=6 if seed % 3 else 5)
    res = X.solve_exact(inst, 20, use_hint=(seed % 2 == 0), workers=2)
    assert res.status == "optimal" and res.value == res.upper == brute_force(inst)
    assert valid_plan(inst, res)


@pytest.mark.parametrize("seed", range(60))
def test_mixed_bound_equals_brute_force_without_purity_and_is_never_below_the_pure_optimum(seed):
    inst = tiny_instance(seed)
    mixed = X.solve_exact(inst, 20, purity=False, workers=2)
    assert mixed.status == "optimal" and mixed.value == brute_force(inst, purity=False)
    assert mixed.value >= X.solve_exact(inst, 20, workers=2).value


def test_the_tiny_comparison_is_not_vacuous():
    """Es gibt Instanzen, in denen die Reinheit etwas kostet und in denen nicht alles mitfährt."""
    price = [brute_force(tiny_instance(s), purity=False) - brute_force(tiny_instance(s)) for s in range(60)]
    assert sum(1 for p in price if p > 0) >= 5 and sum(1 for p in price if p == 0) >= 20
    assert sum(1 for s in range(60) if brute_force(tiny_instance(s)) < SC.offered(tiny_instance(s))) >= 15


# ---------------------------------------------------------------------------------------------------
# Eigenschaften auf mittleren Instanzen
# ---------------------------------------------------------------------------------------------------
def test_optimum_is_at_least_every_rule_and_at_most_the_mixed_bound():
    for seed in range(12):
        inst = SC.make_instance(12, 3 + seed % 4, 120, 50, 60 if seed % 2 else 45, seed)
        res = X.solve_exact(inst, 10)
        assert valid_plan(inst, res)
        for rule in (R.fifo, R.ffd, R.blocks):
            assert R.evaluate(inst, rule(inst)).loaded <= res.value
        mixed = X.solve_exact(inst, 10, purity=False)
        assert res.value <= mixed.upper and res.value <= res.upper <= SC.upper_bound(inst)


def test_hint_and_no_hint_give_the_same_proven_optimum():
    for seed in range(6):
        inst = SC.make_instance(10, 4, 120, 50, 60, seed)
        a, b = X.solve_exact(inst, 20, use_hint=True), X.solve_exact(inst, 20, use_hint=False)
        assert a.proven and b.proven and a.value == b.value


def test_more_offer_never_lowers_the_optimum_and_more_wagons_never_either():
    """Monotonie: dasselbe Präfix an Containern mit mehr Wagen lädt nicht weniger."""
    inst = SC.make_instance(8, 4, 120, 50, 60, 5)
    more = SC.custom_instance(9, 4, 60, inst.boxes)
    assert X.solve_exact(more, 20).value >= X.solve_exact(inst, 20).value
    lighter = SC.custom_instance(8, 4, 70, inst.boxes)
    assert X.solve_exact(lighter, 20).value >= X.solve_exact(inst, 20).value                 # höhere Wagenlast: nicht weniger


# ---------------------------------------------------------------------------------------------------
# Beweislage
# ---------------------------------------------------------------------------------------------------
def test_shortcut_when_the_rule_reaches_the_trivial_bound_no_solver_is_called(monkeypatch):
    inst = SC.make_instance(30, 1, 80, 0, 70, 3)                                             # alles passt
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: pytest.fail("Löser darf nicht laufen"))
    res = X.solve_exact(inst, 5)
    assert res.status == "optimal" and res.source == "Regel" and res.value == res.upper == SC.offered(inst)


def test_full_train_is_proven_without_the_solver_when_the_rule_fills_every_place(monkeypatch):
    inst = SC.make_instance(16, 1, 150, 0, 70, 3)
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: pytest.fail("Löser darf nicht laufen"))
    res = X.solve_exact(inst, 5)
    assert res.value == SC.capacity(inst) and res.proven


def test_solver_result_replaces_the_rule_only_when_at_least_as_good(monkeypatch):
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    rule_value = R.evaluate(inst, R.blocks(inst)).loaded
    worse = tuple(() for _ in range(inst.n_wagons))
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: (cp_model.FEASIBLE, worse, rule_value - 5, rule_value + 1))
    res = X.solve_exact(inst, 1)
    assert res.source == "Regel" and res.value == rule_value and res.plan == R.blocks(inst)


def test_solver_without_a_plan_keeps_the_rule_and_never_claims_a_proof(monkeypatch):
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    rule_value = R.evaluate(inst, R.blocks(inst)).loaded
    if rule_value >= SC.upper_bound(inst):
        pytest.skip("die Regel erreicht die triviale Schranke")
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: (cp_model.UNKNOWN, None, None, None))
    res = X.solve_exact(inst, 1)
    assert res.status == "feasible" and res.source == "Regel" and res.value == rule_value and res.upper == SC.upper_bound(inst) and not res.proven


def test_feasible_result_carries_a_valid_interval(monkeypatch):
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    plan = R.blocks(inst)
    v = R.evaluate(inst, plan).loaded
    if v >= SC.upper_bound(inst) - 1:
        pytest.skip("kein Platz für ein Intervall")
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: (cp_model.FEASIBLE, plan, v, v + 1))
    res = X.solve_exact(inst, 1)
    assert res.status == "feasible" and res.value == v and res.upper == v + 1 and not res.proven


def test_solver_bound_meeting_the_value_counts_as_proven(monkeypatch):
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    plan = R.blocks(inst)
    v = R.evaluate(inst, plan).loaded
    if v >= SC.upper_bound(inst):
        pytest.skip("Regel erreicht die triviale Schranke")
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: (cp_model.FEASIBLE, plan, v, v))
    res = X.solve_exact(inst, 1)
    assert res.status == "optimal" and res.upper == res.value == v


def test_upper_bound_is_never_below_the_value_and_never_above_the_trivial_bound():
    for seed in range(8):
        inst = SC.make_instance(16, 6 + seed % 4, 120, 50, 60, seed)
        res = X.solve_exact(inst, 2)
        assert res.value <= res.upper <= SC.upper_bound(inst)


def test_time_limit_is_respected():
    inst = SC.make_instance(30, 10, 150, 50, 60, 1)
    res = X.solve_exact(inst, 1, workers=4)
    assert res.wall_ms < 6000 and valid_plan(inst, res)


def test_mixed_bound_without_a_plan_from_the_solver_is_an_upper_bound_only(monkeypatch):
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: (cp_model.UNKNOWN, None, None, None))
    res = X.solve_exact(inst, 1, purity=False)
    assert res.status == "feasible" and res.plan is None and res.value == 0 and res.upper == SC.upper_bound(inst)


def test_default_seed_scenario_values():
    """Feste Werte des Standard-Szenarios (16 Wagen, 4 Ziele, 120 %, 50 %, 60 t, Seed 35)."""
    inst = SC.make_instance(16, 4, 120, 50, 60, 35)
    res = X.solve_exact(inst, C.EXACT_LIVE_LIMIT_SECONDS)
    assert res.proven and res.value == 48 and R.evaluate(inst, R.fifo(inst)).loaded == 46 and R.evaluate(inst, R.blocks(inst)).loaded == 48


# ---------------------------------------------------------------------------------------------------
# Feinheiten (aus dem Fehler-Einbau-Test)
# ---------------------------------------------------------------------------------------------------
def test_solver_plan_of_equal_value_is_kept_and_labelled_as_from_the_solver(monkeypatch):
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    other = R.ffd(inst)
    v = R.evaluate(inst, R.blocks(inst)).loaded
    if v >= SC.upper_bound(inst) - 1:
        pytest.skip("kein Platz für ein Intervall")
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: (cp_model.FEASIBLE, other, v, v + 1))
    res = X.solve_exact(inst, 1)
    assert res.source == "Löser" and res.plan == other


def test_upper_bound_is_capped_at_the_trivial_bound(monkeypatch):
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    plan = R.blocks(inst)
    v = R.evaluate(inst, plan).loaded
    if v >= SC.upper_bound(inst) - 1:
        pytest.skip("kein Platz für ein Intervall")
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: (cp_model.FEASIBLE, plan, v, SC.upper_bound(inst) + 20))
    res = X.solve_exact(inst, 1)
    assert res.upper == SC.upper_bound(inst) and res.status == "feasible"


def test_a_proven_result_reports_upper_equal_to_value_even_if_the_bound_is_looser(monkeypatch):
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    plan = R.blocks(inst)
    v = R.evaluate(inst, plan).loaded
    if v >= SC.upper_bound(inst) - 1:
        pytest.skip("Instanz passt nicht")
    monkeypatch.setattr(X, "_solve_model", lambda *a, **k: (cp_model.OPTIMAL, plan, v, v + 1))
    res = X.solve_exact(inst, 1)
    assert res.status == "optimal" and res.upper == res.value == v


_REAL_SOLVER = cp_model.CpSolver


class _FractionalBound:
    """CP-SAT-Löser, dessen Schranke einen halben Punkt über dem Zielwert liegt (zeigt: abgerundet, nicht aufgerundet)."""
    def __init__(self):
        self._real = _REAL_SOLVER()
        self.parameters = self._real.parameters

    def Solve(self, model):
        self._real.Solve(model)
        return cp_model.FEASIBLE

    def Value(self, v):
        return self._real.Value(v)

    def ObjectiveValue(self):
        return self._real.ObjectiveValue()

    def BestObjectiveBound(self):
        return self._real.ObjectiveValue() + 0.5


def test_fractional_solver_bound_is_rounded_down(monkeypatch):
    inst = SC.make_instance(16, 8, 120, 50, 60, 0)
    if R.evaluate(inst, R.blocks(inst)).loaded >= SC.upper_bound(inst):
        pytest.skip("Regel erreicht die triviale Schranke")
    monkeypatch.setattr(cp_model, "CpSolver", _FractionalBound)
    res = X.solve_exact(inst, 2, workers=2)
    assert res.upper == res.value and res.proven                                              # Zielwert + 0,5 rundet auf den Zielwert ab: bewiesen
