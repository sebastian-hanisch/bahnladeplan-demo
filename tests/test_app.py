"""AppTest: Skelett und Footer, jedes Preset, Permalink, alle Regler an Min und Max, Kennzahlen im 2 x 2-Raster, Stichprobe und Kurve auf Knopfdruck, Urteil in allen Zuständen,
Exakt-Tab, Vergleichstabelle, PDF, Texte."""

import pathlib

import pytest
from streamlit.proto.Metric_pb2 import Metric as MetricProto
from streamlit.testing.v1 import AppTest

import bahn_constants as C
import bahn_evaluation as E
import bahn_exact as X
import bahn_rules as R
from bahn_evaluation import Verdict
from bahn_presets import SETTING_SPECS

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")
FOOTER = (
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Hafenlogistik optimieren](https://sebastianhanisch.net/hafenlogistik-optimierung.html)."
)
F_, D_, B_, X_ = C.STRAT_FIFO, C.STRAT_FFD, C.STRAT_BLOCKS, C.STRAT_EXACT


def fresh(**query):
    at = AppTest.from_file(APP, default_timeout=240)
    for k, v in query.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def set_and_run(at, **values):
    for key, value in values.items():
        (at.number_input if key.endswith("_input") else at.slider)(key=key).set_value(value)
    at.run()
    assert not at.exception, at.exception
    return at


def main_metrics(at):
    return [(m.label, m.value, m.delta) for m in at.metric[:4]]


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception, at.exception
    return at


@pytest.fixture
def clean_cache():
    """Die App cached Szenarien prozessweit: Tests mit ersetztem Löser dürfen weder fremde Ergebnisse sehen noch eigene hinterlassen."""
    import streamlit as st
    st.cache_data.clear()
    yield
    st.cache_data.clear()


@pytest.fixture
def fast_curve(monkeypatch):
    """Stichprobe und Kurve mit wenigen Tagen und kurzem Limit: prüft den Ablauf der App, nicht die Zahlen (die prüfen test_evaluation und test_preset_stories). Spart auf der CI Minuten."""
    real_sample, real_curve = E.sample, E.curve_over_dests
    monkeypatch.setattr(E, "sample", lambda *a, **k: real_sample(*a, n_lists=6, exact_limit=1, **k))
    monkeypatch.setattr(E, "curve_over_dests", lambda *a, **k: real_curve(*a, n_lists=3, points=(1, 4, 8), exact_limit=1, **k))


SMALL = dict(n_wagons_slider=8, n_dest_slider=3)


# ---------------------------------------------------------------------------------------------------
# Skelett
# ---------------------------------------------------------------------------------------------------
def test_skeleton_and_footer():
    at = fresh()
    assert [h.value for h in at.sidebar.header] == ["⚙️ Einstellungen"]                # genau EIN Header
    assert len(at.title) == 1 and "Bahn-Ladeplan" in at.title[0].value
    assert any(v.value.startswith("## 🎯") for v in at.markdown)
    assert [s.value for s in at.subheader] == ["📐 Was kostet die Zielreinheit?"]
    assert [e.label for e in at.expander] == ["🔧 Wie wir das erreichen – vollständiger Methodenvergleich", "Wie funktioniert diese Demo?", "📐 Mathematische Formulierung"]
    assert any(c.value == FOOTER for c in at.caption)
    presets = [b.label for b in at.button if b.label in C.PRESETS]
    assert presets == list(C.PRESETS) and len(presets) == 5 and all(len(n) <= 16 for n in presets)


def test_main_metrics_are_2x2_with_the_four_strategies_and_signed_deltas():
    at = fresh()
    assert [m[0] for m in main_metrics(at)] == [C.STRATEGY_LABELS[k] for k in C.STRATEGY_KEYS]
    assert [m[1] for m in main_metrics(at)] == ["46", "47", "48", "48"]
    assert [m[2] for m in main_metrics(at)] == ["", "+1", "+2", "+2"]
    colors = [m.proto.color for m in at.metric[:4]]
    assert colors[1:] == [MetricProto.GREEN] * 3                                          # mehr geladen = besser = grün
    assert all(len(m[0]) <= 24 for m in main_metrics(at))


