"""Plotly-Diagramme: Zug-Bild, Kurve über die Zahl der Ziele, Verteilung der Gewinne, Vergleich.

Konventionen des Portfolios: Achsen `fixedrange` (Touch-Scrollen), Vorlage plotly_white, Markerlinien in mittlerem Grau, neutrale Flächen halbtransparent (nichts Weißes im dunklen
Schema), Überschriften stehen als Markdown ÜBER dem Diagramm. Alle Funktionen sind reine Rechnung auf den Ergebnisobjekten; Streamlit kommt hier nicht vor."""

import math

import bahn_constants as C
import bahn_evaluation as E
from bahn_scenario import teu

LEGEND_TOP = dict(orientation="h", yanchor="bottom", y=1.02, x=0)
LEGEND_BOTTOM = dict(orientation="h", yanchor="top", y=-0.22, x=0)
PAD = 0.05                          # Abstand zwischen Containern (in Plätzen)
WAGONS_PER_ROW = 8
WAGON_GAP = 0.5                     # Lücke zwischen zwei Wagen (in Plätzen)
ROW_HEIGHT = 1.9                    # Höhe einer Wagenreihe inkl. Beschriftung


def _lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def dest_color(dest):
    return C.DEST_COLORS[dest % len(C.DEST_COLORS)]


def _hover_points(x0, x1, y0, y1, nx=3, ny=3):
    """Unsichtbare Punkte über das ganze Rechteck: Plotly hovert Spuren nach dem nächsten DATENPUNKT, ein einzelner Mittelpunkt träfe nur die Mitte."""
    xs = [x0 + (x1 - x0) * (a + 0.5) / nx for a in range(nx)]
    ys = [y0 + (y1 - y0) * (b + 0.5) / ny for b in range(ny)]
    return [x for _ in ys for x in xs], [y for y in ys for _ in xs]


def wagon_origin(k):
    """Linke obere Ecke von Wagen k im Bild: (x, y) mit Reihen von oben nach unten."""
    row, col = divmod(k, WAGONS_PER_ROW)
    return col * (C.PLACES + WAGON_GAP), -row * ROW_HEIGHT


