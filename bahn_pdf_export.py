"""PDF-Export des Ergebnisses (fpdf2, Helvetica-Kernschrift, nur Text und Tabellen).

Die Kernschriften kennen nur Latin-1: Umlaute und "×" sind erlaubt, aber "–" (Gedankenstrich), "€", "Σ", "≥", "≤", Emoji usw. lassen fpdf2 abstürzen. Deshalb läuft jeder Text durch
pdf_text(); Verfahren erscheinen mit ihren Kurznamen ohne Emoji."""

import time

import bahn_constants as C
import bahn_evaluation as E
import bahn_scenario as SC

_REPLACEMENTS = {
    "–": "-", "—": "-", "‑": "-", "−": "-", "Σ": "Summe", "δ": "Delta", "≥": ">=", "≤": "<=", "→": "->", "≈": "ca.", "€": "EUR",
    "·": "-", "“": '"', "”": '"', "„": '"', "’": "'", "‘": "'", "±": "+-", "⚠️": "(!)", "⚠": "(!)",
}
F_, D_, B_, X_ = C.STRAT_FIFO, C.STRAT_FFD, C.STRAT_BLOCKS, C.STRAT_EXACT


def pdf_text(text):
    """Text für die Helvetica-Kernschrift: bekannte Sonderzeichen ersetzen, den Rest Latin-1-sicher machen."""
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def short_name(key):
    return C.STRATEGY_PLAIN[key]


def loaded_text(o):
    """Geladene TEU eines Verfahrens: Zahl, '>=' bei nicht bewiesenem Optimum, '(!)' bei verletzter Bedingung."""
    txt = str(o.loaded)
    if o.key == X_ and not o.exact.proven:
        txt = ">= " + txt
    return txt + ("" if o.valid else " (!)")


def verdict_text(sample, label, key, reference):
    """Ein Satz je Vergleich, wie im Kernabschnitt der App (ohne Emoji)."""
    v = E.verdict(sample, key, reference)
    d = E.distribution(sample, key, reference)
    if v.kind == "none":
        return f"{label}: An keinem Tag sind beide Verfahren zulässig, ein Vergleich ist nicht möglich."
    if v.kind == "better":
        amount = f"{v.pct:.0f} % mehr" if v.pct is not None else f"{v.diff:.1f} mehr"
        return f"{label}: im Mittel {amount} geladene TEU ({v.diff:.1f} je Tag, Standardfehler {v.se:.2f}); an {d.worse * 100:.0f} % der Tage ist es umgekehrt."
    if v.kind == "worse":
        amount = f"{abs(v.pct):.0f} % weniger" if v.pct is not None else f"{-v.diff:.1f} weniger"
        return f"{label}: im Mittel {amount} geladene TEU ({v.diff:.1f} je Tag, Standardfehler {v.se:.2f}); an {d.better * 100:.0f} % der Tage ist es besser."
    return (f"{label}: kein klarer Unterschied, die Differenz ({v.diff:+.1f} TEU je Tag) liegt innerhalb des Rauschens (Standardfehler {v.se:.2f}); "
            f"mehr an {d.better * 100:.0f} %, weniger an {d.worse * 100:.0f} % der Tage.")