def test_main_message_states_fill_gain_in_wagons_and_price_of_purity():
    at = fresh()
    msg = [i.value for i in at.info if "Reihenfolge lädt" in i.value][0]
    assert "**46** von 48 Plätzen (96 %)" in msg and "Exakt **48** (100 %)" in msg and "**2 TEU mehr**, das sind 0.7 Wagen" in msg
    assert "Die Zielreinheit kostet hier nichts" in msg
    assert len(at.get("plotly_chart")) >= 7                                             # 2 im Zug-Blick + 4 im Methodenvergleich + Vergleich
    assert any("ein breites Rechteck ist ein 40-Fuß-Container" in c.value and "1 blau" in c.value and "4 violett" in c.value for c in at.caption)


def test_price_of_purity_message_appears_when_it_costs_something():
    at = click(fresh(), "Viele Ziele")
    msg = [i.value for i in at.info if "Reihenfolge lädt" in i.value][0]
    assert "Gemischte Wagen ließen höchstens" in msg and "die Zielreinheit kostet" in msg


def test_core_section_metrics_show_places_offer_and_price():
    at = fresh()
    assert [(m.label, m.value) for m in at.metric[4:7]] == [("Plätze im Zug", "48"), ("Angebot", "58 TEU"), ("Preis der Zielreinheit", "0 TEU")]


# ---------------------------------------------------------------------------------------------------
# Presets, Permalink
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_loads_within_widget_bounds_and_shows_its_story(name):
    at = fresh()
    click(at, name)
    p = C.PRESETS[name]
    assert at.slider(key="n_dest_slider").value == p["n_dests"] and at.slider(key="offer_slider").value == p["offer_pct"] and at.number_input(key="seed_input").value == p["seed"]
    for state_key, spec in SETTING_SPECS.items():
        if spec.lo is not None:
            value = at.session_state[state_key]
            assert spec.lo <= value <= spec.hi and (spec.step in (None, 1) or (value - spec.lo) % spec.step == 0)
    m = {m[0]: m[1] for m in main_metrics(at)}
    fifo, ffd, blocks, exact = (int(m[C.STRATEGY_LABELS[k]].lstrip("≥ ").split()[0]) for k in C.STRATEGY_KEYS)
    if name == "Locker":
        assert max(fifo, ffd, blocks, exact) - min(fifo, ffd, blocks, exact) <= 1
    elif name in ("Üblich", "Viele Ziele"):
        assert blocks - fifo >= 2 and exact >= blocks
    elif name == "Schwer":
        assert exact > blocks and blocks > fifo
    else:
        assert blocks - fifo >= 2 and exact >= blocks


def test_permalink_is_clamped_snapped_and_ignores_garbage():
    at = fresh(of="123", s4="47", vw="junk", nw="abc", pl="99", nd="0")
    assert at.slider(key="offer_slider").value == 120 and at.slider(key="share40_slider").value == 50
    assert at.radio(key="view_radio").value == C.VIEW_DEFAULT and at.slider(key="n_wagons_slider").value == C.N_WAGONS_DEFAULT
    assert at.slider(key="payload_slider").value == C.PAYLOAD_RANGE[1] and at.slider(key="n_dest_slider").value == C.N_DESTS_RANGE[0]


def test_permalink_roundtrip_reflects_settings():
    at = fresh(nw="10", nd="6", of="100", s4="20", pl="50", seed="11", vw="blocks")
    assert at.slider(key="n_wagons_slider").value == 10 and at.slider(key="n_dest_slider").value == 6 and at.slider(key="offer_slider").value == 100
    assert at.slider(key="share40_slider").value == 20 and at.slider(key="payload_slider").value == 50 and at.number_input(key="seed_input").value == 11
    assert at.radio(key="view_radio").value == "blocks"
    assert at.query_params["nd"] in ("6", ["6"]) and at.query_params["pl"] in ("50", ["50"])


