"""Bewertung eines Ladeplans und die drei konstruktiven Regeln (Reihenfolge, Größe zuerst, Wagenblöcke).

Ein Plan ist ein Tupel von Wagen (genau n_wagons); ein Wagen ist ein Tupel von (Startplatz, Container-Index), nach Startplatz sortiert. Der Index zeigt in inst.boxes. Ein 40-Fuß-Container belegt
Startplatz und den nächsten Platz. Was nicht im Plan steht, wird nicht geladen (bleibt für den nächsten Zug)."""

from dataclasses import dataclass

import bahn_constants as C
from bahn_scenario import teu


@dataclass(frozen=True)
class Evaluation:
    loaded: int             # geladene TEU
    n_boxes: int            # geladene Container
    max_load: int           # größte Wagenlast in t
    violations: tuple       # Namen der verletzten Bedingungen: "Wagen", "Container", "Platz", "Last", "Ziel"

    @property
    def valid(self):
        return not self.violations


def evaluate(inst, plan):
    """Geladene TEU und verletzte Bedingungen: Wagenzahl, jeder Container höchstens einmal, Plätze im Wagen und ohne Überlappung, Wagenlast, ein Ziel je Wagen."""
    bad = []
    if len(plan) != inst.n_wagons:
        bad.append("Wagen")
    seen, loaded, n, max_load = set(), 0, 0, 0
    for wagon in plan:
        free = [True] * C.PLACES
        load, dests = 0, set()
        for start, i in wagon:
            if not 0 <= i < len(inst.boxes) or i in seen:
                if "Container" not in bad:
                    bad.append("Container")
                continue
            seen.add(i)
            b = inst.boxes[i]
            span = range(start, start + teu(b))
            if start < 0 or start + teu(b) > C.PLACES or not all(free[q] for q in span):
                if "Platz" not in bad:
                    bad.append("Platz")
            else:
                for q in span:
                    free[q] = False
            load += b[1]
            dests.add(b[2])
            loaded += teu(b)
            n += 1
        if load > inst.payload and "Last" not in bad:
            bad.append("Last")
        if len(dests) > 1 and "Ziel" not in bad:
            bad.append("Ziel")
        max_load = max(max_load, load)
    return Evaluation(loaded, n, max_load, tuple(bad))


def wagon_dest(inst, wagon):
    """Ziel des Wagens (None, wenn leer)."""
    return inst.boxes[wagon[0][1]][2] if wagon else None


def free_places(wagon, inst):
    return C.PLACES - sum(teu(inst.boxes[i]) for _, i in wagon)


# ---------------------------------------------------------------------------------------------------
# Konstruktive Regeln
# ---------------------------------------------------------------------------------------------------
class _Wagon:
    def __init__(self):
        self.dest, self.free, self.load, self.items = None, [True] * C.PLACES, 0, []

    def slot(self, b, payload):
        """Erster Startplatz, an dem der Container passt (Plätze frei, Last ok), sonst None."""
        if self.load + b[1] > payload:
            return None
        n = teu(b)
        for p in range(C.PLACES - n + 1):
            if all(self.free[p:p + n]):
                return p
        return None

    def put(self, i, b, p):
        for q in range(p, p + teu(b)):
            self.free[q] = False
        self.load += b[1]
        self.dest = b[2]
        self.items.append((p, i))

    @property
    def fill(self):
        return sum(1 for f in self.free if not f)

    def frozen(self):
        return tuple(sorted(self.items))


def _place(inst, order, choose):
    """Container der Reihe nach in einen Wagen mit gleichem Ziel oder einen leeren; choose 'first' (erster passender, bevorzugt gleiches Ziel) oder 'best' (wenigster Restplatz)."""
    wagons = [_Wagon() for _ in range(inst.n_wagons)]
    for i in order:
        b = inst.boxes[i]
        cands = []
        for w in wagons:
            if w.dest == b[2] or w.dest is None:
                p = w.slot(b, inst.payload)
                if p is not None:
                    cands.append((w, p))
        if not cands:
            continue
        if choose == "first":
            w, p = cands[0]                                   # Wagen füllen sich der Reihe nach: Wagen desselben Ziels stehen immer vor den leeren
        else:
            w, p = min(cands, key=lambda c: (c[0].dest is None, C.PLACES - c[0].fill - teu(b)))
        w.put(i, b, p)
    return tuple(w.frozen() for w in wagons)


def _size_order(inst):
    """Große zuerst, dann schwere zuerst, dann Ankunftsreihenfolge (deterministisch)."""
    return sorted(range(len(inst.boxes)), key=lambda i: (-teu(inst.boxes[i]), -inst.boxes[i][1], i))


def fifo(inst):
    """Reihenfolge: Ankunftsreihenfolge, erster passender Wagen."""
    return _place(inst, range(len(inst.boxes)), "first")


def ffd(inst):
    """Größe zuerst: 40-Fuß und schwere zuerst, Wagen mit dem wenigsten Restplatz."""
    return _place(inst, _size_order(inst), "best")


def blocks(inst):
    """Wagenblöcke: je Ziel die Container per Größe-zuerst in eigene Wagen packen (unbegrenzt viele), dann die Wagen mit der größten Füllung wählen, bis der Zug voll ist."""
    made = []
    for d in range(inst.n_dests):
        ws = []
        for i in [i for i in _size_order(inst) if inst.boxes[i][2] == d]:
            b = inst.boxes[i]
            best = None
            for w in ws:
                p = w.slot(b, inst.payload)
                if p is not None and (best is None or w.fill > best[0].fill):
                    best = (w, p)
            if best is None:
                w = _Wagon()
                p = w.slot(b, inst.payload)
                if p is None:
                    continue                                  # der Container passt in keinen Wagen (Gewicht über der Wagenlast)
                ws.append(w)
                best = (w, p)
            best[0].put(i, b, best[1])
        made += ws
    made.sort(key=lambda w: (-w.fill, -w.load))
    chosen = [w.frozen() for w in made[:inst.n_wagons]]
    return tuple(chosen) + ((),) * (inst.n_wagons - len(chosen))


def arrival_load(inst):
    """Zur Einordnung: TEU, die die Reihenfolge lädt (Kurzform)."""
    return evaluate(inst, fifo(inst)).loaded