def generate_bahn_pdf(inst, outcomes, mixed_upper, settings, sample=None, curve=None, compress=True):
    """Ergebnis der aktuellen Einstellung als PDF: Szenario, Zusammenfassung, Verfahrensvergleich, optional Stichprobe/Urteil und Kurve, Hinweise.

    `outcomes`: die vier Outcomes; `mixed_upper`: Schranke ohne Zielreinheit; `settings`: dict mit den Reglerwerten (n_wagons, n_dests, offer_pct, share40_pct, payload, seed);
    `sample`: Tupel von ListResult oder None; `curve`: E.Curve oder None (beides nur, wenn auf Knopfdruck berechnet und zu den Einstellungen passend)."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    by_key = {o.key: o for o in outcomes}
    ref, best = by_key[F_], by_key[X_]
    cap, offered = SC.capacity(inst), SC.offered(inst)

    pdf = FPDF()
    pdf.set_compression(compress)
    pdf.add_page()

    def line(text, height=7, width=0):
        pdf.cell(width, height, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def heading(text):
        pdf.set_font("Helvetica", "B", 12)
        line(text, 8)
        pdf.set_font("Helvetica", "", 10)

    def pairs(rows):
        for label, value in rows:
            pdf.cell(70, 6, pdf_text(label), border=0)
            line(value, 6)

    def table(headers, widths, rows):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 230, 230)
        for header, width in zip(headers, widths):
            pdf.cell(width, 7, pdf_text(header), border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)
        pdf.set_font("Helvetica", "", 9)
        for row in rows:
            for value, width in zip(row, widths):
                pdf.cell(width, 7, pdf_text(str(value)), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(7)

    def keep_together(height):
        """Beginnt einen Abschnitt auf einer neuen Seite, wenn er sonst über den Seitenumbruch liefe (keine halb abgeschnittenen Listen)."""
        if pdf.get_y() + height > pdf.h - pdf.b_margin:
            pdf.add_page()

    def note(text, size=8):
        pdf.set_font("Helvetica", "I", size)
        pdf.set_text_color(110, 110, 110)
        pdf.multi_cell(0, 5, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 16)
    line("Bahn-Ladeplan: Wie voll wird der Zug?", 10)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    line(f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')}  -  sebastianhanisch.net", 6)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    s = settings
    heading("Szenario")
    pairs([
        ("Zug", f"{s['n_wagons']} Wagen zu je {C.PLACES} Plätzen = {cap} Plätze"),
        ("Zielterminals", str(s["n_dests"])),
        ("Angebot", f"{offered} TEU ({s['offer_pct']} % der Kapazität eingestellt)"),
        ("Anteil 40-Fuß", f"{s['share40_pct']} %"),
        ("Wagenlast", f"{s['payload']} t"),
        ("Seed des Tages", str(s["seed"])),
        ("Container", f"{len(inst.boxes)}"),
    ])
    pdf.ln(3)

    heading("Zusammenfassung")
    pairs([(short_name(o.key), loaded_text(o) + " TEU" + ("" if o.key == F_ else f" ({o.loaded - ref.loaded:+d} gegen Reihenfolge)")) for o in outcomes])
    gain = best.loaded - ref.loaded
    note(f"Die Reihenfolge lädt {ref.loaded} von {cap} Plätzen ({E.utilization(inst, ref.loaded):.0f} %), Exakt {'mindestens ' if not best.exact.proven else ''}{best.loaded} "
         f"({E.utilization(inst, best.loaded):.0f} %)" + (f": {gain} TEU mehr, das sind {gain / C.PLACES:.1f} Wagen." if gain > 0 else "."), 9)
    price = mixed_upper - best.loaded
    note(f"Ohne Zielreinheit (gemischte Wagen) ließen höchstens {mixed_upper} TEU zu: die Zielreinheit kostet {'höchstens ' if not best.exact.proven else ''}{price} TEU.", 9)
    pdf.ln(3)

    heading("Verfahrensvergleich")
    table_rows = []
    for r in E.comparison_rows(inst, outcomes):
        table_rows.append([short_name(r.key), loaded_text(by_key[r.key]), f"{r.utilization:.0f}", r.leftover, r.n_used_wagons, r.max_load, "ja" if r.valid else "nein"])
    table(["Verfahren", "Geladene TEU", "Auslastung (%)", "Bleiben stehen", "Wagen mit Ladung", "Größte Last (t)", "zulässig"], [38, 28, 26, 26, 30, 28, 14], table_rows)
    value, upper, proven = E.exact_interval(best)
    if not proven:
        note(f"Exakt ist nicht bewiesen: das Optimum liegt zwischen {value} und {upper} TEU (nach {C.EXACT_LIVE_LIMIT_SECONDS} s Zeitlimit).")
    else:
        note("Geladene TEU: 20 Fuß = 1, 40 Fuß = 2. Ein Optimum, das das Angebot oder alle Plätze ausschöpft, ist ohne Löser bewiesen.")
    pdf.ln(3)

    if sample is not None:
        keep_together(95)
        heading("Stichprobe und Urteil")
        table(["Verfahren", "Geladene TEU im Mittel", "zulässig in (%)"], [50, 60, 40],
              [[short_name(k), "-" if E.mean_loaded(sample, k) is None else f"{E.mean_loaded(sample, k):.1f}", f"{E.valid_share(sample, k) * 100:.0f}"] for k in C.STRATEGY_KEYS])
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        for label, key, reference in (("Wagenblöcke gegen Reihenfolge", B_, F_), ("Exakt gegen Reihenfolge", X_, F_), ("Exakt gegen Wagenblöcke", X_, B_)):
            pdf.multi_cell(0, 5, pdf_text("- " + verdict_text(sample, label, key, reference)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        mp = E.mean_price(sample)
        note(f"Basis: {len(sample)} Tage (Seeds 0-{len(sample) - 1}, nicht der eingestellte Seed) mit den eingestellten Werten. Klar heißt: Unterschied größer als zwei Standardfehler der gepaarten "
             f"Differenz, nur über Tage, an denen beide Verfahren zulässig sind. Preis der Zielreinheit im Mittel {'höchstens ' if E.unproven_count(sample) else ''}{mp:.1f} TEU. "
             f"An {E.unproven_count(sample)} von {len(sample)} Tagen ist Exakt nicht bewiesen (untere Schranke).")
        pdf.ln(3)

    if curve is not None:
        keep_together(80)
        heading("Geladene TEU über der Zahl der Zielterminals")
        pts = curve.points
        cw = [44] + [max(14, int(146 / len(pts)))] * len(pts)
        rows = []
        for key in C.STRATEGY_KEYS:
            rows.append([short_name(key)] + ["-" if v is None else f"{v:.1f}" for v in E.curve_means(curve, key)])
        rows.append(["ohne Reinheit"] + [f"{v:.1f}" for v in E.curve_mixed(curve)])
        table(["Ziele"] + [str(p) for p in pts], cw, rows)
        kante = E.kante(curve)
        note(f"Basis: {len(pts)} Zielzahlen x {curve.n_lists} Tage (Seeds 0-{curve.n_lists - 1}). "
             + (f"Ab {kante} Zielen kostet die Zielreinheit im Mittel mehr als {C.KANTE_PRICE:g} Platz." if kante is not None
                else f"Im untersuchten Bereich kostet die Zielreinheit im Mittel höchstens {C.KANTE_PRICE:g} Platz."))
        pdf.ln(3)

    keep_together(70)
    heading("Hinweise zum Modell")
    pdf.set_font("Helvetica", "", 9)
    for text in [
        "Ein Zug, eine Abfahrt, keine Zeitachse: alle Container sind da, bevor beladen wird. Keine Achslast, keine Reefer, kein Gefahrgut, nur 60-Fuß-Wagen mit drei Plätzen.",
        "Zielreinheit (ein Ziel je Wagen) ist eine Modellannahme; die Schranke ohne Zielreinheit ist kein Verfahren, sondern die Messlatte für ihren Preis.",
        "Die Regel Wagenblöcke ist eine eigene Konstruktion; der Exakt-Löser (CP-SAT) beweist das Optimum, wo das Zeitlimit reicht, sonst steht ein Intervall.",
        "Alle Zahlen sind Größenordnungen aus einer Simulation mit zufälligen Tagen, keine Messung an echten Zügen.",
    ]:
        pdf.multi_cell(0, 5, pdf_text("- " + text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
