"""Jedes Preset erzählt eine Geschichte (Abnahmekriterien in bahn_stories.py). Hier wird geprüft, dass sie trägt:

1. an dem EINEN Tag, den das Preset zeigt (sonst zeigt das Preset das Gegenteil seines Hilfetexts),
2. im MITTEL über 20 andere Tage (sonst ist das Preset ein Einzelfall, ausgesucht nach dem schönsten Seed),
3. dass der gewählte Tag typisch ist: bei jeder Kennzahl zwischen dem 10. und 90. Perzentil der Tage.

(Die Schwellen selbst prüft test_stories.py mit künstlichen Werten.) Zeitlimits: Aussagen über Exakt sind Aussagen über ein bewiesenes Optimum; auf einem langsamen Rechner (CI, wenige Kerne)
beweist der Löser in 2 s weniger als lokal. Darum rechnet der gezeigte Tag großzügig (Ende, sobald bewiesen) und die Grundgesamtheit mit dem App-Limit von 2 s, nur "Schwer" (Exakt gegen
Wagenblöcke) mit 10 s; die Schwellen stehen mit Abstand."""

import pytest

import bahn_constants as C
import bahn_evaluation as E
import bahn_stories as ST

NAMES = list(C.PRESETS)
POP_LIMIT = {"Schwer": 10}
SHOWN_LIMIT = C.EXACT_LONG_LIMIT_SECONDS
_cache = {}


def _run(name, seed, limit):
    p = C.PRESETS[name]
    return E.run_list(p["n_wagons"], p["n_dests"], p["offer_pct"], p["share40_pct"], p["payload"], seed, limit)


def _population(name):
    if name not in _cache:
        _cache[name] = tuple(_run(name, s, POP_LIMIT.get(name, C.SAMPLE_LIMIT_SECONDS)) for s in range(C.SAMPLE_LISTS))
    return _cache[name]


# ---------------- 1. am gezeigten Tag ----------------
@pytest.mark.parametrize("name", NAMES)
def test_the_story_holds_on_the_day_the_preset_shows(name):
    r = _run(name, C.PRESETS[name]["seed"], SHOWN_LIMIT)
    assert ST.holds(name, r), (name, r)


def test_presets_share_one_day_number_and_only_change_what_the_story_needs():
    assert len({p["seed"] for p in C.PRESETS.values()}) == 1 and len({p["n_wagons"] for p in C.PRESETS.values()}) == 1
    assert [C.PRESETS[n]["n_dests"] for n in NAMES] == [4, 4, 8, 4, 10] and [C.PRESETS[n]["offer_pct"] for n in NAMES] == [80, 120, 120, 120, 120]
    assert C.PRESETS["Schwer"]["payload"] == 40 and C.PRESETS["Schwer"]["share40_pct"] == 30
    assert all(C.PRESETS[n]["payload"] == 60 and C.PRESETS[n]["share40_pct"] == 50 for n in NAMES if n != "Schwer")


# ---------------- 2. im Mittel der Grundgesamtheit ----------------
@pytest.mark.parametrize("name", NAMES)
def test_the_story_holds_on_average_over_many_days(name):
    failed = [text for ok, text in ST.criteria(name, _population(name)) if not ok]
    assert not failed, failed


def test_the_population_does_not_contain_the_preset_seed():
    assert C.PRESETS["Locker"]["seed"] not in range(C.SAMPLE_LISTS)                     # sonst wäre die Grundgesamtheit nicht unabhängig vom gezeigten Fall


# ---------------- 3. der gezeigte Tag ist typisch ----------------
def _pct(values, q):
    v = sorted(values)
    return v[int(q * (len(v) - 1))]


@pytest.mark.parametrize("name,key", ST.TYPICAL)
def test_the_shown_day_is_typical(name, key):
    pop = [r.loaded[key] for r in _population(name) if r.valid[key]]
    shown = _run(name, C.PRESETS[name]["seed"], SHOWN_LIMIT).loaded[key]
    assert _pct(pop, 0.1) <= shown <= _pct(pop, 0.9), (name, key, shown, sorted(pop))
