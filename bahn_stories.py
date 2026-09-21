"""Abnahmekriterien der Presets (Plan, Abschnitt 7): Welche Geschichte erzählt jedes Beispielszenario, und woran erkennt man, dass sie trägt?

Einzige Quelle für `tools/tune_presets.py` (Abstimmung) und `tests/test_preset_stories.py` (Abnahme). Jedes Kriterium ist eine Aussage über ein Tupel von `ListResult`s
(bahn_evaluation): über viele Tage die Aussage im MITTEL (`criteria`), über den EINEN Tag des Presets die Aussage an diesem Tag (`holds`). So wird dieselbe Geschichte an der Grundgesamtheit
UND am gewählten Tag geprüft: das Preset soll typisch sein, nicht der schönste Einzelfall. Geladene TEU sind ganze Zahlen; ein Verfahren ohne zulässigen Plan zählt in keinem Mittelwert.
Der Exakt-Wert kann bei Zeitlimit eine UNTERE Schranke des Optimums sein; Schwellen für ihn sind so gewählt, dass sie auch auf einem langsamen Rechner (CI) halten."""

import statistics

import bahn_constants as C
import bahn_evaluation as E

F_, D_, B_, X_ = C.STRAT_FIFO, C.STRAT_FFD, C.STRAT_BLOCKS, C.STRAT_EXACT

# Kennzahlen, an denen 'typisch' gemessen wird: (Preset, Verfahren)
TYPICAL = (("Üblich", F_), ("Üblich", B_), ("Viele Ziele", F_), ("Viele Ziele", B_), ("Schwer", B_), ("Schwer", X_), ("Ganz lang", F_), ("Ganz lang", X_))


def _mean(results, key):
    m = E.mean_loaded(results, key)
    return float("nan") if m is None else m


def _fmt(x):
    return "-" if x is None else f"{x:.2f}"


def _all_valid(results):
    return all(E.valid_share(results, k) == 1.0 for k in C.STRATEGY_KEYS)


def _equal_share(results, a, b):
    return sum(1 for r in results if r.valid[a] and r.valid[b] and r.loaded[a] == r.loaded[b]) / len(results)


def _better_share(results, a, b):
    """Anteil der Tage, an denen a mehr lädt als b (beide zulässig)."""
    return sum(1 for r in results if r.valid[a] and r.valid[b] and r.loaded[a] > r.loaded[b]) / len(results)


def criteria(name, results):
    """Mittelwert-Kriterien über viele Tage. Rückgabe: Liste (erfüllt, Text)."""
    offered = statistics.fmean(r.offered for r in results)
    if name == "Locker":
        means = [_mean(results, k) for k in C.STRATEGY_KEYS]
        return [(_all_valid(results), "alle vier Verfahren zulässig an allen Tagen"),
                (_mean(results, F_) >= 0.95 * offered, f"Reihenfolge lädt >= 95 % des Angebots: {_mean(results, F_):.1f} von {offered:.1f}"),
                (max(means) - min(means) <= 0.5, f"die Verfahren liegen im Mittel höchstens 0,5 TEU auseinander: {max(means) - min(means):.2f}")]
    if name == "Üblich":
        return [(_mean(results, B_) - _mean(results, F_) >= 1.5, f"Wagenblöcke laden >= 1,5 TEU mehr als die Reihenfolge: {_mean(results, B_) - _mean(results, F_):.2f}"),
                (_equal_share(results, X_, B_) >= 0.9, f"Exakt = Wagenblöcke an >= 90 % der Tage: {_equal_share(results, X_, B_) * 100:.0f} %"),
                (_mean(results, B_) >= 45, f"Wagenblöcke laden >= 45 von {C.PLACES * C.N_WAGONS_DEFAULT} Plätzen: {_mean(results, B_):.1f}")]
    if name == "Viele Ziele":
        price = E.mean_price(results)
        return [(_mean(results, B_) - _mean(results, F_) >= 2.0, f"Wagenblöcke laden >= 2 TEU mehr als die Reihenfolge: {_mean(results, B_) - _mean(results, F_):.2f}"),
                (price is not None and price >= 1.0, f"Preis der Zielreinheit >= 1 TEU: {_fmt(price)}")]
    if name == "Schwer":
        paired = E.paired(results, X_, B_)
        gain = statistics.fmean(paired) if paired else float("nan")
        return [(gain >= 0.3, f"Exakt lädt im Mittel >= 0,3 TEU mehr als Wagenblöcke: {gain:.2f}"),
                (_better_share(results, X_, B_) >= 0.25, f"Exakt lädt an >= 25 % der Tage mehr als Wagenblöcke: {_better_share(results, X_, B_) * 100:.0f} %")]
    if name == "Ganz lang":
        price = E.mean_price(results)
        unproven = E.unproven_count(results) / len(results)
        return [(unproven >= 0.3, f"Exakt ist an >= 30 % der Tage nicht bewiesen: {unproven * 100:.0f} %"),
                (price is not None and price >= 1.5, f"Preis der Zielreinheit >= 1,5 TEU: {_fmt(price)}")]
    raise KeyError(name)


def holds(name, r):
    """Gilt die Geschichte an dem EINEN Tag (`ListResult`), den das Preset zeigt?"""
    ld, ok = r.loaded, r.valid
    if name == "Locker":
        vals = [ld[k] for k in C.STRATEGY_KEYS]
        return all(ok.values()) and ld[F_] >= 0.95 * r.offered and max(vals) - min(vals) <= 1
    if name == "Üblich":
        return ok[F_] and ok[B_] and ok[X_] and ld[B_] - ld[F_] >= 2 and ld[X_] == ld[B_]
    if name == "Viele Ziele":
        return ok[F_] and ok[B_] and ok[X_] and ld[B_] - ld[F_] >= 2 and r.mixed_upper - ld[X_] >= 1
    if name == "Schwer":
        return ok[B_] and ok[X_] and ld[X_] - ld[B_] >= 1
    if name == "Ganz lang":
        return ok[X_] and r.mixed_upper - ld[X_] >= 2
    raise KeyError(name)


def key_values(name, results):
    """Die Kennzahlen dieses Presets aus TYPICAL als {Verfahren: Mittel}."""
    return {k: _mean(results, k) for n, k in TYPICAL if n == name}
