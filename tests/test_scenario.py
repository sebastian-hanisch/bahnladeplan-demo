import pytest

import bahn_constants as C
import bahn_scenario as SC
from bahn_scenario import teu
from helpers import random_instance


def test_make_instance_is_deterministic_and_seed_dependent():
    a = SC.make_instance(16, 4, 120, 50, 60, 31)
    assert a == SC.make_instance(16, 4, 120, 50, 60, 31)
    assert a != SC.make_instance(16, 4, 120, 50, 60, 32)


def test_offer_is_the_smallest_container_list_reaching_the_percentage_of_capacity():
    for offer in (80, 100, 120, 150):
        for seed in range(6):
            inst = SC.make_instance(16, 4, offer, 50, 60, seed)
            cap = SC.capacity(inst)
            assert SC.offered(inst) * 100 >= offer * cap
            last = teu(inst.boxes[-1])
            assert (SC.offered(inst) - last) * 100 < offer * cap                       # ohne den letzten Container wäre es zu wenig: kleinste Liste


def test_fixed_values_for_the_default_scenario():
    inst = SC.make_instance(16, 4, 120, 50, 60, 35)
    assert SC.capacity(inst) == 48 and SC.offered(inst) == 58 and len(inst.boxes) == 40 and SC.upper_bound(inst) == 48
    assert SC.upper_bound(SC.make_instance(16, 4, 80, 50, 60, 35)) == SC.offered(SC.make_instance(16, 4, 80, 50, 60, 35))     # unter 100 %: das Angebot begrenzt


def test_weights_lengths_and_destinations_are_in_range():
    for seed in range(20):
        inst = random_instance(seed)
        for length, weight, dest in inst.boxes:
            lo, hi = C.WEIGHT_40 if length == 40 else C.WEIGHT_20
            assert length in (20, 40) and lo <= weight <= hi and 0 <= dest < inst.n_dests


def test_share40_extremes():
    assert all(b[0] == 20 for b in SC.make_instance(16, 4, 120, 0, 60, 3).boxes)
    assert all(b[0] == 40 for b in SC.make_instance(16, 4, 120, 100, 60, 3).boxes)
    share = sum(b[0] == 40 for b in SC.make_instance(30, 4, 150, 50, 60, 3).boxes) / len(SC.make_instance(30, 4, 150, 50, 60, 3).boxes)
    assert 0.3 < share < 0.7


def test_single_destination_uses_destination_zero_only():
    assert {b[2] for b in SC.make_instance(16, 1, 120, 50, 60, 5).boxes} == {0}


def test_all_destinations_appear_in_a_large_instance():
    assert {b[2] for b in SC.make_instance(30, 10, 150, 50, 60, 5).boxes} == set(range(10))


@pytest.mark.parametrize("args", [(0, 4, 120, 50, 60, 1), (16, 0, 120, 50, 60, 1), (16, 4, 120, 50, 0, 1), (16, 4, 0, 50, 60, 1), (16, 4, 120, -1, 60, 1), (16, 4, 120, 101, 60, 1)])
def test_make_instance_rejects_invalid_values(args):
    with pytest.raises(ValueError):
        SC.make_instance(*args)


def test_every_slider_corner_gives_a_valid_instance():
    for w in (C.N_WAGONS_RANGE[0], C.N_WAGONS_RANGE[1]):
        for d in (C.N_DESTS_RANGE[0], C.N_DESTS_RANGE[1]):
            for o in (C.OFFER_PCT_RANGE[0], C.OFFER_PCT_RANGE[1]):
                for s in (C.SHARE40_PCT_RANGE[0], C.SHARE40_PCT_RANGE[1]):
                    inst = SC.make_instance(w, d, o, s, C.PAYLOAD_RANGE[0], 7)
                    assert len(inst.boxes) >= 1 and SC.offered(inst) * 100 >= o * SC.capacity(inst)


def test_custom_instance_validates():
    ok = SC.custom_instance(2, 2, 60, [(20, 10, 0), (40, 20, 1)])
    assert ok.boxes == ((20, 10, 0), (40, 20, 1)) and SC.offered(ok) == 3 and SC.capacity(ok) == 6
    for bad in ([], [(30, 10, 0)], [(20, 0, 0)], [(20, 10.5, 0)], [(20, 10, 5)], [(20, 10, -1)]):
        with pytest.raises(ValueError):
            SC.custom_instance(2, 2, 60, bad)
    with pytest.raises(ValueError):
        SC.custom_instance(0, 2, 60, [(20, 10, 0)])


def test_prefix_property_more_offer_appends_containers():
    small = SC.make_instance(16, 4, 100, 50, 60, 9).boxes
    big = SC.make_instance(16, 4, 150, 50, 60, 9).boxes
    assert big[:len(small)] == small


def test_share40_zero_and_hundred_are_exact_over_many_seeds():
    """Die Grenze 'kleiner als' zählt: bei 0 % kommt nie ein 40-Fuß-Container, bei 100 % nie ein 20-Fuß-Container vor (auch nicht durch Zufall an der Grenze)."""
    for seed in range(40):
        assert all(b[0] == 20 for b in SC.make_instance(16, 4, 150, 0, 60, seed).boxes)
        assert all(b[0] == 40 for b in SC.make_instance(16, 4, 150, 100, 60, seed).boxes)


def test_custom_instance_boundaries_of_length_and_destination():
    for bad in ([(45, 10, 0)], [(60, 10, 0)], [(20, 10, 2)]):                                 # Ziel 2 gibt es bei n_dests=2 nicht (0 und 1)
        with pytest.raises(ValueError):
            SC.custom_instance(2, 2, 60, bad)
    assert SC.custom_instance(2, 2, 60, [(20, 1, 1)]).boxes == ((20, 1, 1),)                  # Gewicht 1 und Ziel n-1 sind erlaubt