def train_figure(inst, plan, legend=True):
    """Ein Zug: Wagen als Reihen aus drei Plätzen. Farbe = Zielterminal, Zahl = Gewicht in t (dunkler = schwerer), leere Plätze grau. Unter jedem Wagen die Last in t.
    Hover über das ganze Container-Rechteck."""
    import plotly.graph_objects as go

    fig = go.Figure()
    hx, hy, htext, lx, ly, ltext, wx, wy, wtext = [], [], [], [], [], [], [], [], []
    n_rows = (inst.n_wagons + WAGONS_PER_ROW - 1) // WAGONS_PER_ROW
    for k, wagon in enumerate(plan):
        x0, y0 = wagon_origin(k)
        for p in range(C.PLACES):
            fig.add_shape(type="rect", x0=x0 + p + PAD, x1=x0 + p + 1 - PAD, y0=y0 - 1 + PAD, y1=y0 - PAD, fillcolor=C.EMPTY_CELL_COLOR, line=dict(width=0), layer="below")
        load = sum(inst.boxes[i][1] for _, i in wagon)
        for p, i in wagon:
            length, weight, dest = inst.boxes[i]
            xa, xb = x0 + p + PAD, x0 + p + teu(inst.boxes[i]) - PAD
            fig.add_shape(type="rect", x0=xa, x1=xb, y0=y0 - 1 + PAD, y1=y0 - PAD, fillcolor=dest_color(dest), opacity=0.5 + 0.5 * min(1.0, weight / C.WEIGHT_40[1]),
                          line=dict(color="rgba(128,136,149,0.5)", width=1), layer="below")
            px, py = _hover_points(xa, xb, y0 - 1 + PAD, y0 - PAD)
            hx += px
            hy += py
            htext += [f"<b>Ziel {dest + 1}</b>, {length} Fuß, {weight} t<br>Wagen {k + 1}, Platz {p + 1}" + (f"-{p + teu(inst.boxes[i])}" if length == 40 else "")] * len(px)
            lx.append((xa + xb) / 2)
            ly.append(y0 - 0.5)
            ltext.append(f"{weight}")
        wx.append(x0 + C.PLACES / 2)
        wy.append(y0 - 1.25)
        wtext.append(f"{load} t" if wagon else "leer")
    fig.add_trace(go.Scatter(x=hx, y=hy, mode="markers", marker=dict(size=14, opacity=0), showlegend=False, text=htext, hovertemplate="%{text}<extra></extra>", name="Container"))
    fig.add_trace(go.Scatter(x=lx, y=ly, mode="text", text=ltext, textfont=dict(color="white", size=11), showlegend=False, hoverinfo="skip", name="Gewichte"))
    fig.add_trace(go.Scatter(x=wx, y=wy, mode="text", text=wtext, textfont=dict(size=10), showlegend=False, hoverinfo="skip", name="Wagen"))
    if legend:
        present = sorted({inst.boxes[i][2] for wagon in plan for _, i in wagon})
        for d in present:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=f"Ziel {d + 1}", marker=dict(size=12, symbol="square", color=dest_color(d))))
    width = min(inst.n_wagons, WAGONS_PER_ROW) * (C.PLACES + WAGON_GAP)
    fig.update_layout(template="plotly_white", height=60 + 70 * n_rows + (40 if legend else 0), legend=LEGEND_TOP, showlegend=legend, margin=dict(t=50 if legend else 10, b=10, l=10, r=10),
                      hovermode="closest")
    fig.update_xaxes(range=[-0.1, width], visible=False)
    fig.update_yaxes(range=[-(n_rows - 1) * ROW_HEIGHT - 1.6, 0.1], visible=False)
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Kurve über die Zahl der Ziele
# ---------------------------------------------------------------------------------------------------
def curve_figure(cv, dests_current=None, capacity=None):
    """Geladene TEU über der Zahl der Zielterminals (Mittel über die Instanzen mit zulässigem Plan). Exakt: gefüllter Punkt = in allen Instanzen bewiesen, offener Punkt = in mindestens
    einer nur die beste gefundene Lösung (untere Schranke). Gestrichelt violett: die Schranke ohne Zielreinheit; die Lücke dazu ist der Preis der Reinheit. Gepunktete graue Linie =
    eingestellte Zahl der Ziele."""
    import plotly.graph_objects as go

    fig = go.Figure()
    proven = E.curve_proven(cv)
    for key in C.STRATEGY_KEYS:
        means = E.curve_means(cv, key)
        idx = [i for i, m in enumerate(means) if m is not None]
        if not idx:
            continue
        color, label = C.STRATEGY_COLORS[key], C.STRATEGY_LABELS[key]
        x = [cv.points[i] for i in idx]
        y = [means[i] for i in idx]
        if key == C.STRAT_EXACT:
            symbols = ["circle" if proven[i] == 1 else "circle-open" for i in idx]
            hover = [f"<b>{label}</b><br>{cv.points[i]} Ziele<br>{means[i]:.1f} TEU im Mittel<br>bewiesen in {proven[i] * 100:.0f} % der Instanzen" for i in idx]
        else:
            symbols = ["circle"] * len(idx)
            hover = [f"<b>{label}</b><br>{cv.points[i]} Ziele<br>{means[i]:.1f} TEU im Mittel" for i in idx]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers" if len(idx) > 1 else "markers", name=label, line=dict(color=color, width=2.5), text=hover, hovertemplate="%{text}<extra></extra>",
                                 marker=dict(size=8, symbol=symbols, color=color, line=dict(color=color, width=2))))
    mixed = E.curve_mixed(cv)
    fig.add_trace(go.Scatter(x=list(cv.points), y=list(mixed), mode="lines+markers", name="ohne Zielreinheit (Schranke)", line=dict(color=C.MIXED_COLOR, width=2, dash="dash"),
                             marker=dict(size=6, color=C.MIXED_COLOR), text=[f"<b>Schranke ohne Zielreinheit</b><br>{p} Ziele<br>höchstens {m:.1f} TEU im Mittel" for p, m in zip(cv.points, mixed)],
                             hovertemplate="%{text}<extra></extra>"))
    if dests_current is not None:
        fig.add_vline(x=dests_current, line=dict(color=C.MARKER_LINE_COLOR, width=2, dash="dot"), annotation_text="eingestellt", annotation_position="top", annotation_font=dict(size=11))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT + 20, legend=LEGEND_BOTTOM, margin=dict(t=30, b=140), hovermode="closest", xaxis_title="Zielterminals des Zuges",
                      yaxis_title="geladene TEU (Mittel)")
    fig.update_xaxes(range=[min(cv.points) - 0.5, max(cv.points) + 0.5], tickmode="array", tickvals=list(cv.points))
    values = list(mixed) + [m for k in C.STRATEGY_KEYS for m in E.curve_means(cv, k) if m is not None]
    ymax = max(values + ([capacity] if capacity else []))
    fig.update_yaxes(range=[max(0, math.floor(min(values)) - 2), ymax + 1])          # Liniendiagramm: die Achse beginnt nicht bei 0, sonst verschwinden Unterschiede von wenigen TEU
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Verteilung der Gewinne, Vergleich
# ---------------------------------------------------------------------------------------------------
def distribution_figure(dists):
    """Je Verfahren ein gestapelter Balken: Anteil der Instanzen, in denen es gegen die Reihenfolge mehr / gleich viel / weniger lädt (nur Instanzen, in denen beide zulässig sind)."""
    import plotly.graph_objects as go

    labels = [C.STRATEGY_PLAIN[d.key] for d in dists]
    fig = go.Figure()
    for attr, name in (("better", "lädt mehr als die Reihenfolge"), ("equal", "gleich viel"), ("worse", "lädt weniger als die Reihenfolge")):
        shares = [getattr(d, attr) * 100 for d in dists]
        fig.add_trace(go.Bar(y=labels, x=shares, orientation="h", name=name, marker_color=C.OUTCOME_COLORS[attr], text=[f"{v:.0f} %" if v >= 6 else "" for v in shares],
                             textposition="inside", insidetextanchor="middle", hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:.0f}} % der Instanzen<extra></extra>"))
    fig.update_layout(barmode="stack", template="plotly_white", height=150 + 70 * len(dists), legend=dict(LEGEND_BOTTOM, y=-0.45, traceorder="normal"), margin=dict(t=20, b=110, l=10),
                      xaxis_title="Anteil der Instanzen (%)")
    fig.update_xaxes(range=[0, 100])
    fig.update_yaxes(autorange="reversed")
    return _lock_axes(fig)


