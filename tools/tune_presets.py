"""Preset-Abstimmung per Sweep: traegt die Geschichte jedes Presets im MITTEL ueber viele Tage, und an dem einen Tag, den das Preset zeigt?

Aufruf (im Projektordner): ./venv/Scripts/python.exe tools/tune_presets.py <modus>
  population   Grundgesamtheit (Seeds 0-19, 2 s Limit): Mittelwert-Kriterien aller Presets
  seeds        je Seed 0..59: welche Presets tragen an diesem Tag, Abstand zum Median der Kennzahlen; nennt die besten gemeinsamen Seeds

Grundsaetze (aus Schiffsstau-, Kaiplatz- und Fahrzeug-Demo): den Seed nicht nach dem schoensten Einzelfall waehlen, sondern nahe am MEDIAN (die Verteilungen sind schief); Kriterien an der
Grundgesamtheit messen; alle Presets teilen sich EINE Tagesnummer. Der Rechner rechnet mit max_workers=2: viele Prozesse mit je 8 Loeser-Threads verfaelschen die Zeitlimits (weniger bewiesene
Optima) - die Messung haengt an der Rechenlast."""
import math
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, ".")
import bahn_constants as C
import bahn_evaluation as E
import bahn_stories as ST

NAMES = list(C.PRESETS)
SEEDS = range(60)
LIMIT = C.SAMPLE_LIMIT_SECONDS


def _cell(args):
    name, seed = args
    p = C.PRESETS[name]
    return name, seed, E.run_list(p["n_wagons"], p["n_dests"], p["offer_pct"], p["share40_pct"], p["payload"], seed, LIMIT)


def _table(seeds=SEEDS):
    with ProcessPoolExecutor(max_workers=2) as ex:
        cells = list(ex.map(_cell, [(n, s) for n in NAMES for s in seeds], chunksize=2))
    table = {n: {} for n in NAMES}
    for n, s, r in cells:
        table[n][s] = r
    return table


def cmd_population():
    table = _table(range(C.SAMPLE_LISTS))
    for name in NAMES:
        res = tuple(table[name][s] for s in range(C.SAMPLE_LISTS))
        print(f"\n### {name}")
        for ok, text in ST.criteria(name, res):
            print(("  OK   " if ok else "  FAIL ") + text)
        print("  Kennzahlen:", {k: round(v, 2) for k, v in ST.key_values(name, res).items()}, "| unbewiesen:", E.unproven_count(res))


def _median(table):
    return {(n, k): statistics.median(table[n][s].loaded[k] for s in table[n]) for n, k in ST.TYPICAL}


def _score(table, med, seed):
    return sum(abs(math.log(table[n][seed].loaded[k] + 0.5) - math.log(med[(n, k)] + 0.5)) for n, k in ST.TYPICAL)


def cmd_seeds():
    table = _table()
    med = _median(table)
    for name in NAMES:
        good = [s for s in SEEDS if ST.holds(name, table[name][s])]
        print(f"{name}: traegt an {len(good)} von {len(SEEDS)} Tagen")
    allgood = sorted((s for s in SEEDS if all(ST.holds(n, table[n][s]) for n in NAMES)), key=lambda s: _score(table, med, s))
    print("\nalle fuenf tragen an:", allgood[:12])
    for s in allgood[:6]:
        print(f"  seed {s:3d} | Abstand zum Median {_score(table, med, s):.2f} | " + ", ".join(f"{n}: " + "/".join(str(table[n][s].loaded[k]) for k in C.STRATEGY_KEYS) + f" (Schranke {table[n][s].mixed_upper})" for n in NAMES))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "population"
    {"population": cmd_population, "seeds": cmd_seeds}.get(mode, lambda: sys.exit(__doc__))()
