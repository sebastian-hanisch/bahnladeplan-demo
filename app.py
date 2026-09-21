"""
Bahn-Ladeplan – interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Welle 4 der Hafen-Linie (Kran -> Hinterland): Wie belädt man einen Containerzug, dessen Wagen jeweils zu genau einem Zielterminal fahren, so, dass möglichst wenige Plätze leer bleiben?
Die Alltagsregel verschenkt Plätze; gezeigt wird, was kluge Regeln und ein exakter Löser laden und was die Zielreinheit (ein Ziel je Wagen) kostet.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import bahn_constants as C
import bahn_evaluation as E
import bahn_scenario as SC
import bahn_visualization as V
from bahn_pdf_export import generate_bahn_pdf
from bahn_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, scenario_instance, SETTING_SPECS, sync_query_params)
from bahn_ui_panel import render_exact_panel, render_strategy_panel

st.set_page_config(page_title="Bahn-Ladeplan – Sebastian Hanisch", layout="wide")

SCENARIO_KEYS = list(SETTING_SPECS)
F_, D_, B_, X_ = C.STRAT_FIFO, C.STRAT_FFD, C.STRAT_BLOCKS, C.STRAT_EXACT
LABEL = C.STRATEGY_LABELS


@st.cache_data(show_spinner=False, max_entries=32)
def _compute_scenario(key):
    """Instanz, alle vier Verfahren (Exakt mit kurzem Zeitlimit) und die Schranke ohne Zielreinheit."""
    inst = scenario_instance(*key)
    outcomes = E.run_methods(inst, C.EXACT_LIVE_LIMIT_SECONDS)
    best = E.outcome_of(outcomes, X_).loaded
    mixed = SC.upper_bound(inst) if best >= SC.upper_bound(inst) else max(E.mixed_bound(inst, C.SAMPLE_LIMIT_SECONDS)[0], best)
    return inst, outcomes, mixed


@st.cache_data(show_spinner=False, max_entries=8)
def _compute_exact_long(key):
    """Exakt-Tab auf Knopfdruck: langes Zeitlimit."""
    return E.exact_outcome(scenario_instance(*key), C.EXACT_LONG_LIMIT_SECONDS)


st.title("🚆 Bahn-Ladeplan: Wie voll wird der Zug?")
st.markdown(
    """
