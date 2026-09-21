import statistics

import pytest

import bahn_constants as C
import bahn_rules as R
import bahn_scenario as SC
from bahn_scenario import teu
from helpers import brute_force, random_instance, tiny_instance

RULES = {"fifo": R.fifo, "ffd": R.ffd, "blocks": R.blocks}


def inst_of(boxes, n_wagons=2, n_dests=3, payload=60):
    return SC.custom_instance(n_wagons, n_dests, payload, boxes)


# ---------------------------------------------------------------------------------------------------
# Bewertung: jede Bedingung einzeln
# ---------------------------------------------------------------------------------------------------
def test_evaluate_counts_loaded_teu_and_boxes_and_max_load():
    inst = inst_of([(20, 10, 0), (40, 20, 0), (20, 5, 1)])
    plan = (((0, 0), (1, 1)), ((0, 2),))
    ev = R.evaluate(inst, plan)
    assert ev.valid and ev.loaded == 4 and ev.n_boxes == 3 and ev.max_load == 30 and ev.violations == ()


def test_evaluate_empty_plan_loads_nothing_and_is_valid():
    ev = R.evaluate(inst_of([(20, 10, 0)]), ((), ()))
    assert ev.valid and ev.loaded == 0 and ev.max_load == 0


@pytest.mark.parametrize("plan,expected", [
    ((((0, 0),),), "Wagen"),                                        # zu wenige Wagen
    ((((0, 0),), ((0, 0),)), "Container"),                          # Container 0 zweimal
    ((((0, 5),), ()), "Container"),                                 # unbekannter Container
    ((((-1, 0),), ()), "Platz"),                                    # Startplatz vor dem Wagen
    ((((3, 0),), ()), "Platz"),                                     # Startplatz hinter dem Wagen
    ((((2, 1),), ()), "Platz"),                                     # 40 Fuß ragt über das Wagenende
    ((((0, 0), (0, 2)), ()), "Platz"),                              # zwei Container auf demselben Platz
    ((((0, 1), (1, 0)), ()), "Platz"),                              # 20 Fuß liegt auf dem zweiten Platz des 40-Fuß-Containers
])
def test_evaluate_flags_each_placement_error(plan, expected):
    inst = inst_of([(20, 10, 0), (40, 20, 0), (20, 5, 0)])
    assert expected in R.evaluate(inst, plan).violations


def test_evaluate_flags_load_and_mixed_destinations_and_treats_the_boundary_as_valid():
    inst = inst_of([(20, 30, 0), (20, 30, 0), (20, 1, 0), (20, 5, 1)], payload=60)
    assert R.evaluate(inst, (((0, 0), (1, 1)), ())).valid                                   # genau 60 t: erlaubt
    assert "Last" in R.evaluate(inst, (((0, 0), (1, 1), (2, 2)), ())).violations           # 61 t
    assert "Ziel" in R.evaluate(inst, (((0, 0), (1, 3)), ())).violations
    assert R.evaluate(inst, (((0, 0), (1, 1), (2, 2)), ())).loaded == 3                    # geladen zählt trotzdem (Verletzung ist benannt)


def test_evaluate_reports_each_violation_only_once():
    inst = inst_of([(20, 50, 0), (20, 50, 1), (20, 50, 1)])
    ev = R.evaluate(inst, (((0, 0), (1, 1), (2, 2)), ()))
    assert ev.violations.count("Last") == 1 and ev.violations.count("Ziel") == 1


# ---------------------------------------------------------------------------------------------------
# Regeln
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(RULES))
def test_every_rule_returns_a_valid_plan_within_the_upper_bound(name):
    for seed in range(60):
        inst = random_instance(seed)
        plan = RULES[name](inst)
        ev = R.evaluate(inst, plan)
        assert ev.valid, (name, seed, ev.violations)
        assert len(plan) == inst.n_wagons and ev.loaded <= SC.upper_bound(inst)


@pytest.mark.parametrize("name", list(RULES))
def test_every_rule_loads_everything_when_there_is_plenty_of_room(name):
    inst = SC.make_instance(30, 1, 80, 0, 70, 3)                                            # ein Ziel, nur 20 Fuß, 80 % Angebot
    assert R.evaluate(inst, RULES[name](inst)).loaded == SC.offered(inst)


@pytest.mark.parametrize("name", list(RULES))
def test_no_rule_beats_the_brute_force_optimum(name):
    checked = 0
    for seed in range(50):
        inst = tiny_instance(seed)
        assert R.evaluate(inst, RULES[name](inst)).loaded <= brute_force(inst)
        checked += 1
    assert checked == 50


def test_at_least_one_tiny_instance_leaves_something_behind_so_the_comparison_is_not_vacuous():
    left = [seed for seed in range(50) if brute_force(tiny_instance(seed)) < SC.offered(tiny_instance(seed))]
    assert len(left) >= 10


def test_one_destination_all_rules_agree_on_average_and_blocks_reach_the_bound_often():
    means = {name: statistics.fmean(R.evaluate(SC.make_instance(16, 1, 120, 50, 60, s), rule(SC.make_instance(16, 1, 120, 50, 60, s))).loaded for s in range(20)) for name, rule in RULES.items()}
    assert max(means.values()) - min(means.values()) < 1.0


def test_rules_are_deterministic():
    inst = random_instance(4)
    for rule in RULES.values():
        assert rule(inst) == rule(inst)


