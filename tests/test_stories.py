"""Kriterien der Preset-Geschichten (bahn_stories.py) mit KÜNSTLICHEN Werten: jedes Kriterium kippt einzeln an seiner Schwelle. (Abnahmen über echte Daten prüfen Schwellen nicht;
die stehen in test_preset_stories.py.) Schnell, ohne Löser."""

import pytest

import bahn_constants as C
import bahn_stories as ST
from bahn_evaluation import ListResult

F_, D_, B_, X_ = C.STRAT_FIFO, C.STRAT_FFD, C.STRAT_BLOCKS, C.STRAT_EXACT
NAMES = list(C.PRESETS)


def fake(loaded, valid=None, proven=True, mixed=48, offered=58, n=10):
    """n gleiche Tage. loaded: {Verfahren: TEU}; valid: {Verfahren: bool} (Standard alle zulässig)."""
    v = {k: True for k in C.STRATEGY_KEYS}
    v.update(valid or {})
    return tuple(ListResult(i, offered, dict(loaded), v, proven, "optimal" if proven else "feasible", mixed) for i in range(n))


def failing(name, results):
    return [i for i, (ok, _) in enumerate(ST.criteria(name, results)) if not ok]


BASE = {
    "Locker": (dict(fifo=39, ffd=39, blocks=39, exact=39), dict(mixed=39, offered=39)),
    "Üblich": (dict(fifo=45, ffd=46, blocks=47, exact=47), dict(mixed=48, offered=58)),
    "Viele Ziele": (dict(fifo=42, ffd=43, blocks=45, exact=45), dict(mixed=48, offered=58)),
    "Schwer": (dict(fifo=42, ffd=44, blocks=46, exact=47), dict(mixed=48, offered=58)),
    "Ganz lang": (dict(fifo=42, ffd=43, blocks=45, exact=45), dict(mixed=48, offered=58, proven=False)),
}


def base(name, **override):
    loaded, extra = BASE[name]
    loaded = {C.STRATEGY_KEYS[i]: v for i, v in enumerate(loaded.values())}
    loaded.update({k: v for k, v in override.items() if k in C.STRATEGY_KEYS})
    kw = dict(extra, **{k: v for k, v in override.items() if k not in C.STRATEGY_KEYS})
    return fake(loaded, **kw)


@pytest.mark.parametrize("name", NAMES)
def test_the_artificial_base_case_satisfies_every_criterion_and_the_single_day_story(name):
    assert failing(name, base(name)) == []
    assert ST.holds(name, base(name)[0])


@pytest.mark.parametrize("name,override,expected", [
    # Locker: [alle zulässig, Reihenfolge >= 95 % des Angebots, Spannweite <= 0,5]
    ("Locker", dict(fifo=37), [1, 2]), ("Locker", dict(fifo=38.4), [2]), ("Locker", dict(offered=42), [1]),
    # Üblich: [Blöcke - Reihenfolge >= 1,5, Exakt = Blöcke an >= 90 %, Blöcke >= 95 % der Plätze]
    ("Üblich", dict(fifo=46), [0]), ("Üblich", dict(fifo=45.5), []), ("Üblich", dict(blocks=45, exact=45), [0]), ("Üblich", dict(blocks=44, exact=44), [0, 2]), ("Üblich", dict(exact=48), [1]),
    # Viele Ziele: [Blöcke - Reihenfolge >= 2, Preis >= 1]
    ("Viele Ziele", dict(fifo=44), [0]), ("Viele Ziele", dict(fifo=43), []), ("Viele Ziele", dict(mixed=45), [1]), ("Viele Ziele", dict(mixed=46), []),
    # Schwer: [Exakt - Blöcke >= 0,3, Anteil >= 25 %]
    ("Schwer", dict(exact=46), [0, 1]), ("Schwer", dict(blocks=46.7, exact=47), [0]),
    # Ganz lang: [nicht bewiesen an >= 30 %, Preis >= 1,5]
    ("Ganz lang", dict(proven=True), [0]), ("Ganz lang", dict(mixed=46), [1]), ("Ganz lang", dict(mixed=46.5), []),
])
def test_each_criterion_flips_at_its_threshold(name, override, expected):
    assert failing(name, base(name, **override)) == expected, (name, override)


def test_locker_needs_all_methods_valid_on_every_day():
    r = list(base("Locker"))
    r[3] = ListResult(3, 39, r[3].loaded, dict(r[3].valid, **{D_: False}), True, "optimal", 39)
    assert failing("Locker", tuple(r)) == [0]


def test_locker_spread_is_inclusive_at_half_a_teu():
    def with_spread(k):                                               # k von 10 Tagen laden mit Reihenfolge 38 statt 39: Mittel 39 - k/10, Spannweite k/10
        rows = [ListResult(i, 39, {F_: 38 if i < k else 39, D_: 39, B_: 39, X_: 39}, {q: True for q in C.STRATEGY_KEYS}, True, "optimal", 39) for i in range(10)]
        return tuple(rows)
    assert failing("Locker", with_spread(5)) == [] and failing("Locker", with_spread(6)) == [2]


