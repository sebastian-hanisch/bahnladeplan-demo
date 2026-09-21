import re

import pytest

import bahn_constants as C
import bahn_evaluation as E
import bahn_rules as R
import bahn_scenario as SC
from bahn_evaluation import ListResult, Outcome
from bahn_exact import ExactResult
from bahn_pdf_export import generate_bahn_pdf, loaded_text, pdf_text, short_name, verdict_text

F_, D_, B_, X_ = C.STRAT_FIFO, C.STRAT_FFD, C.STRAT_BLOCKS, C.STRAT_EXACT
_cache = {}


def _settings(name="Üblich", **override):
    p = dict(C.PRESETS[name])
    p.update(override)
    return p


def _pdf(name="Üblich", compress=False, sample=None, curve=None, **override):
    s = _settings(name, **override)
    key = (name, tuple(sorted(override.items())))
    if key not in _cache:
        inst = SC.make_instance(s["n_wagons"], s["n_dests"], s["offer_pct"], s["share40_pct"], s["payload"], s["seed"])
        outs = E.run_methods(inst, 2)
        _cache[key] = (inst, outs, max(E.mixed_bound(inst, 2)[0], outs[3].loaded))
    inst, outs, mixed = _cache[key]
    return generate_bahn_pdf(inst, outs, mixed, s, sample=sample, curve=curve, compress=compress), inst, outs, mixed, s


