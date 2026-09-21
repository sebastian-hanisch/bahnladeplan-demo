"""Wiederverwendbare Panels: je Verfahren ein Tab im Methodenvergleich und der selbstständige Exakt-Tab (Beweis oder Intervall)."""

import streamlit as st

import bahn_constants as C
import bahn_evaluation as E
import bahn_scenario as SC
from bahn_visualization import train_figure

VIOLATION_TEXT = {
    "Wagen": "Die Wagenzahl stimmt nicht",
    "Container": "Ein Container ist doppelt oder unbekannt",
    "Platz": "Plätze doppelt belegt oder außerhalb des Wagens",
    "Last": "Die Wagenlast ist überschritten",
    "Ziel": "Ein Wagen hat mehr als ein Ziel",
}


def render_strategy_panel(prefix, outcome, outcomes, inst):
    """Beschreibung, Kennzahlen (2 x 2) und Zug-Bild eines Verfahrens. Deltas lesen sich immer als "dieses Verfahren minus Reihenfolge" (mehr geladene TEU ist besser). Verletzt der Plan eine
    Bedingung, steht das ausdrücklich dabei. `prefix` macht die Widget-Schlüssel eindeutig."""
    ref = E.outcome_of(outcomes, C.BASELINE)
    st.markdown(C.STRATEGY_DESCRIPTIONS[outcome.key])
    is_ref = outcome.key == ref.key
    diff = outcome.loaded - ref.loaded
    top, bottom = st.columns(2), st.columns(2)                      # 2 x 2: vier Spalten schneiden die Namen in schmalen Tabs ab
    m1, m2, m3, m4 = top + bottom
    m1.metric("Geladene TEU", f"{outcome.loaded}" + ("" if outcome.valid else " ⚠️"), delta=None if is_ref else f"{diff:+d}", delta_color="off" if diff == 0 or not outcome.valid else "normal",
              help="TEU (20 Fuß = 1, 40 Fuß = 2), die mitfahren. Mehr ist besser.")
    m2.metric("Platz-Auslastung", f"{E.utilization(inst, outcome.loaded):.0f} %", help=f"Geladene TEU von {C.PLACES * inst.n_wagons} Plätzen.")
    m3.metric("Bleiben stehen", f"{E.leftover(inst, outcome.loaded)} TEU", help="Angebotene TEU, die nicht mitfahren und auf den nächsten Zug warten.")
    m4.metric("Wagen mit Ladung", f"{sum(1 for w in outcome.plan if w)} von {inst.n_wagons}", help=f"Größte Wagenlast {outcome.evaluation.max_load} t von {inst.payload} t.")
    if not outcome.valid:
        st.warning("⚠️ " + "; ".join(VIOLATION_TEXT.get(v, v) for v in outcome.violations) + ": Das Ergebnis ist mit den zulässigen Plänen nicht vergleichbar.")
    st.plotly_chart(train_figure(inst, outcome.plan), width="stretch", key=f"{prefix}_train_chart")


def render_exact_panel(prefix, inst, outcome, long_run=False):
    """Exakt-Tab: Beweislage (bewiesen optimal oder Intervall), Optimum und Zug-Bild. `long_run` = das Ergebnis stammt aus dem langen Zeitlimit."""
    res = outcome.exact
    limit = C.EXACT_LONG_LIMIT_SECONDS if long_run else C.EXACT_LIVE_LIMIT_SECONDS
    if res.status == "optimal":
        why = "alles Angebotene oder alle Plätze sind belegt" if res.value == SC.upper_bound(inst) else "vom Löser bewiesen"
        st.success(f"✅ Bewiesen optimal ({why}), {res.wall_ms:.0f} ms.")
    else:
        st.warning(f"⏱️ Nicht bewiesen: Nach {limit} s liegt das Optimum zwischen **{res.value}** und **{res.upper}** TEU (beste gefundene Lösung: {res.value}"
                   + ("; Plan der Regel Wagenblöcke, der Löser fand nichts Besseres" if res.source == "Regel" else "") + ").")
    st.metric("Optimum der geladenen TEU" + ("" if res.proven else " (beste bekannte)"), f"{res.value}",
              help="Größte Zahl geladener TEU, die Plätze, Wagenlast und Zielreinheit einhält." + ("" if res.proven else " Nicht bewiesen: das Optimum kann größer sein (bis " + str(res.upper) + ")."))
    st.caption(f"Platz-Auslastung {E.utilization(inst, outcome.loaded):.0f} %, {E.leftover(inst, outcome.loaded)} TEU bleiben stehen, größte Wagenlast {outcome.evaluation.max_load} t von {inst.payload} t.")
    st.plotly_chart(train_figure(inst, outcome.plan), width="stretch", key=f"{prefix}_train_chart")