def test_ueblich_exact_equals_blocks_share_flips_at_90_percent():
    def with_equal(k):
        rows = [ListResult(i, 58, {F_: 45, D_: 46, B_: 47, X_: 47 if i < k else 48}, {q: True for q in C.STRATEGY_KEYS}, True, "optimal", 48) for i in range(10)]
        return tuple(rows)
    assert failing("Üblich", with_equal(9)) == [] and failing("Üblich", with_equal(8)) == [1]


def test_schwer_share_of_days_with_more_than_blocks_flips_at_25_percent():
    def with_gain(k):                                                 # k von 20 Tagen +2, die übrigen 0: Mittel k/10 >= 0,3 erst ab k=3, Anteil >= 25 % erst ab k=5
        rows = [ListResult(i, 58, {F_: 42, D_: 44, B_: 46, X_: 48 if i < k else 46}, {q: True for q in C.STRATEGY_KEYS}, True, "optimal", 48) for i in range(20)]
        return tuple(rows)
    assert failing("Schwer", with_gain(5)) == [] and failing("Schwer", with_gain(4)) == [1]


def test_ganz_lang_unproven_share_flips_at_30_percent():
    def with_unproven(k):
        return tuple(ListResult(i, 58, {F_: 42, D_: 43, B_: 45, X_: 45}, {q: True for q in C.STRATEGY_KEYS}, i >= k, "optimal" if i >= k else "feasible", 48) for i in range(10))
    assert failing("Ganz lang", with_unproven(3)) == [] and failing("Ganz lang", with_unproven(2)) == [0]


def test_a_method_without_any_valid_plan_fails_its_criterion_instead_of_counting_as_zero():
    assert 0 in failing("Üblich", base("Üblich", valid={B_: False}))
    assert 0 in failing("Schwer", base("Schwer", valid={X_: False}))
    assert failing("Viele Ziele", base("Viele Ziele", valid={X_: False})) != []


@pytest.mark.parametrize("name,override,expected", [
    ("Locker", dict(fifo=37), False), ("Locker", dict(fifo=38), True), ("Locker", dict(exact=41), False),
    ("Üblich", dict(fifo=46), False), ("Üblich", dict(fifo=45), True), ("Üblich", dict(exact=48), False),
    ("Viele Ziele", dict(fifo=44), False), ("Viele Ziele", dict(fifo=43), True), ("Viele Ziele", dict(mixed=45), False), ("Viele Ziele", dict(mixed=46), True),
    ("Schwer", dict(exact=46), False), ("Schwer", dict(exact=47), True),
    ("Ganz lang", dict(mixed=46), False), ("Ganz lang", dict(mixed=47), True),
])
def test_single_day_story_flips_at_its_threshold(name, override, expected):
    assert ST.holds(name, base(name, **override)[0]) is expected, (name, override)


@pytest.mark.parametrize("name,who", [("Locker", D_), ("Üblich", F_), ("Üblich", B_), ("Üblich", X_), ("Viele Ziele", X_), ("Schwer", B_), ("Schwer", X_), ("Ganz lang", X_)])
def test_an_invalid_plan_is_never_a_holding_story(name, who):
    assert not ST.holds(name, base(name, valid={who: False})[0])


def test_unknown_preset_name_raises():
    with pytest.raises(KeyError):
        ST.criteria("Unbekannt", base("Locker"))
    with pytest.raises(KeyError):
        ST.holds("Unbekannt", base("Locker")[0])


def test_key_values_lists_the_typical_indicators_of_the_preset():
    assert ST.key_values("Schwer", base("Schwer")) == {B_: 46.0, X_: 47.0} and ST.key_values("Locker", base("Locker")) == {}
    assert {n for n, _ in ST.TYPICAL} == set(NAMES) - {"Locker"}


def test_locker_thresholds_are_inclusive_at_95_percent_of_the_offer():
    even = dict(fifo=38, ffd=38, blocks=38, exact=38)
    assert failing("Locker", fake(even, mixed=38, offered=40)) == [] and ST.holds("Locker", fake(even, mixed=38, offered=40)[0])           # genau 95 %
    low = dict(fifo=37, ffd=37, blocks=37, exact=37)
    assert failing("Locker", fake(low, mixed=37, offered=40)) == [1] and not ST.holds("Locker", fake(low, mixed=37, offered=40)[0])


def test_schwer_mean_gain_is_inclusive_at_three_tenths():
    def with_gain(k):
        return tuple(ListResult(i, 58, {F_: 42, D_: 44, B_: 46, X_: 47 if i < k else 46}, {q: True for q in C.STRATEGY_KEYS}, True, "optimal", 48) for i in range(10))
    assert failing("Schwer", with_gain(3)) == []                                                # Mittel 0,3 (inklusive) und 30 % der Tage über 25 %
    assert failing("Schwer", with_gain(2)) == [0, 1]                                            # Mittel 0,2 und 20 % der Tage