Ein Containerzug besteht aus Wagen mit je drei Plätzen. Jeder Wagen fährt zu **einem Zielterminal**, ein 40-Fuß-Container braucht **zwei benachbarte Plätze**, und jeder Wagen trägt nur
begrenztes Gewicht. Was nicht mitfährt, wartet auf den nächsten Zug. Die Demo zeigt, wie viele Container ein Zug wirklich schafft, was die Alltagsregel „erster passender Wagen“ verschenkt und
was die **Zielreinheit** (ein Ziel je Wagen) kostet. Wie das Modell funktioniert, steht im Expander "Wie funktioniert diese Demo?" weiter unten, die formale Herleitung im Expander
"📐 Mathematische Formulierung".
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
PRESET_HELP = {
    "Locker": "Das Angebot liegt unter der Kapazität: es passt (fast) alles, die Regeln unterscheiden sich kaum.",
    "Üblich": "Mehr Angebot als Plätze und vier Ziele: die Reihenfolge verschenkt Plätze, Wagenblöcke und Exakt laden ein Vollzug.",
    "Viele Ziele": "Acht Ziele: die Alltagsregel verschenkt noch mehr, und die Zielreinheit kostet mehrere Plätze.",
    "Schwer": "Wenige 40-Fuß-Container, aber nur 40 t je Wagen: das Gewicht bindet, und der Löser lädt an manchen Tagen mehr als die Regel Wagenblöcke.",
    "Ganz lang": "Zehn Ziele: der Löser kommt an seine Grenze, „nicht bewiesen“ wird sichtbar.",
}
# Je Zeile drei Schaltflächen: bei fünf in einer Zeile werden die Namen in schmalen Fenstern abgeschnitten.
preset_names = list(C.PRESETS.keys())
for row in (preset_names[:3], preset_names[3:]):
    cols = st.columns(3)
    for col, name in zip(cols, row):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_wagons = st.slider("Anzahl Wagen", *bounds("n_wagons_slider"), key="n_wagons_slider", help="Länge des Zuges; je Wagen drei Plätze. Ab etwa 24 Wagen beweist der Löser bei vielen Zielen nicht immer.")
    n_dests = st.slider("Zielterminals", *bounds("n_dest_slider"), key="n_dest_slider", help="Wohin die Container wollen. Mehr Ziele = mehr Zielreinheit-Zwang. Bei einem Ziel laden alle Verfahren gleich.")
    offer_pct = st.slider("Angebot (% der Kapazität)", *bounds("offer_slider"), step=C.OFFER_PCT_STEP, format="%d%%", key="offer_slider",
                          help="Angebotene TEU in Prozent der Plätze. Unter 100 % passt alles, darüber muss der Plan auswählen.")
    share40_pct = st.slider("Anteil 40-Fuß (%)", *bounds("share40_slider"), step=C.SHARE40_PCT_STEP, format="%d%%", key="share40_slider",
                            help="0 % = nur 20 Fuß (kaum Lücken), 100 % = nur 40 Fuß (jeder Wagen verschenkt einen Platz).")
    payload = st.slider("Wagenlast (t)", *bounds("payload_slider"), step=C.PAYLOAD_STEP, format="%d t", key="payload_slider",
                        help="Höchstes Gewicht je Wagen. Unter etwa 50 t bindet das Gewicht; darüber ändert es wenig.")
    seed = st.number_input("Seed des Tages", *bounds("seed_input"), key="seed_input", step=1, help="Bestimmt Container, Gewichte und Ziele.")
    st.button("🎲 Neuer Tag", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Seed für den Tag.")

sync_query_params({key: st.session_state[key] for key in SCENARIO_KEYS})

scenario_key = (int(n_wagons), int(n_dests), int(offer_pct), int(share40_pct), int(payload), int(seed))
sample_key = scenario_key[:5]
curve_key = (int(n_wagons), int(offer_pct), int(share40_pct), int(payload))

with st.spinner("Führe die Verfahren aus (Exakt bis zu %d s)..." % C.EXACT_LIVE_LIMIT_SECONDS):
    inst, outcomes, mixed_upper = _compute_scenario(scenario_key)
by_key = {o.key: o for o in outcomes}
ref = by_key[F_]
cap, offered = SC.capacity(inst), SC.offered(inst)


def _loaded_text(o):
    """Wert der Kennzahl: geladene TEU, mit ≥ bei nicht bewiesenem Optimum, mit ⚠️ bei verletzter Bedingung."""
    txt = f"{o.loaded}"
    if o.key == X_ and not o.exact.proven:
        txt = f"≥ {txt}"
    return txt + ("" if o.valid else " ⚠️")


# ---------------------------------------------------------------------------------------------------
# Hauptansicht
# ---------------------------------------------------------------------------------------------------
st.markdown("## 🎯 Wie viele Container schafft dieser Zug?")
st.caption(f"Geladene TEU (20 Fuß = 1, 40 Fuß = 2) auf {inst.n_wagons} Wagen mit {cap} Plätzen; angeboten sind {offered} TEU. Alle Verfahren laden dieselben Container.")

metric_rows = [st.columns(2), st.columns(2)]                  # 2 x 2: vier Spalten schneiden die Namen bei 800 px ab
for col, o in zip(metric_rows[0] + metric_rows[1], outcomes):
    diff = o.loaded - ref.loaded
    help_txt = "Referenz für alle Vergleiche." if o.key == F_ else "Differenz: dieses Verfahren minus Reihenfolge (mehr geladene TEU ist besser)."
    if not o.valid:
        help_txt += " ⚠️ Der Plan verletzt eine Bedingung (" + ", ".join(o.violations) + "): nicht mit den zulässigen Plänen vergleichbar."
    if o.key == X_ and not o.exact.proven:
        help_txt += f" Nicht bewiesen: das Optimum liegt zwischen {o.exact.value} und {o.exact.upper}."
    col.metric(o.label, _loaded_text(o), delta=None if o.key == F_ else f"{diff:+d}", delta_color="off" if diff == 0 or not o.valid else "normal", help=help_txt)

best = by_key[X_]
gain = best.loaded - ref.loaded
price = mixed_upper - best.loaded
st.info(
    f"ℹ️ Die Reihenfolge lädt **{ref.loaded}** von {cap} Plätzen ({E.utilization(inst, ref.loaded):.0f} %), Exakt **{'mindestens ' if not best.exact.proven else ''}{best.loaded}** "
    f"({E.utilization(inst, best.loaded):.0f} %)"
    + (f": **{gain} TEU mehr**, das sind {gain / C.PLACES:.1f} Wagen." if gain > 0 else ".")
    + (f" Gemischte Wagen ließen höchstens {mixed_upper} TEU zu: die Zielreinheit kostet {'höchstens ' if not best.exact.proven else ''}**{price}** TEU." if price > 0
       else " Die Zielreinheit kostet hier nichts: mehr als das Optimum ließe auch ein Zug mit gemischten Wagen nicht zu.")
)

st.markdown("#### 🔍 Blick auf den Zug")
right_key = st.radio("Rechts vergleichen mit", list(C.RIGHT_VIEW_KEYS), format_func=LABEL.get, key="view_radio", horizontal=True, help="Links steht immer die Reihenfolge.")
right = by_key[right_key]
left_col, right_col = st.columns(2)
for col, o, side in ((left_col, ref, "left"), (right_col, right, "right")):
    with col:
        st.markdown(f"**{o.label}**: {_loaded_text(o)} TEU")
        st.plotly_chart(V.train_figure(inst, o.plan, legend=False), width="stretch", key=f"train_chart_{side}")
dest_colors = ", ".join(f"{d + 1} {C.DEST_COLOR_NAMES[d]}" for d in range(inst.n_dests))
st.caption(f"Ein Rechteck je Container: Farbe = Zielterminal ({dest_colors}), Zahl = Gewicht in t (dunkler = schwerer), ein breites Rechteck ist ein 40-Fuß-Container, graue Felder sind leere Plätze. "
           f"Unter jedem Wagen steht seine Last (höchstens {inst.payload} t); die Wagennummer zeigt der Tooltip.")

pdf_slot = st.container()          # der Download steht in der Hauptansicht, wird aber erst gefüllt, wenn Stichprobe und Kurve (falls berechnet) feststehen

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Kernabschnitt
# ---------------------------------------------------------------------------------------------------
st.subheader("📐 Was kostet die Zielreinheit?")
st.markdown(
    """
Kernfrage dieser Demo: Wie viele Plätze verschenkt die Alltagsregel, und was kostet die Vorgabe „ein Ziel je Wagen“? Wer den Zug in Ankunftsreihenfolge belädt, reißt mit jedem neuen Ziel einen
Wagen an und lässt Plätze leer. Die kluge Regel **Wagenblöcke** füllt je Ziel eigene Wagen und nimmt die vollsten; sie trifft das Optimum fast immer. Was dann noch fehlt gegenüber einem Zug mit
gemischten Wagen, ist der **Preis der Zielreinheit**; er wächst mit der Zahl der Ziele. Hier live für Ihre Einstellungen gerechnet, **mit der Verteilung dazu**:
"""
)
g1, g2, g3 = st.columns(3)
g1.metric("Plätze im Zug", f"{cap}", help=f"{inst.n_wagons} Wagen mit je {C.PLACES} Plätzen (60 Fuß).")
g2.metric("Angebot", f"{offered} TEU", help=f"{offered * 100 / cap:.0f} % der Kapazität (eingestellt {offer_pct} %, ganze Container).")
g3.metric("Preis der Zielreinheit", f"{'≤ ' if not best.exact.proven else ''}{price} TEU", help="Höchstens so viele TEU lädt ein Zug mit gemischten Wagen mehr als das Optimum mit Zielreinheit "
          "(Schranke ohne Reinheit minus beste Lösung).")

pts, n_lists = E.curve_plan(int(n_wagons))
st.caption(
    f"Die Stichprobe rechnet {C.SAMPLE_LISTS} Tage mit Ihren Einstellungen, die Kurve {len(pts)} Zielzahlen × {n_lists} Tage, jeweils mit {C.SAMPLE_LIMIT_SECONDS} s Limit für den exakten "
    "Löser. Das dauert je nach Einstellung etwa 30 bis 90 Sekunden und läuft deshalb auf Knopfdruck. Beides hängt nicht vom eingestellten Seed ab."
)
if st.button("📊 Stichprobe und Kurve berechnen", key="bahn_curve_btn"):
    bar = st.progress(0.0, text="Rechne die Stichprobe ...")
    try:
        sample_new = E.sample(*sample_key, progress=lambda f: bar.progress(min(1.0, 0.4 * f), text=f"Rechne die Stichprobe ... {f * 100:.0f} %"))
        curve_new = E.curve_over_dests(*curve_key, progress=lambda f: bar.progress(min(1.0, 0.4 + 0.6 * f), text=f"Rechne die Kurve ... {f * 100:.0f} %"))
        st.session_state["bahn_curve"] = (sample_key, curve_key, sample_new, curve_new)
    except ValueError as err:
        st.warning(f"Die Berechnung ist mit diesen Einstellungen nicht möglich: {err}")
    bar.empty()


def _show_verdict(sample, label, key, reference):
    v = E.verdict(sample, key, reference)
    d = E.distribution(sample, key, reference)
    if v.kind == "none":
        st.info(f"ℹ️ **{label}**: In keinem Tag sind beide Verfahren zulässig, ein Vergleich ist nicht möglich.")
    elif v.kind == "better":
        amount = f"**{v.pct:.0f} % mehr**" if v.pct is not None else f"**{v.diff:.1f} mehr**"
        st.success(f"✅ **{label}**: im Mittel {amount} geladene TEU ({v.diff:.1f} je Tag, Standardfehler {v.se:.2f}). An **{d.worse * 100:.0f} %** der Tage ist es umgekehrt.")
    elif v.kind == "worse":
        amount = f"**{abs(v.pct):.0f} % weniger**" if v.pct is not None else f"**{-v.diff:.1f} weniger**"
        st.warning(f"⚠️ **{label}**: im Mittel {amount} geladene TEU ({v.diff:.1f} je Tag, Standardfehler {v.se:.2f}). An **{d.better * 100:.0f} %** der Tage ist es besser.")
    else:
        st.info(f"ℹ️ Kein klarer Unterschied bei **{label}**: die Differenz ({v.diff:+.1f} TEU je Tag) liegt innerhalb des Rauschens (Standardfehler {v.se:.2f}). "
                f"Mehr in {d.better * 100:.0f} %, weniger in {d.worse * 100:.0f} % der Tage.")


stored = st.session_state.get("bahn_curve")
have_curve = stored is not None and stored[0] == sample_key and stored[1] == curve_key
if have_curve:
    sample, curve = stored[2], stored[3]
    st.markdown("**Urteil über die Stichprobe** (gepaarte Differenz, klar ab mehr als zwei Standardfehlern; nur Tage, an denen beide Verfahren zulässig sind)")
    _show_verdict(sample, "Wagenblöcke gegen Reihenfolge", B_, F_)
    _show_verdict(sample, "Exakt gegen Reihenfolge", X_, F_)
    _show_verdict(sample, "Exakt gegen Wagenblöcke", X_, B_)
    dists = [E.distribution(sample, k, F_) for k in (D_, B_, X_)]
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.markdown("**Wie sich die Gewinne verteilen** (Anteil der Tage)")
        st.plotly_chart(V.distribution_figure(dists), width="stretch", key="distribution_chart")
    with dcol2:
        st.markdown("**Typischer Tag gegen Mittelwert**")
        st.plotly_chart(V.gain_figure(dists), width="stretch", key="gain_chart")
    mp = E.mean_price(sample)
    st.caption(
        f"Basis: {len(sample)} Tage (Seeds 0-{len(sample) - 1}, nicht Ihr Seed). Im Mittel laden die Reihenfolge {E.mean_loaded(sample, F_):.1f}, Größe zuerst {E.mean_loaded(sample, D_):.1f}, "
        f"Wagenblöcke {E.mean_loaded(sample, B_):.1f} und Exakt {E.mean_loaded(sample, X_):.1f} von {cap} Plätzen. Gleich heißt: dieselbe Zahl. Preis der Zielreinheit im Mittel "
        f"{'höchstens ' if E.unproven_count(sample) else ''}{mp:.1f} TEU. In {E.unproven_count(sample)} von {len(sample)} Tagen ist Exakt nicht bewiesen; der Wert ist dort eine untere Schranke des Optimums."
    )
    st.markdown("**Geladene TEU über der Zahl der Zielterminals**")
    st.plotly_chart(V.curve_figure(curve, int(n_dests) if int(n_dests) in curve.points else None, capacity=cap), width="stretch", key="curve_chart")
    kante = E.kante(curve)
    st.caption(
        f"Basis: {len(curve.points)} Zielzahlen × {curve.n_lists} Tage (Seeds 0-{curve.n_lists - 1}). Ein gefüllter grüner Punkt heißt: Optimum an allen Tagen bewiesen; ein offener: an mindestens "
        "einem Tag nur die beste gefundene Lösung (untere Schranke). Die violette Linie ist die Schranke ohne Zielreinheit; der Abstand zu Exakt ist der Preis der Reinheit. Die senkrechte Achse beginnt nicht bei 0. "
        + (f"Ab {kante} Zielen kostet die Zielreinheit im Mittel mehr als {C.KANTE_PRICE:g} Platz." if kante is not None else f"Im untersuchten Bereich kostet die Zielreinheit im Mittel höchstens {C.KANTE_PRICE:g} Platz.")
    )
elif stored is not None:
    st.info("ℹ️ Die zuletzt berechnete Stichprobe und Kurve bezogen sich auf andere Einstellungen. Erneut auf '📊 Stichprobe und Kurve berechnen' klicken.")
else:
    st.info("Noch nichts berechnet – auf den Button oben klicken.")

with pdf_slot:
    st.download_button(
        "📄 Ergebnis als PDF herunterladen",
        data=generate_bahn_pdf(inst, outcomes, mixed_upper, dict(n_wagons=int(n_wagons), n_dests=int(n_dests), offer_pct=int(offer_pct), share40_pct=int(share40_pct), payload=int(payload), seed=int(seed)),
                               sample=stored[2] if have_curve else None, curve=stored[3] if have_curve else None),
        file_name="bahn_ladeplan_ergebnis.pdf", mime="application/pdf", key="primary_pdf_download",
        help="Szenario, Verfahrensvergleich und, falls berechnet, Stichprobe mit Urteil und die Kurve über der Zahl der Zielterminals.")

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Methodenvergleich
# ---------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tabs = st.tabs([o.label for o in outcomes] + ["📊 Vergleich"])
    for tab, outcome in zip(tabs, outcomes):
        with tab:
            if outcome.key == X_:
                long_key = st.session_state.get("bahn_exact_long_key")
                st.caption("Die größte Zahl geladener TEU, die alle Bedingungen einhält (CP-SAT). Ein Optimum, das das Angebot oder die Plätze ausschöpft, ist ohne Löser bewiesen; sonst steht ein "
                           f"Intervall aus bester Lösung und oberer Schranke. Live mit {C.EXACT_LIVE_LIMIT_SECONDS} s Limit, hier auf Knopfdruck mit {C.EXACT_LONG_LIMIT_SECONDS} s.")
                if st.button(f"🧮 Mit {C.EXACT_LONG_LIMIT_SECONDS} s nachrechnen", key="bahn_exact_btn"):
                    st.session_state["bahn_exact_long_key"] = scenario_key
                    long_key = scenario_key
                if long_key == scenario_key:
                    with st.spinner(f"Exakte Suche (bis zu {C.EXACT_LONG_LIMIT_SECONDS} s)..."):
                        long_outcome = _compute_exact_long(scenario_key)
                    render_exact_panel("exact", inst, long_outcome, long_run=True)
                else:
                    if long_key is not None:
                        st.info("ℹ️ Das zuletzt nachgerechnete Ergebnis bezog sich auf ein anderes Szenario. Erneut auf den Knopf klicken; gezeigt ist das Live-Ergebnis.")
                    render_exact_panel("exact", inst, outcome)
            else:
                render_strategy_panel(f"strategy_{outcome.key}", outcome, outcomes, inst)
    with tabs[4]:
        table = []
        for r in E.comparison_rows(inst, outcomes):
            o = by_key[r.key]
            table.append({"Verfahren": r.label, "Geladene TEU": _loaded_text(o), "Platz-Auslastung": f"{r.utilization:.0f} %", "Bleiben stehen (TEU)": r.leftover,
                          "Wagen mit Ladung": r.n_used_wagons, "Größte Wagenlast (t)": r.max_load, "zulässig": "ja" if r.valid else "nein: " + ", ".join(r.violations),
                          "Differenz zur Reihenfolge": r.delta_vs_baseline})
        table.append({"Verfahren": "Ohne Zielreinheit (Schranke)", "Geladene TEU": f"≤ {mixed_upper}", "Platz-Auslastung": f"≤ {mixed_upper * 100 / cap:.0f} %", "Bleiben stehen (TEU)": offered - mixed_upper,
                      "zulässig": "Vergleichswert, kein Verfahren", "Differenz zur Reihenfolge": mixed_upper - ref.loaded})
        st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)
        st.plotly_chart(V.comparison_figure(inst, outcomes, mixed_upper), width="stretch", key="comparison_chart")
        st.caption("Die Schranke ohne Zielreinheit rechnet dieselben Container auf gemischte Wagen; sie ist kein Plan, sondern die Messlatte für den Preis der Zielreinheit.")

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Zug und Container.** Ein Zug besteht aus Wagen mit je **drei Plätzen** (ein 60-Fuß-Wagen trägt 3 TEU). Ein Container ist 20 Fuß (ein Platz) oder 40 Fuß (zwei **benachbarte** Plätze), hat ein
Gewicht in Tonnen und ein **Zielterminal**. Jeder Wagen trägt höchstens die eingestellte Last. Wird mehr angeboten, als der Zug fasst, wählt der Plan aus; der Rest bleibt für den nächsten Zug.

