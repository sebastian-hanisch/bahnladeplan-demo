"""Regler-Grenzen, Vorgaben und feste Parameter der Bahn-Ladeplan-Demo.

Ein Zug aus Wagen mit je drei Plätzen (60 Fuß = 3 TEU), Container zu 20 oder 40 Fuß mit Gewicht und Zielterminal; jeder Wagen fährt zu genau einem Ziel. Alles ganzzahlig."""

# --- Regler: Grenzen und Vorgaben ---
N_WAGONS_RANGE, N_WAGONS_DEFAULT = (8, 30), 16
N_DESTS_RANGE, N_DESTS_DEFAULT = (1, 10), 4
OFFER_PCT_RANGE, OFFER_PCT_STEP, OFFER_PCT_DEFAULT = (80, 150), 10, 120        # Angebot in % der Zugkapazität (in TEU)
SHARE40_PCT_RANGE, SHARE40_PCT_STEP, SHARE40_PCT_DEFAULT = (0, 100), 10, 50    # Anteil der 40-Fuß-Container in %
PAYLOAD_RANGE, PAYLOAD_STEP, PAYLOAD_DEFAULT = (40, 70), 5, 60                 # Wagenlast in Tonnen
SEED_RANGE, SEED_DEFAULT = (0, 9999), 35

# --- feste Parameter ---
PLACES = 3                              # Plätze (zu 20 Fuß) je Wagen
WEIGHT_20 = (6, 24)                     # Gewicht eines 20-Fuß-Containers in t (gleichverteilt, ganzzahlig)
WEIGHT_40 = (8, 30)
EXACT_LIVE_LIMIT_SECONDS = 4            # Exakt in der Hauptansicht
EXACT_LONG_LIMIT_SECONDS = 30           # Exakt-Tab auf Knopfdruck
SAMPLE_LIMIT_SECONDS = 2                # je Instanz in Stichprobe und Kurve

# --- Verfahren (Schlüssel -> Beschriftung, in Anzeigereihenfolge); "Reihenfolge" ist die Referenz aller Deltas ---
STRAT_FIFO, STRAT_FFD, STRAT_BLOCKS, STRAT_EXACT = "fifo", "ffd", "blocks", "exact"
STRATEGY_LABELS = {
    STRAT_FIFO: "📥 Reihenfolge",
    STRAT_FFD: "📦 Größe zuerst",
    STRAT_BLOCKS: "🧱 Wagenblöcke",
    STRAT_EXACT: "🧮 Exakt",
}
STRATEGY_PLAIN = {STRAT_FIFO: "Reihenfolge", STRAT_FFD: "Größe zuerst", STRAT_BLOCKS: "Wagenblöcke", STRAT_EXACT: "Exakt"}     # ohne Emoji (PDF, Diagramme)
STRATEGY_SHORT = {STRAT_FIFO: "Reihenfolge", STRAT_FFD: "Größe<br>zuerst", STRAT_BLOCKS: "Wagen-<br>blöcke", STRAT_EXACT: "Exakt"}
STRATEGY_KEYS = tuple(STRATEGY_LABELS)
BASELINE = STRAT_FIFO

# --- Presets: eine gemeinsame Instanznummer (Seed); Angebot, Ziele und Wagenlast wechseln (Werte vorläufig, AP 6 stimmt sie gegen die Abnahmekriterien ab) ---
_BASE = dict(n_wagons=N_WAGONS_DEFAULT, share40_pct=SHARE40_PCT_DEFAULT, seed=SEED_DEFAULT)
PRESETS = {
    "Locker": dict(_BASE, n_dests=4, offer_pct=80, payload=60),
    "Üblich": dict(_BASE, n_dests=4, offer_pct=120, payload=60),
    "Viele Ziele": dict(_BASE, n_dests=8, offer_pct=120, payload=60),
    "Schwer": dict(_BASE, n_dests=4, offer_pct=120, payload=40, share40_pct=30),
    "Ganz lang": dict(_BASE, n_dests=10, offer_pct=120, payload=60),
}

# --- Stichprobe und Kurve über die Zahl der Zielterminals (Instanzen mit den Seeds 0.. , nicht der eingestellte Seed) ---
SAMPLE_LISTS = 20
CURVE_LISTS, CURVE_LISTS_LARGE = 8, 6
CURVE_POINTS = (1, 2, 3, 4, 6, 8, 10)
CURVE_POINTS_LARGE = (1, 2, 4, 7, 10)
CURVE_LARGE_WAGONS = 20                 # ab so vielen Wagen weniger Punkte und Instanzen (Laufzeit)
VERDICT_Z = 2.0                         # "klar" heißt gepaarte Differenz > VERDICT_Z Standardfehler
KANTE_PRICE = 1.0                       # Preis der Zielreinheit (TEU), ab dem die Kante gemeldet wird

# --- Darstellung ---
DEST_COLORS = ("#2a6fb0", "#2e7d4f", "#c77700", "#7a3fb0", "#b0356a", "#1a8a8a", "#8a6d1a", "#5b7f2a", "#a0452a", "#4b5563")     # Ziel 1..10
DEST_COLOR_NAMES = ("blau", "grün", "orange", "violett", "rosa", "türkis", "ocker", "oliv", "rostrot", "schiefer")
EMPTY_CELL_COLOR = "rgba(128,136,149,0.14)"      # leerer Platz: halbtransparentes Mittelgrau (hell und dunkel lesbar)
MARKER_LINE_COLOR = "#808895"           # mittleres Grau: auf hellem und dunklem Grund sichtbar
STRATEGY_COLORS = {STRAT_FIFO: "#8a94a3", STRAT_FFD: "#c77700", STRAT_BLOCKS: "#2a6fb0", STRAT_EXACT: "#2e7d4f"}
MIXED_COLOR = "#7a3fb0"
OUTCOME_COLORS = {"better": "#2e7d4f", "equal": "#b8bfc9", "worse": "#c0392b"}
CHART_HEIGHT = 420
STRATEGY_DESCRIPTIONS = {
    STRAT_FIFO: "**Reihenfolge.** Die Container in Ankunftsreihenfolge: in den ersten Wagen desselben Ziels, in dem noch Platz und Last frei sind, sonst in einen neuen Wagen. Der Alltag ohne "
                "Plan und die Referenz aller Vergleiche.",
    STRAT_FFD: "**Größe zuerst.** Erst die 40-Fuß-Container, jeweils die schwereren zuerst; jeder in den Wagen seines Ziels mit dem wenigsten Restplatz. Die bekannte Packregel, "
               "aber ohne Blick darauf, wie viele Wagen jedes Ziel braucht.",
    STRAT_BLOCKS: "**Wagenblöcke.** Je Ziel werden die Container mit „Größe zuerst“ in eigene Wagen gepackt (so viele, wie nötig); danach fährt der Zug mit den vollsten Wagen. Trifft das "
                  "Optimum in fast allen Fällen.",
    STRAT_EXACT: "**Exakt (CP-SAT).** Die größte Zahl geladener TEU, die Plätze, Nachbarschaft der 40-Fuß-Container, Wagenlast und Zielreinheit einhält, mit Beweis oder Intervall "
                 "[beste Lösung, obere Schranke], wenn das Zeitlimit nicht reicht.",
}

# --- Ansicht ---
RIGHT_VIEW_KEYS = (STRAT_FFD, STRAT_BLOCKS, STRAT_EXACT)     # im Zug-Blick steht links immer die Reihenfolge
VIEW_DEFAULT = STRAT_EXACT