def test_seed_button_uses_the_random_draw_unchanged(monkeypatch):
    import random
    monkeypatch.setattr(random, "randint", lambda lo, hi: hi)
    at = click(fresh(), "🎲 Neuer Tag")
    assert at.number_input(key="seed_input").value == C.SEED_RANGE[1]


def test_seed_button_changes_only_the_seed():
    at = fresh()
    before = {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"}
    click(at, "🎲 Neuer Tag")
    assert {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"} == before
    assert C.SEED_RANGE[0] <= at.number_input(key="seed_input").value <= C.SEED_RANGE[1]


# ---------------------------------------------------------------------------------------------------
# Regler an den Grenzen
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key,value", [
    ("n_wagons_slider", 8), ("n_wagons_slider", 30), ("n_dest_slider", 1), ("n_dest_slider", 10), ("offer_slider", 80), ("offer_slider", 150), ("share40_slider", 0),
    ("share40_slider", 100), ("payload_slider", 40), ("payload_slider", 70), ("seed_input", 0), ("seed_input", 9999),
])
def test_every_slider_at_min_and_max(key, value):
    at = set_and_run(fresh(), **{key: value})
    assert len(at.get("plotly_chart")) >= 2 and [m[0] for m in main_metrics(at)] == [C.STRATEGY_LABELS[k] for k in C.STRATEGY_KEYS]


def test_longest_and_shortest_trains_and_extreme_mixes():
    big = set_and_run(fresh(), n_wagons_slider=30, n_dest_slider=10, offer_slider=150, payload_slider=40)
    assert all(m[1] != "" for m in main_metrics(big))
    small = set_and_run(fresh(), n_wagons_slider=8, n_dest_slider=1, offer_slider=80, share40_slider=0)
    values = [int(m[1].lstrip("≥ ")) for m in main_metrics(small)]
    assert max(values) - min(values) <= 1                                                # ein Ziel und viel Platz: alle Verfahren laden (fast) gleich viel
    forty = set_and_run(fresh(), share40_slider=100)
    assert all(int(m[1].lstrip("≥ ")) <= 48 for m in main_metrics(forty))


def test_exact_unproven_is_shown_with_a_lower_bound_sign(monkeypatch, clean_cache):
    def unproven(inst, limit=None, **k):
        plan = R.blocks(inst)
        v = R.evaluate(inst, plan).loaded
        return X.ExactResult("feasible", plan, v, v + 1, "Regel", 1.0)

    monkeypatch.setattr(X, "solve_exact", unproven)
    at = fresh()
    blocks = main_metrics(at)[2][1]
    assert main_metrics(at)[3][1] == f"≥ {blocks}"
    assert f"zwischen {blocks} und {int(blocks) + 1}" in at.metric[3].help
    assert any("Exakt **mindestens" in i.value for i in at.info)


# ---------------------------------------------------------------------------------------------------
# Stichprobe und Kurve auf Knopfdruck
# ---------------------------------------------------------------------------------------------------
def test_before_the_button_nothing_is_computed_and_after_it_everything_is_shown():
    at = set_and_run(fresh(), **SMALL)
    assert any("Noch nichts berechnet" in i.value for i in at.info)
    click(at, "📊 Stichprobe und Kurve berechnen")
    assert not any("Noch nichts berechnet" in i.value for i in at.info)
    texts = [x.value for x in list(at.success) + list(at.warning) + list(at.info)]
    assert any("Wagenblöcke gegen Reihenfolge" in t for t in texts) and any("Exakt gegen Reihenfolge" in t for t in texts) and any("Exakt gegen Wagenblöcke" in t for t in texts)
    assert len(at.get("plotly_chart")) >= 7 + 3                                        # dazu Verteilung, Gewinn, Kurve
    caps = " ".join(c.value for c in at.caption)
    assert "Basis: 20 Tage (Seeds 0-19" in caps and "Basis: 7 Zielzahlen × 8 Tage (Seeds 0-7)" in caps and "untere Schranke" in caps