**Zielreinheit.** Die Wagen eines Ziels werden am Zielterminal abgekoppelt; darum fährt jeder Wagen zu **genau einem** Ziel. Ein halb gefüllter Wagen kann keine Container eines zweiten Ziels
aufnehmen. Das ist die Annahme, die diese Demo untersucht.

**Vier Verfahren**, alle mit denselben Containern:

- **Reihenfolge** (Referenz): Container in Ankunftsreihenfolge, in den ersten Wagen desselben Ziels mit Platz und Last, sonst in einen neuen Wagen. Der Alltag ohne Plan.
- **Größe zuerst**: erst die 40-Fuß-Container, jeweils schwerere zuerst, jeder in den Wagen seines Ziels mit dem wenigsten Restplatz.
- **Wagenblöcke**: je Ziel die Container mit „Größe zuerst“ in eigene Wagen packen (so viele wie nötig), dann die vollsten Wagen auswählen, bis der Zug voll ist.
- **Exakt (CP-SAT)**: die größte Zahl geladener TEU mit Beweis. Reicht das Zeitlimit nicht, steht ein Intervall aus bester Lösung und oberer Schranke, nie ein unbewiesener Wert als Optimum.
  Lädt schon die Regel alles Angebotene oder alle Plätze, ist das Optimum ohne Löser bewiesen.

