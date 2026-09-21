"""Auswertung: ein Zug mit allen Verfahren, Stichprobe über viele Instanzen, Kurve über die Zahl der Zielterminals, gepaarte Differenz, Verteilung und Urteil.

Reine Rechnung ohne Streamlit. Kosten sind hier ein GEWINN: geladene TEU (mehr ist besser). Ein Plan zählt nur, wenn er alle Bedingungen einhält (`valid`). Alle Vergleiche sind gepaart
(dieselben Instanzen); Unterschied = Verfahren minus Referenz, positiv = mehr geladen. Der Preis der Zielreinheit ist die Schranke ohne Reinheit minus das Optimum mit Reinheit."""

import math
import statistics
from dataclasses import dataclass

import bahn_constants as C
import bahn_exact as X
import bahn_rules as R
import bahn_scenario as SC


# ---------------------------------------------------------------------------------------------------
# Ein Zug, alle Verfahren
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Outcome:
    key: str
    label: str
    plan: object
    evaluation: object
    exact: object = None    # nur beim Exakt-Verfahren: das ExactResult

    @property
    def loaded(self):
        return self.evaluation.loaded

    @property
    def valid(self):
        return self.evaluation.valid

    @property
    def violations(self):
        return self.evaluation.violations


def utilization(inst, loaded):
    """Anteil der belegten Plätze in % der Kapazität."""
    return 100.0 * loaded / SC.capacity(inst)


def leftover(inst, loaded):
    """Angebotene TEU, die nicht mitfahren (bleiben für den nächsten Zug)."""
    return SC.offered(inst) - loaded


def run_methods(inst, exact_limit=C.EXACT_LIVE_LIMIT_SECONDS):
    """Alle vier Verfahren auf demselben Zug. Exakt läuft mit `exact_limit` Sekunden und liefert bei Nichtbeweis ein Intervall (`outcome.exact`)."""
    out = []
    for key, rule in ((C.STRAT_FIFO, R.fifo), (C.STRAT_FFD, R.ffd), (C.STRAT_BLOCKS, R.blocks)):
        plan = rule(inst)
        out.append(Outcome(key, C.STRATEGY_LABELS[key], plan, R.evaluate(inst, plan)))
    out.append(exact_outcome(inst, exact_limit))
    return tuple(out)


def exact_outcome(inst, exact_limit=C.EXACT_LIVE_LIMIT_SECONDS):
    """Nur das Exakt-Verfahren (für das lange Nachrechnen im Exakt-Tab): dieselbe Outcome-Form wie in `run_methods`."""
    res = X.solve_exact(inst, exact_limit)
    return Outcome(C.STRAT_EXACT, C.STRATEGY_LABELS[C.STRAT_EXACT], res.plan, R.evaluate(inst, res.plan), res)


def outcome_of(outcomes, key):
    return next(o for o in outcomes if o.key == key)


def mixed_bound(inst, limit=C.SAMPLE_LIMIT_SECONDS):
    """Obere Schranke der TEU ohne Zielreinheit (gemischte Wagen erlaubt) und ob sie bewiesen ist."""
    res = X.solve_exact(inst, limit, purity=False)
    return res.upper, res.proven


def exact_interval(outcome):
    """(beste Lösung, obere Schranke, bewiesen) des Exakt-Ergebnisses."""
    res = outcome.exact
    return res.value, res.upper, res.proven


@dataclass(frozen=True)
class Row:
    key: str
    label: str
    loaded: int
    utilization: float
    leftover: int
    n_used_wagons: int      # Wagen mit Ladung
    max_load: int
    valid: bool
    violations: tuple
    delta_vs_baseline: int  # mein Wert minus Referenz (TEU, positiv = mehr geladen)


def comparison_rows(inst, outcomes, baseline=C.BASELINE):
    ref = outcome_of(outcomes, baseline).loaded
    rows = []
    for o in outcomes:
        used = sum(1 for w in o.plan if w)
        rows.append(Row(o.key, o.label, o.loaded, utilization(inst, o.loaded), leftover(inst, o.loaded), used, o.evaluation.max_load, o.valid, o.violations, o.loaded - ref))
    return tuple(rows)