def gain_figure(dists):
    """Median-Gewinn neben Mittel-Gewinn je Verfahren (TEU je Instanz mehr als die Reihenfolge): ein Mittelwert weit vom Median heißt, dass wenige Instanzen tragen."""
    import plotly.graph_objects as go

    labels = [C.STRATEGY_SHORT[d.key] for d in dists]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=[d.median_gain for d in dists], name="Median (typische Instanz)", marker_color="#2a6fb0", hovertemplate="<b>%{x}</b><br>Median-Gewinn %{y:.1f} TEU<extra></extra>"))
    fig.add_trace(go.Bar(x=labels, y=[d.mean_gain for d in dists], name="Mittelwert", marker_color="#c77700", hovertemplate="<b>%{x}</b><br>Mittel-Gewinn %{y:.1f} TEU<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=C.MARKER_LINE_COLOR, width=1))
    fig.update_layout(barmode="group", template="plotly_white", height=C.CHART_HEIGHT - 60, legend=LEGEND_BOTTOM, margin=dict(t=20, b=100), yaxis_title="Gewinn (TEU je Instanz)")
    return _lock_axes(fig)


def comparison_figure(inst, outcomes, mixed_upper=None):
    """Geladene TEU je Verfahren für denselben Zug. Gepunktete Linie = Kapazität, gestrichelt violett = Schranke ohne Zielreinheit (falls berechnet). Schraffiert = verletzt eine Bedingung."""
    import plotly.graph_objects as go

    fig = go.Figure()
    labels = [C.STRATEGY_SHORT[o.key] for o in outcomes]
    for label, o in zip(labels, outcomes):
        fig.add_trace(go.Bar(x=[label], y=[o.loaded], marker=dict(color=C.STRATEGY_COLORS[o.key], pattern_shape="" if o.valid else "/", line=dict(color=C.MARKER_LINE_COLOR, width=1)),
                             showlegend=False, text=[str(o.loaded)], textposition="outside",
                             hovertemplate=f"<b>{o.label}</b><br>%{{y}} TEU" + ("" if o.valid else "<br>verletzt: " + ", ".join(o.violations)) + "<extra></extra>"))
    cap = inst_capacity(inst)
    fig.add_hline(y=cap, line=dict(color=C.MARKER_LINE_COLOR, width=1.5, dash="dot"), annotation_text=f"Kapazität {cap}", annotation_position="top left", annotation_font=dict(size=11))
    if mixed_upper is not None:
        fig.add_hline(y=mixed_upper, line=dict(color=C.MIXED_COLOR, width=1.5, dash="dash"), annotation_text=f"ohne Zielreinheit ≤ {mixed_upper}", annotation_position="bottom left",
                      annotation_font=dict(size=11, color=C.MIXED_COLOR))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT - 60, margin=dict(t=30, b=50), barmode="overlay", yaxis_title="geladene TEU")
    fig.update_xaxes(tickangle=0, tickfont=dict(size=10), categoryorder="array", categoryarray=labels)
    fig.update_yaxes(range=[0, cap * 1.12])
    if any(not o.valid for o in outcomes):
        fig.add_annotation(text="Schraffiert = verletzt eine Bedingung (nicht vergleichbar)", xref="paper", yref="paper", x=0, y=-0.2, showarrow=False, xanchor="left",
                           font=dict(size=11, color=C.MARKER_LINE_COLOR))
    return _lock_axes(fig)


def inst_capacity(inst):
    return C.PLACES * inst.n_wagons