def test_stale_curve_after_a_setting_change_is_flagged_and_not_shown(fast_curve):
    at = set_and_run(fresh(), **SMALL)
    click(at, "📊 Stichprobe und Kurve berechnen")
    set_and_run(at, offer_slider=100)
    assert any("bezogen sich auf andere Einstellungen" in i.value for i in at.info)
    assert not [s for s in list(at.success) + list(at.warning) if "Wagenblöcke gegen Reihenfolge" in s.value]
    set_and_run(at, offer_slider=120)                                                    # zurück: das gespeicherte Ergebnis passt wieder
    assert [s for s in list(at.success) + list(at.info) if "Wagenblöcke gegen Reihenfolge" in s.value]


def test_the_seed_does_not_invalidate_the_sample_but_the_payload_does(fast_curve):
    at = set_and_run(fresh(), **SMALL)
    click(at, "📊 Stichprobe und Kurve berechnen")
    set_and_run(at, seed_input=77)
    assert [s for s in list(at.success) + list(at.info) if "Wagenblöcke gegen Reihenfolge" in s.value]
    set_and_run(at, payload_slider=45)
    assert any("bezogen sich auf andere Einstellungen" in i.value for i in at.info)


def _fake_verdict(monkeypatch, kind, pct):
    monkeypatch.setattr(E, "verdict", lambda res, key, ref=C.BASELINE: Verdict(kind, 2.0 if kind == "better" else -2.0, 0.5, pct, 20, 0.25))


@pytest.mark.parametrize("kind,pct,expected", [
    ("better", 40.0, "im Mittel **40 % mehr** geladene TEU (2.0 je Tag, Standardfehler 0.50)."),
    ("better", None, "im Mittel **2.0 mehr** geladene TEU (2.0 je Tag, Standardfehler 0.50)."),
    ("worse", -25.0, "im Mittel **25 % weniger** geladene TEU (-2.0 je Tag, Standardfehler 0.50)."),
    ("worse", None, "im Mittel **2.0 weniger** geladene TEU (-2.0 je Tag, Standardfehler 0.50)."),
])
def test_verdict_sentences_in_the_four_variants(monkeypatch, clean_cache, fast_curve, kind, pct, expected):
    _fake_verdict(monkeypatch, kind, pct)
    at = set_and_run(fresh(), **SMALL)
    click(at, "📊 Stichprobe und Kurve berechnen")
    texts = [x.value for x in (at.success if kind == "better" else at.warning) if "geladene TEU" in x.value and "im Mittel" in x.value]
    assert len(texts) == 3 and all(expected in t for t in texts)
    assert all(t.count("(") == t.count(")") for t in texts)


def test_verdict_unclear_and_none(monkeypatch, clean_cache, fast_curve):
    _fake_verdict(monkeypatch, "unclear", 1.0)
    at = set_and_run(fresh(), **SMALL)
    click(at, "📊 Stichprobe und Kurve berechnen")
    us = [i.value for i in at.info if "Kein klarer Unterschied" in i.value]
    assert len(us) == 3 and all("Rauschens" in u for u in us)
    _fake_verdict(monkeypatch, "none", None)
    at2 = set_and_run(fresh(), **SMALL)
    click(at2, "📊 Stichprobe und Kurve berechnen")
    assert len([i for i in at2.info if "In keinem Tag sind beide Verfahren zulässig" in i.value]) == 3


def test_real_verdicts_blocks_beat_the_everyday_rule(fast_curve):
    at = set_and_run(fresh(), n_wagons_slider=10, n_dest_slider=6)
    click(at, "📊 Stichprobe und Kurve berechnen")
    assert [s for s in at.success if "Wagenblöcke gegen Reihenfolge" in s.value and "mehr" in s.value]


