"""Testhilfen: unabhängige Vergleichsimplementierung (Brute Force) und Instanz-Generatoren."""
import random

import bahn_constants as C
import bahn_scenario as SC
from bahn_scenario import teu


def random_instance(seed, max_wagons=30):
    """Zufällige Instanz innerhalb der Reglergrenzen der App."""
    rng = random.Random(seed)
    return SC.make_instance(rng.randint(C.N_WAGONS_RANGE[0], max_wagons), rng.randint(*C.N_DESTS_RANGE), rng.choice(range(80, 151, 10)), rng.choice(range(0, 101, 10)),
                            rng.choice(range(40, 71, 5)), rng.randint(0, 9999))


def tiny_instance(seed, n_wagons=2, max_boxes=6, purity_matters=True):
    """Winzige Instanz für Brute Force: wenige Wagen, wenige Container, gerne mehrere Ziele und knappe Last."""
    rng = random.Random(seed)
    n = rng.randint(3, max_boxes)
    boxes = []
    for _ in range(n):
        is40 = rng.random() < 0.4
        boxes.append((40 if is40 else 20, rng.randint(*(C.WEIGHT_40 if is40 else C.WEIGHT_20)), rng.randrange(3 if purity_matters else 1)))
    return SC.custom_instance(n_wagons, 3 if purity_matters else 1, rng.choice([25, 35, 45, 60]), boxes)


def brute_force(inst, purity=True):
    """Größte Zahl ladbarer TEU durch vollständiges Durchprobieren (Container für Container: nicht laden oder in Wagen w auf Startplatz p), unabhängig vom CP-SAT-Modell."""
    boxes = inst.boxes
    W = inst.n_wagons
    best = 0

    def rec(i, free, load, dest, loaded):
        nonlocal best
        if loaded + sum(teu(b) for b in boxes[i:]) <= best:
            return
        if i == len(boxes):
            best = max(best, loaded)
            return
        b = boxes[i]
        n = teu(b)
        for w in range(W):
            if load[w] + b[1] > inst.payload:
                continue
            if purity and dest[w] is not None and dest[w] != b[2]:
                continue
            for p in range(C.PLACES - n + 1):
                if all(free[w][p:p + n]):
                    for q in range(p, p + n):
                        free[w][q] = False
                    old_dest = dest[w]
                    load[w] += b[1]
                    dest[w] = b[2]
                    rec(i + 1, free, load, dest, loaded + n)
                    dest[w] = old_dest
                    load[w] -= b[1]
                    for q in range(p, p + n):
                        free[w][q] = True
        rec(i + 1, free, load, dest, loaded)

    rec(0, [[True] * C.PLACES for _ in range(W)], [0] * W, [None] * W, 0)
    return best
