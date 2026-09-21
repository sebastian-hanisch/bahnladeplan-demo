"""Instanz aus den Reglern: Zug, Container (Länge, Gewicht, Ziel). Ganzzahlig, deterministisch aus dem Seed."""

import random
from dataclasses import dataclass

import bahn_constants as C


@dataclass(frozen=True)
class Instance:
    n_wagons: int
    n_dests: int
    payload: int
    boxes: tuple            # (Länge 20|40, Gewicht in t, Ziel 0..n_dests-1), in Ankunftsreihenfolge


def teu(box):
    return 2 if box[0] == 40 else 1


def capacity(inst):
    return C.PLACES * inst.n_wagons


def offered(inst):
    """Angebotene TEU (alle Container)."""
    return sum(teu(b) for b in inst.boxes)


def upper_bound(inst):
    """Triviale obere Schranke der ladbaren TEU: nicht mehr als angeboten und nicht mehr als Plätze."""
    return min(offered(inst), capacity(inst))


def make_instance(n_wagons, n_dests, offer_pct, share40_pct, payload, seed):
    """Container, bis die angebotenen TEU mindestens offer_pct % der Kapazität erreichen (ganzzahlig: teu * 100 >= offer_pct * Kapazität)."""
    if n_wagons < 1 or n_dests < 1 or payload < 1:
        raise ValueError("Wagen, Ziele und Wagenlast müssen mindestens 1 sein")
    if not 0 < offer_pct:
        raise ValueError("Angebot muss positiv sein")
    if not 0 <= share40_pct <= 100:
        raise ValueError("Anteil 40-Fuß in 0 bis 100")
    rng = random.Random(seed)
    cap = C.PLACES * n_wagons
    boxes, total = [], 0
    while total * 100 < offer_pct * cap:
        is40 = rng.randrange(100) < share40_pct
        lo, hi = C.WEIGHT_40 if is40 else C.WEIGHT_20
        boxes.append((40 if is40 else 20, rng.randint(lo, hi), rng.randrange(n_dests)))
        total += 2 if is40 else 1
    return Instance(n_wagons, n_dests, payload, tuple(boxes))


def custom_instance(n_wagons, n_dests, payload, boxes):
    """Eigene Instanz prüfen (Länge 20/40, positives ganzzahliges Gewicht, Ziel im Bereich)."""
    if n_wagons < 1 or n_dests < 1 or payload < 1:
        raise ValueError("Wagen, Ziele und Wagenlast müssen mindestens 1 sein")
    boxes = tuple(tuple(b) for b in boxes)
    if not boxes:
        raise ValueError("mindestens ein Container")
    for length, weight, dest in boxes:
        if length not in (20, 40):
            raise ValueError("Länge 20 oder 40")
        if not isinstance(weight, int) or weight < 1:
            raise ValueError("Gewicht: positive ganze Zahl")
        if not 0 <= dest < n_dests:
            raise ValueError("Ziel außerhalb des Bereichs")
    return Instance(n_wagons, n_dests, payload, boxes)