**Das Zug-Bild lesen.** Ein Rechteck je Container: Farbe = Zielterminal, Zahl = Gewicht in t (dunkler = schwerer), ein breites Rechteck ist ein 40-Fuß-Container, graue Felder sind leere Plätze.

**Warum die Alltagsregel Plätze verschenkt.** Jeder neue Container mit einem neuen Ziel reißt einen Wagen an. Sind viele Ziele im Spiel, bleiben viele Wagen halb leer, und die
40-Fuß-Container lassen in Wagen mit ungerader Platzzahl einen Platz frei. Wagenblöcke sehen zuerst, wie viele Container jedes Ziel hat, und füllen Wagen je Ziel; die vollsten Wagen
fahren mit. Das ist fast immer schon optimal.

**Der Preis der Zielreinheit.** Zum Vergleich wird derselbe Zug mit gemischten Wagen gerechnet (kein Verfahren, nur eine Schranke). Der Abstand zum Optimum mit Zielreinheit ist der Preis der
Reinheit: bei einem Ziel null, mit vielen Zielen und wenigen Containern je Ziel mehrere Plätze.

**Stichprobe, Verteilung und Urteil.** Die Stichprobe stellt Ihre Einstellungen auf 20 Tage (Seeds 0 bis 19, nicht Ihr Seed) nach. Ein Unterschied gilt als klar, wenn er mehr als zwei
Standardfehler der gepaarten Differenz beträgt. Die Verteilung zeigt, an wie vielen Tagen ein Verfahren mehr, gleich viel oder weniger lädt als die Reihenfolge; ein Mittelwert weit vom Median heißt,
dass wenige Tage den Gewinn tragen.