# ---------------------------------------------------------------------------------------------------
# Stichprobe: viele Instanzen
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ListResult:
    seed: int
    offered: int
    loaded: dict            # Verfahren -> geladene TEU
    valid: dict             # Verfahren -> hält alle Bedingungen ein
    proven: bool            # Exakt: bewiesen optimal
    exact_status: str
    mixed_upper: int        # Schranke ohne Zielreinheit


def run_list(n_wagons, n_dests, offer_pct, share40_pct, payload, seed, exact_limit):
    inst = SC.make_instance(n_wagons, n_dests, offer_pct, share40_pct, payload, seed)
    outs = run_methods(inst, exact_limit)
    exact = outcome_of(outs, C.STRAT_EXACT)
    upper, _ = mixed_bound(inst, exact_limit)
    return ListResult(seed, SC.offered(inst), {o.key: o.loaded for o in outs}, {o.key: o.valid for o in outs}, exact.exact.proven, exact.exact.status, max(upper, exact.loaded))


def sample(n_wagons, n_dests, offer_pct, share40_pct, payload, n_lists=C.SAMPLE_LISTS, exact_limit=C.SAMPLE_LIMIT_SECONDS, progress=None):
    """Instanzen mit den Seeds 0..n_lists-1 (unabhängig vom eingestellten Seed) mit den eingestellten Zug- und Angebotswerten, alle Verfahren je Instanz."""
    out = []
    for i, seed in enumerate(range(n_lists)):
        out.append(run_list(n_wagons, n_dests, offer_pct, share40_pct, payload, seed, exact_limit))
        if progress:
            progress((i + 1) / n_lists)
    return tuple(out)


def curve_plan(n_wagons):
    """(Punkte = Zahl der Ziele, Anzahl Instanzen): ab CURVE_LARGE_WAGONS Wagen weniger von beidem (Laufzeit)."""
    if n_wagons >= C.CURVE_LARGE_WAGONS:
        return C.CURVE_POINTS_LARGE, C.CURVE_LISTS_LARGE
    return C.CURVE_POINTS, C.CURVE_LISTS


@dataclass(frozen=True)
class Curve:
    points: tuple           # Zahl der Zielterminals
    lists: dict             # Punkt -> Tupel von ListResult (gleiche Seeds an jedem Punkt)
    n_lists: int


def curve_over_dests(n_wagons, offer_pct, share40_pct, payload, exact_limit=C.SAMPLE_LIMIT_SECONDS, points=None, n_lists=None, progress=None):
    """Geladene TEU über der Zahl der Zielterminals: dieselben Seeds an jedem Punkt."""
    default_points, default_lists = curve_plan(n_wagons)
    points = tuple(points or default_points)
    n_lists = n_lists or default_lists
    lists, done, total = {}, 0, len(points) * n_lists
    for d in points:
        rows = []
        for seed in range(n_lists):
            rows.append(run_list(n_wagons, d, offer_pct, share40_pct, payload, seed, exact_limit))
            done += 1
            if progress:
                progress(done / total)
        lists[d] = tuple(rows)
    return Curve(points, lists, n_lists)


# ---------------------------------------------------------------------------------------------------
# Statistik über Instanzen (gepaart)
# ---------------------------------------------------------------------------------------------------
def _se(xs):
    return statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0


def values(results, key):
    """Geladene TEU des Verfahrens über die Instanzen, in denen es einen zulässigen Plan hat."""
    return [r.loaded[key] for r in results if r.valid[key]]


def valid_share(results, key):
    return sum(1 for r in results if r.valid[key]) / len(results)


def mean_loaded(results, key):
    v = values(results, key)
    return statistics.fmean(v) if v else None


def median_loaded(results, key):
    v = values(results, key)
    return statistics.median(v) if v else None


def unproven_count(results):
    """Zahl der Instanzen, in denen das Exakt-Ergebnis nicht bewiesen ist (der Wert ist dort eine untere Schranke des Optimums)."""
    return sum(1 for r in results if not r.proven)