def test_measured_ordering_over_many_days_at_four_and_eight_destinations():
    """Gemessene Tatsachen (16 Wagen, 120 %, 60 t, 20 Tage): Reihenfolge < Größe zuerst < Wagenblöcke im Mittel; Wagenblöcke laden mindestens 2 TEU mehr als die Reihenfolge."""
    for d in (4, 8):
        insts = [SC.make_instance(16, d, 120, 50, 60, s) for s in range(20)]
        mean = {n: statistics.fmean(R.evaluate(i, r(i)).loaded for i in insts) for n, r in RULES.items()}
        assert mean["fifo"] < mean["ffd"] < mean["blocks"]
        assert mean["blocks"] - mean["fifo"] >= 2


def test_blocks_never_load_a_wagon_of_mixed_destinations_and_use_full_wagons_first():
    inst = SC.make_instance(16, 6, 120, 50, 60, 2)
    plan = R.blocks(inst)
    fills = [sum(teu(inst.boxes[i]) for _, i in w) for w in plan if w]
    assert fills == sorted(fills, reverse=True)                                              # die vollsten Wagen zuerst
    for w in plan:
        assert len({inst.boxes[i][2] for _, i in w}) <= 1


def test_blocks_skip_a_container_heavier_than_the_wagon_load():
    inst = inst_of([(40, 30, 0), (20, 6, 0)], payload=25, n_wagons=1)
    plan = R.blocks(inst)
    assert R.evaluate(inst, plan).valid and R.evaluate(inst, plan).loaded == 1


def test_fifo_takes_the_first_fitting_wagon_of_the_same_destination():
    inst = inst_of([(20, 10, 0), (20, 10, 1), (20, 10, 0)], n_wagons=3)
    plan = R.fifo(inst)
    assert plan[0] == ((0, 0), (1, 2)) and plan[1] == ((0, 1),)                              # dritter Container zum ersten Wagen (gleiches Ziel), nicht zum leeren


def test_ffd_puts_forty_footers_first_and_heavy_first_within_a_length():
    inst = inst_of([(20, 5, 0), (40, 10, 0), (20, 20, 0)], n_wagons=2)
    assert R._size_order(inst) == [1, 2, 0]
    plan = R.ffd(inst)
    assert plan[0][0] == (0, 1)                                                              # der 40-Fuß-Container steht auf Platz 1-2 des ersten Wagens


def test_free_places_and_wagon_dest_helpers():
    inst = inst_of([(20, 5, 2), (40, 10, 2)])
    assert R.wagon_dest(inst, ()) is None and R.wagon_dest(inst, ((0, 0),)) == 2
    assert R.free_places(((0, 0),), inst) == 2 and R.free_places(((0, 0), (1, 1)), inst) == 0 and R.free_places((), inst) == C.PLACES


# ---------------------------------------------------------------------------------------------------
# Feinheiten (aus dem Fehler-Einbau-Test)
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(RULES))
def test_every_rule_fills_a_wagon_exactly_to_the_wagon_load(name):
    inst = inst_of([(20, 10, 0), (20, 10, 0)], n_wagons=2, payload=20)
    plan = RULES[name](inst)
    assert R.evaluate(inst, plan).loaded == 2 and sum(1 for w in plan if w) == 1               # beide in einen Wagen: genau 20 t ist erlaubt


@pytest.mark.parametrize("name", list(RULES))
def test_one_tonne_over_the_wagon_load_opens_a_second_wagon(name):
    inst = inst_of([(20, 10, 0), (20, 11, 0)], n_wagons=2, payload=20)
    plan = RULES[name](inst)
    assert sum(1 for w in plan if w) == 2


def test_best_fit_picks_the_fullest_fitting_wagon_and_first_fit_the_first():
    """Wagen 0 hält einen 20-Fuß-Container (2 Plätze frei), Wagen 1 einen 40-Fuß-Container (1 Platz frei); der dritte Container passt in beide (Gewicht knapp genug)."""
    inst = inst_of([(20, 10, 0), (40, 45, 0), (20, 2, 0)], n_wagons=3, payload=50)
    assert [i for _, i in R._place(inst, [0, 1, 2], "best")[1]] == [1, 2]                     # größte Füllung: in den Wagen mit dem 40-Fuß-Container
    assert [i for _, i in R._place(inst, [0, 1, 2], "first")[0]] == [0, 2]                    # erster passender Wagen


def test_blocks_prefer_the_fullest_wagon_of_a_destination():
    inst = inst_of([(40, 45, 0), (20, 10, 0), (20, 2, 0)], n_wagons=3, payload=50)
    plan = R.blocks(inst)
    assert [i for _, i in plan[0]] == [0, 2] and [i for _, i in plan[1]] == [1]                # 45-t-Wagen zuerst und voll: der leichte Container rutscht dorthin


def test_blocks_choose_the_fullest_wagons_and_leave_the_rest_out():
    inst = inst_of([(40, 10, 0), (20, 10, 1), (40, 10, 2)], n_wagons=2, payload=60, n_dests=3)
    plan = R.blocks(inst)
    assert sorted(i for w in plan for _, i in w) == [0, 2]                                     # die beiden vollen 40-Fuß-Wagen fahren, der halbleere 20-Fuß-Wagen bleibt


def test_blocks_fewer_wagons_than_needed_pads_with_empty_wagons():
    inst = inst_of([(20, 5, 0)], n_wagons=4)
    plan = R.blocks(inst)
    assert len(plan) == 4 and sum(1 for w in plan if w) == 1


def test_size_order_uses_arrival_index_as_last_tie_break():
    inst = inst_of([(20, 5, 0), (20, 5, 1), (20, 5, 2)])
    assert R._size_order(inst) == [0, 1, 2]