def _texts(data):
    """Alle Textstücke des (unkomprimierten) PDFs als Liste, Latin-1 gelesen, PDF-Escapes aufgelöst."""
    raw = re.findall(rb"\((.*?)\)\s*Tj", data)
    return [t.decode("latin-1").replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\") for t in raw]


def _after(text, label):
    return text[text.index(label) + 1]


def lr(seed, **kw):
    v = dict(fifo=44, ffd=45, blocks=47, exact=47, mixed=48)
    v.update(kw)
    return ListResult(seed, 58, {F_: v["fifo"], D_: v["ffd"], B_: v["blocks"], X_: v["exact"]}, {k: True for k in C.STRATEGY_KEYS}, True, "optimal", v["mixed"])


# ---------- Sonderzeichen: mit den GENAUEN Zeichen testen (fpdf2 stürzt bei "–" und "€" ab) ----------
EXPECTED = {"–": "-", "—": "-", "−": "-", "€": "EUR", "Σ": "Summe", "δ": "Delta", "≥": ">=", "≤": "<=", "→": "->", "≈": "ca.", "„": '"', "“": '"', "’": "'", "·": "-", "±": "+-",
            "⚠️": "(!)", "⚠": "(!)"}


@pytest.mark.parametrize("char,replacement", list(EXPECTED.items()))
def test_pdf_text_replaces_every_known_troublemaker_with_a_readable_equivalent(char, replacement):
    out = pdf_text(f"a{char}b")
    out.encode("latin-1")
    assert out == f"a{replacement}b"


def test_pdf_text_keeps_umlauts_and_times_sign_and_replaces_unknown():
    assert pdf_text("Füllgrad äöüß ÄÖÜ × 3") == "Füllgrad äöüß ÄÖÜ × 3"
    assert pdf_text("日本語").encode("latin-1") == b"???"
    assert "?" in pdf_text("🧮 Exakt")


def test_short_names_have_no_emoji_and_survive_latin_1():
    for key in C.STRATEGY_KEYS:
        assert pdf_text(short_name(key)) == short_name(key) and "<br>" not in short_name(key)
    assert short_name(B_) == "Wagenblöcke" and short_name(F_) == "Reihenfolge"


# ---------- Inhalt ----------
def test_pdf_is_a_valid_document_with_all_sections_without_sample():
    data, *_ = _pdf()
    assert data.startswith(b"%PDF") and data.endswith(b"%%EOF\n") and len(data) > 2000
    text = _texts(data)
    for needle in ["Bahn-Ladeplan: Wie voll wird der Zug?", "Szenario", "Zusammenfassung", "Verfahrensvergleich", "Hinweise zum Modell"]:
        assert needle in text, needle
    assert "Stichprobe und Urteil" not in text and "Geladene TEU über der Zahl der Zielterminals" not in text


def test_pdf_scenario_block_pairs_every_label_with_its_own_value():
    data, inst, outs, mixed, s = _pdf()
    text = _texts(data)
    assert _after(text, "Zug") == "16 Wagen zu je 3 Plätzen = 48 Plätze" and _after(text, "Zielterminals") == "4"
    assert _after(text, "Angebot") == f"{SC.offered(inst)} TEU (120 % der Kapazität eingestellt)"
    assert _after(text, "Anteil 40-Fuß") == "50 %" and _after(text, "Wagenlast") == "60 t" and _after(text, "Seed des Tages") == str(s["seed"]) and _after(text, "Container") == str(len(inst.boxes))


def test_pdf_scenario_follows_the_settings():
    data, inst, *_ = _pdf("Schwer", n_wagons=10, seed=9)
    text = _texts(data)
    assert _after(text, "Zug") == "10 Wagen zu je 3 Plätzen = 30 Plätze" and _after(text, "Wagenlast") == "40 t" and _after(text, "Anteil 40-Fuß") == "30 %" and _after(text, "Seed des Tages") == "9"


def test_pdf_summary_quotes_each_method_with_its_signed_difference():
    data, inst, outs, mixed, s = _pdf()
    text = _texts(data)
    ref = outs[0].loaded
    assert _after(text, "Reihenfolge") == f"{ref} TEU"
    for o in outs[1:]:
        assert _after(text, short_name(o.key)) == f"{loaded_text(o)} TEU ({o.loaded - ref:+d} gegen Reihenfolge)"


def test_pdf_states_the_gain_in_wagons_and_the_price_of_purity():
    data, inst, outs, mixed, s = _pdf("Viele Ziele")
    text = " ".join(_texts(data))
    gain = outs[3].loaded - outs[0].loaded
    assert f"{gain} TEU mehr, das sind {gain / C.PLACES:.1f} Wagen" in text
    assert f"ließen höchstens {mixed} TEU zu: die Zielreinheit kostet" in text and f" {mixed - outs[3].loaded} TEU." in text


def test_pdf_comparison_table_rows_are_complete_and_in_column_order():
    data, inst, outs, mixed, s = _pdf()
    text = _texts(data)
    start = text.index("zulässig") + 1
    rows = E.comparison_rows(inst, outs)
    for i, r in enumerate(rows):
        row = text[start + 7 * i: start + 7 * i + 7]
        assert row == [short_name(r.key), loaded_text(outs[i]), f"{r.utilization:.0f}", str(r.leftover), str(r.n_used_wagons), str(r.max_load), "ja" if r.valid else "nein"], (r.key, row)


def test_pdf_shows_an_unproven_exact_result_as_an_interval_and_marks_it_with_a_lower_bound_sign():
    data0, inst, outs, mixed, s = _pdf()
    plan = R.blocks(inst)
    ev = R.evaluate(inst, plan)
    fake = Outcome(X_, C.STRATEGY_LABELS[X_], plan, ev, ExactResult("feasible", plan, ev.loaded, ev.loaded + 1, "Regel", 1.0))
    text = _texts(generate_bahn_pdf(inst, outs[:3] + (fake,), mixed, s, compress=False))
    assert _after(text, short_name(X_)).startswith(f">= {ev.loaded} TEU")
    assert any(f"zwischen {ev.loaded} und {ev.loaded + 1} TEU" in t for t in text)
    assert any("mindestens" in t or "höchstens" in t for t in text)


def test_loaded_text_marks_invalid_plans_and_unproven_exact():
    plan = tuple(() for _ in range(2))
    valid = Outcome(F_, "x", plan, R.Evaluation(5, 3, 30, ()))
    bad = Outcome(F_, "x", plan, R.Evaluation(5, 3, 70, ("Last",)))
    unproven = Outcome(X_, "x", plan, R.Evaluation(5, 3, 30, ()), ExactResult("feasible", plan, 5, 6, "Löser", 1.0))
    proven = Outcome(X_, "x", plan, R.Evaluation(5, 3, 30, ()), ExactResult("optimal", plan, 5, 5, "Löser", 1.0))
    assert loaded_text(valid) == "5" and loaded_text(bad) == "5 (!)" and loaded_text(unproven) == ">= 5" and loaded_text(proven) == "5"
    assert loaded_text(Outcome(B_, "x", plan, R.Evaluation(5, 3, 30, ()), ExactResult("feasible", plan, 5, 6, "Löser", 1.0))) == "5"        # nur Exakt trägt das Zeichen


# ---------- Stichprobe, Urteil, Kurve ----------
def test_pdf_sample_section_lists_means_shares_and_the_three_verdicts():
    sample = tuple(lr(i, fifo=43 + i % 3, blocks=47, exact=47) for i in range(10))
    text = _texts(_pdf(sample=sample)[0])
    assert "Stichprobe und Urteil" in text
    start = text.index("zulässig in (%)") + 1
    assert text[start: start + 3] == [short_name(F_), f"{E.mean_loaded(sample, F_):.1f}", "100"]
    joined = " ".join(text)
    for label in ("Wagenblöcke gegen Reihenfolge", "Exakt gegen Reihenfolge", "Exakt gegen Wagenblöcke"):
        assert label in joined
    assert "Basis: 10 Tage (Seeds 0-9, nicht der eingestellte Seed)" in joined and "An 0 von 10 Tagen ist Exakt nicht bewiesen" in joined


def test_pdf_a_small_sample_still_gets_its_section():
    assert "Stichprobe und Urteil" in _texts(_pdf(sample=tuple(lr(i) for i in range(3)))[0])


def test_pdf_verdicts_pair_each_label_with_its_own_comparison():
    sample = tuple(lr(i, fifo=40, ffd=44, blocks=46 + i % 2, exact=47) for i in range(12))
    joined = " ".join(_texts(_pdf(sample=sample)[0]))
    for label, key, ref in (("Wagenblöcke gegen Reihenfolge", B_, F_), ("Exakt gegen Reihenfolge", X_, F_), ("Exakt gegen Wagenblöcke", X_, B_)):
        assert verdict_text(sample, label, key, ref) in joined, label


def test_pdf_curve_section_has_one_row_per_method_plus_the_mixed_bound_and_one_column_per_point():
    pts = (1, 4, 8)
    cv = E.Curve(pts, {p: tuple(lr(i, fifo=44 - p // 2, blocks=48 - p // 4, exact=48 - p // 4, mixed=48) for i in range(4)) for p in pts}, 4)
    text = _texts(_pdf(curve=cv)[0])
    assert "Geladene TEU über der Zahl der Zielterminals" in text
    start = text.index("Ziele") + 1
    assert text[start: start + 3] == ["1", "4", "8"]
    assert text[start + 3: start + 7] == [short_name(F_), "44.0", "42.0", "40.0"]
    assert text[start + 15: start + 19] == [short_name(X_), "48.0", "47.0", "46.0"]
    assert text[start + 19: start + 23] == ["ohne Reinheit", "48.0", "48.0", "48.0"]
    joined = " ".join(text)
    assert "Basis: 3 Zielzahlen x 4 Tage (Seeds 0-3)" in joined


def test_pdf_curve_note_names_the_kante_or_says_there_is_none():
    cheap = E.Curve((1, 2), {p: tuple(lr(i, exact=48, mixed=48) for i in range(3)) for p in (1, 2)}, 3)
    assert "höchstens 1 Platz" in " ".join(_texts(_pdf(curve=cheap)[0]))
    costly = E.Curve((1, 2), {1: tuple(lr(i, exact=48, mixed=48) for i in range(3)), 2: tuple(lr(i, exact=45, mixed=48) for i in range(3))}, 3)
    assert "Ab 2 Zielen kostet die Zielreinheit" in " ".join(_texts(_pdf(curve=costly)[0]))


@pytest.mark.parametrize("kind", ["better", "worse", "unclear", "none"])
def test_verdict_text_covers_all_states(kind):
    if kind == "better":
        sample = tuple(lr(i, fifo=40 + i % 2, blocks=46) for i in range(10))
    elif kind == "worse":
        sample = tuple(lr(i, fifo=50 + i % 2, blocks=46) for i in range(10))
    elif kind == "unclear":
        sample = tuple(lr(i, fifo=44 + (i % 2) * 2 - 1, blocks=44) for i in range(10))
    else:
        sample = tuple(ListResult(i, 58, lr(i).loaded, dict(lr(i).valid, **{B_: False}), True, "optimal", 48) for i in range(4))
    text = verdict_text(sample, "L", B_, F_)
    assert text.startswith("L:") and {"better": "% mehr geladene TEU", "worse": "% weniger geladene TEU", "unclear": "kein klarer Unterschied", "none": "An keinem Tag"}[kind] in text
    text.encode("latin-1")


def test_verdict_text_direction_and_reverse_shares():
    mixed_better = tuple(lr(i, fifo=40, blocks=(46 if i < 16 else 39)) for i in range(20))
    t = verdict_text(mixed_better, "L", B_, F_)
    assert "mehr geladene TEU" in t and "an 20 % der Tage ist es umgekehrt" in t
    mixed_worse = tuple(lr(i, fifo=40, blocks=(34 if i < 16 else 41)) for i in range(20))
    t = verdict_text(mixed_worse, "L", B_, F_)
    assert "weniger geladene TEU" in t and "an 20 % der Tage ist es besser" in t


# ---------- Ränder ----------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_pdf_is_generated_for_every_preset_compressed_and_uncompressed(name):
    for compress in (True, False):
        data = _pdf(name, compress=compress)[0]
        assert data.startswith(b"%PDF") and len(data) > 1500


def test_pdf_at_the_limits_stays_valid():
    tiny = _pdf(n_wagons=8, n_dests=1, offer_pct=80, share40_pct=0, payload=70)[0]
    big = _pdf(n_wagons=30, n_dests=10, offer_pct=150, share40_pct=100, payload=40)[0]
    assert tiny.startswith(b"%PDF") and big.startswith(b"%PDF")


def _pages(data):
    """Textstücke je Seite (unkomprimiertes PDF: ein Inhaltsstrom je Seite)."""
    streams = re.findall(rb"stream\r?\n(.*?)endstream", data, re.S)
    return [[t.decode("latin-1") for t in re.findall(rb"\((.*?)\)\s*Tj", s)] for s in streams]


def test_pdf_sections_are_not_split_across_pages():
    sample = tuple(lr(i) for i in range(20))
    cv = E.Curve(C.CURVE_POINTS, {p: tuple(lr(i) for i in range(8)) for p in C.CURVE_POINTS}, 8)
    pages = _pages(_pdf(sample=sample, curve=cv)[0])
    assert len(pages) <= 3
    for head, last in (("Stichprobe und Urteil", "An 0 von 20 Tagen ist Exakt nicht bewiesen"), ("Geladene TEU über der Zahl der Zielterminals", "höchstens 1 Platz"), ("Hinweise zum Modell", "echten Zügen.")):
        page = next(p for p in pages if head in p)
        assert last in " ".join(page), head
        assert page.index(head) < len(page) - 3, head


def test_verdict_text_without_a_percentage_when_the_reference_loads_nothing():
    sample = tuple(lr(i, fifo=0, blocks=2) for i in range(6))
    t = verdict_text(sample, "L", B_, F_)
    assert "2.0 mehr geladene TEU" in t and "%" not in t.split("(")[0]


def test_pdf_sample_table_shows_a_dash_for_a_method_without_any_valid_plan():
    sample = tuple(ListResult(i, 58, lr(i).loaded, dict(lr(i).valid, **{F_: False}), True, "optimal", 48) for i in range(4))
    text = _texts(_pdf(sample=sample)[0])
    start = text.index("zulässig in (%)") + 1
    assert text[start: start + 3] == [short_name(F_), "-", "0"]