def paired(results, key, reference):
    """Gepaarte Differenz key - reference über die Instanzen, in denen BEIDE zulässig sind (TEU, positiv = key lädt mehr)."""
    return [r.loaded[key] - r.loaded[reference] for r in results if r.valid[key] and r.valid[reference]]


def purity_price(results):
    """Preis der Zielreinheit je Instanz: Schranke ohne Reinheit minus bestes gefundenes Optimum mit Reinheit (bei unbewiesenem Exakt eine Obergrenze des Preises)."""
    return [r.mixed_upper - r.loaded[C.STRAT_EXACT] for r in results if r.valid[C.STRAT_EXACT]]


def mean_price(results):
    v = purity_price(results)
    return statistics.fmean(v) if v else None


@dataclass(frozen=True)
class Distribution:
    key: str
    n: int                  # Instanzen, in denen beide zulässig sind
    better: float           # Anteile (0..1) gegen die Referenz
    equal: float
    worse: float
    mean_gain: float        # TEU je Instanz mehr als die Referenz
    median_gain: float


def distribution(results, key, reference=C.BASELINE):
    d = paired(results, key, reference)
    n = len(d)
    if n == 0:
        return Distribution(key, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
    better, worse = sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)
    return Distribution(key, n, better / n, (n - better - worse) / n, worse / n, statistics.fmean(d), statistics.median(d))


@dataclass(frozen=True)
class Verdict:
    kind: str               # "better" (mehr geladen) | "worse" | "unclear" | "none" (keine gemeinsam zulässige Instanz)
    diff: float             # Verfahren minus Referenz, TEU je Instanz (positiv = mehr geladen)
    se: float
    pct: object             # Unterschied in % der Referenz; None, wenn die Referenz im Mittel 0 hat
    n: int
    worse_share: float      # Anteil der Instanzen, in denen das Verfahren weniger lädt als die Referenz


def verdict(results, key, reference=C.BASELINE):
    """Bewertung gegen die Referenz. 'Klar' heißt: Unterschied > VERDICT_Z Standardfehler der gepaarten Differenz; sonst 'unclear'; 'none', wenn keine Instanz beide zulässig hat."""
    d = paired(results, key, reference)
    if not d:
        return Verdict("none", 0.0, 0.0, None, 0, 0.0)
    diff, se = statistics.fmean(d), _se(d)
    ref_mean = statistics.fmean(r.loaded[reference] for r in results if r.valid[key] and r.valid[reference])
    if se == 0:
        kind = "unclear" if diff == 0 else ("better" if diff > 0 else "worse")
    else:
        kind = "unclear" if abs(diff) <= C.VERDICT_Z * se else ("better" if diff > 0 else "worse")
    return Verdict(kind, diff, se, 100.0 * diff / ref_mean if ref_mean else None, len(d), sum(1 for x in d if x < 0) / len(d))


# ---------------------------------------------------------------------------------------------------
# Kurve über die Zahl der Ziele
# ---------------------------------------------------------------------------------------------------
def curve_means(cv, key):
    """Mittlere geladene TEU des Verfahrens je Punkt; None, wo keine Instanz zulässig ist."""
    return tuple(mean_loaded(cv.lists[p], key) for p in cv.points)


def curve_mixed(cv):
    """Mittlere Schranke ohne Zielreinheit je Punkt."""
    return tuple(statistics.fmean(r.mixed_upper for r in cv.lists[p]) for p in cv.points)


def curve_price(cv):
    return tuple(mean_price(cv.lists[p]) for p in cv.points)


def curve_proven(cv):
    """Anteil der Instanzen je Punkt, in denen das Exakt-Ergebnis bewiesen ist."""
    return tuple(1 - unproven_count(cv.lists[p]) / len(cv.lists[p]) for p in cv.points)


def kante(cv, threshold=C.KANTE_PRICE):
    """Kleinste Zahl von Zielen, ab der die Zielreinheit im Mittel mehr als `threshold` TEU kostet; None, wenn nie."""
    for p in sorted(cv.points):
        m = mean_price(cv.lists[p])
        if m is not None and m > threshold:
            return p
    return None