# ---------------------------------------------------------------------------------------------------
# Methodenvergleich
# ---------------------------------------------------------------------------------------------------
def test_comparison_table_lists_all_strategies_and_the_mixed_bound_row():
    at = fresh()
    df = at.dataframe[0].value
    assert list(df["Verfahren"]) == [C.STRATEGY_LABELS[k] for k in C.STRATEGY_KEYS] + ["Ohne Zielreinheit (Schranke)"]
    assert list(df["Geladene TEU"])[:4] == ["46", "47", "48", "48"] and list(df["Differenz zur Reihenfolge"])[:4] == [0, 1, 2, 2] and list(df["Bleiben stehen (TEU)"])[:4] == [12, 11, 10, 10]
    assert df.loc[3, "zulässig"] == "ja" and df.loc[4, "zulässig"].startswith("Vergleichswert") and df.loc[4, "Geladene TEU"].startswith("≤ ")


def test_exact_tab_long_run_button_and_stale_key():
    at = fresh()
    assert any("Live mit 4 s Limit" in c.value for c in at.caption)
    click(at, f"🧮 Mit {C.EXACT_LONG_LIMIT_SECONDS} s nachrechnen")
    assert any("Bewiesen optimal" in s.value for s in at.success)
    set_and_run(at, seed_input=5)
    assert any("zuletzt nachgerechnete Ergebnis bezog sich auf ein anderes Szenario" in i.value for i in at.info)


# ---------------------------------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------------------------------
def test_pdf_download_button_is_in_the_main_view_and_survives_edge_scenarios():
    at = fresh()
    buttons = at.get("download_button")
    assert len(buttons) == 1 and "PDF" in buttons[0].proto.label and buttons[0].proto.url.endswith(".pdf")
    assert not at.sidebar.get("download_button")
    for values in (dict(offer_slider=80), dict(share40_slider=100), dict(n_dest_slider=1, n_wagons_slider=8), dict(n_wagons_slider=30, n_dest_slider=10)):
        assert len(set_and_run(at, **values).get("download_button")) == 1


def test_pdf_is_built_from_the_curve_only_when_it_matches_the_settings(monkeypatch, fast_curve):
    import bahn_pdf_export as PDF
    seen = []
    real = PDF.generate_bahn_pdf
    monkeypatch.setattr(PDF, "generate_bahn_pdf", lambda *a, **k: seen.append((k.get("sample"), k.get("curve"))) or real(*a, **k))
    at = set_and_run(fresh(), **SMALL)
    assert seen[-1] == (None, None)                                                     # noch nichts berechnet
    click(at, "📊 Stichprobe und Kurve berechnen")
    assert seen[-1][0] is not None and seen[-1][1] is not None
    set_and_run(at, offer_slider=100)                                                    # andere Einstellung: die alte Kurve gehört nicht ins PDF
    assert seen[-1] == (None, None)


# ---------------------------------------------------------------------------------------------------
# Texte
# ---------------------------------------------------------------------------------------------------
def test_texts_mention_limits_and_no_dead_file_links():
    at = fresh()
    md = "\n".join(m.value for m in at.markdown)
    assert "Grenzen dieses Modells" in md and "Größenordnungen aus einer Simulation" in md and "keine Zeitachse" in md
    assert "Wagenblöcke ist meine Konstruktion" in md and "Zielreinheit ist eine Modellannahme" in md
    assert "](" not in md.replace("https://sebastianhanisch.net", "")
    for word in ("Zielreinheit", "Wagenblöcke", "Mathematische Formulierung", "Zielterminal", "Platz"):
        assert word in md
    for ascii_form in ("Groesse", "Zielterminals fahren", "Plaetze", "Gewaehlt"):
        assert ascii_form not in md