**Grenzen dieses Modells** (bewusst so gewählt, damit die Aussage ehrlich bleibt):

- **Ein Zug, eine Abfahrt, keine Zeitachse**: Alle Container sind da, bevor der Zug beladen wird. Eine Online-Beladung (Container kommen nach und nach) ist nicht modelliert.
- **Keine Achslast und Lastverteilung im Wagen**, nur die Summe je Wagen; keine Reefer, kein Gefahrgut, nur 60-Fuß-Wagen.
- Die **Zielreinheit ist eine Modellannahme**; in der Praxis gibt es auch gemischte Wagen und Umsetzen unterwegs.
- Gewichte und Ziele sind **gleichverteilt und unabhängig**; die Regel **Wagenblöcke ist meine Konstruktion**.
- Alle Zahlen sind **Größenordnungen aus einer Simulation mit zufälligen Tagen, keine Messung an echten Zügen.**
        """
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Beladung eines Zuges mit Zielreinheit** (Packproblem mit Nachbarschaft und Kapazitäten; NP-schwer, kleine Fälle exakt lösbar).

Gegeben sind $W$ Wagen mit je drei Plätzen, Container $i$ mit Länge $\ell_i \in \{20, 40\}$ (Platzbedarf $s_i = 1$ oder $2$), Gewicht $g_i$ und Ziel $d(i) \in \{1, \dots, D\}$, sowie die
Wagenlast $PL$. Variablen: $x_{i,w,p} \in \{0,1\}$ (Container $i$ liegt in Wagen $w$ und belegt die Plätze $p, \dots, p + s_i - 1$) und $y_{w,d} \in \{0,1\}$ (Wagen $w$ fährt zu Ziel $d$).

**Bedingungen:**
$$
\sum_{w,p} x_{i,w,p} \le 1, \qquad \sum_{i}\;\sum_{p \le q \le p + s_i - 1} x_{i,w,p} \le 1 \;\; (\text{Platz } q), \qquad \sum_i g_i \sum_p x_{i,w,p} \le PL,
$$
$$
\sum_d y_{w,d} \le 1, \qquad x_{i,w,p} \le y_{w,d(i)} .
$$

**Zielfunktion:** die geladenen TEU maximieren,
$$
\max \sum_{i,w,p} s_i \, x_{i,w,p} .
$$
Trivial ist $\sum s_i x \le \min\big(\textstyle\sum_i s_i,\; 3W\big)$; wird diese Schranke erreicht, ist das Optimum ohne Löser bewiesen. Die **Schranke ohne Zielreinheit** lässt $y$ und die letzte
Bedingung weg (gemischte Wagen); der Unterschied der Optima ist der **Preis der Zielreinheit**.

**Vergleich über Tage.** Für Verfahren $A$ gegen die Referenz $B$ auf denselben Tagen $\ell = 1, \dots, S$ (beide zulässig) ist $\Delta_\ell = z_A^{(\ell)} - z_B^{(\ell)}$ der Gewinn in TEU;
berichtet werden Mittel, Median und die Anteile der Tage mit $\Delta_\ell > 0$ (mehr), $= 0$ (gleich), $< 0$ (weniger). Ein Unterschied gilt als klar, wenn $|\bar\Delta| > 2\,\mathrm{SE}(\Delta)$
mit dem Standardfehler der gepaarten Differenz.

Implementiert in `bahn_rules.py` (Bewertung und Regeln), `bahn_exact.py` (CP-SAT) und `bahn_evaluation.py` (Vergleiche).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
