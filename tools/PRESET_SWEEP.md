# Preset-Abstimmung (AP 6)

Werkzeug: `tools/tune_presets.py` (Modi `population`, `seeds`); Kriterien in `bahn_stories.py`, Abnahme in `tests/test_preset_stories.py` (echte Daten) und `tests/test_stories.py`
(künstliche Werte an den Schwellen).

Messbasis: 16 Wagen (48 Plätze), Angebot 120 % (Locker 80 %), Tage mit den Seeds 0 bis 19 (Grundgesamtheit, 2 s Limit für den Löser, „Schwer“ 10 s) und 0 bis 59 (Suche nach dem Preset-Seed).

## Grundgesamtheit (20 Tage je Preset, geladene TEU im Mittel)

| Preset | Einstellung | Reihenfolge | Größe zuerst | Wagenblöcke | Exakt | Schranke ohne Reinheit | Preis der Reinheit |
|---|---|---|---|---|---|---|---|
| Locker | 4 Ziele, Angebot 80 % | 39,15 | 39,15 | 39,15 | 39,15 | 39,25 | 0,10 |
| Üblich | 4 Ziele | 45,20 | 45,65 | 47,35 | 47,35 (bewiesen 18/20) | 47,80 | 0,45 |
| Viele Ziele | 8 Ziele | 42,65 | 43,00 | 45,40 | 45,40 (12 von 20 nicht bewiesen) | 47,80 | 2,40 |
| Schwer | 4 Ziele, 30 % 40-Fuß, 40 t je Wagen | – | – | 47,10 | 47,70 (an 40 % der Tage mehr als Wagenblöcke) | – | – |
| Ganz lang | 10 Ziele | 42,25 | 43,20 | 45,35 | 45,35 (14 von 20 nicht bewiesen) | 48,00 | 2,65 |

## Befunde und Abweichungen vom Plan

- **Die kluge Regel „Wagenblöcke“ gleicht dem Exakt-Wert fast immer** (0 Tage mit Wagenblöcke < Exakt bei „Üblich“, „Viele Ziele“, „Ganz lang“). Das war schon die Vorab-Messung; die Presets
  erzählen deshalb Abstand zur Alltagsregel und Preis der Zielreinheit, nicht „Exakt schlägt alles“.
- **„Schwer“ wurde gegenüber dem Plan geändert.** Der Plan sah 6 Ziele bei 45 t und 50 % 40-Fuß vor („Blöcke liegen in einzelnen Fällen unter dem Optimum“). Mit dem gebauten Zufallsstrom
  (ganzzahlig, Angebot als Prozent der Kapazität) lag Wagenblöcke bei 45 t an **keinem** von 20 Tagen unter Exakt. Ein Raster (Ziele 3/6, Angebot 120/150 %, 30/70 % 40-Fuß, 40/45 t) zeigte den
  Effekt erst bei **wenigen 40-Fuß-Containern und 40 t je Wagen** (bis 7 von 12 Tagen); das Preset heißt weiter „Schwer“, hat aber 30 % 40-Fuß und 40 t.
- **Die Zeitlimit-Messung schwankt mit der Rechenlast.** Mit vielen gleichzeitigen Prozessen (je 8 Löser-Threads) beweist der Löser in 2 s weniger; das Werkzeug rechnet deshalb mit
  `max_workers=2`. Kriterien über Exakt sind Aussagen über eine untere Schranke und stehen mit Abstand zur Schwelle (Lehre aus der Schiffsstau-Demo, wo drei Preset-Tests auf der CI kippten).
- **Zeitkosten:** Die Stichprobe von 20 Tagen dauert bei 8 Zielen etwa 30 s (jeder Tag löst zweimal: mit und ohne Zielreinheit), die Kurve über 7 Zielzahlen × 8 Tage etwa 40 s.

## Gewählt

- Eine gemeinsame Tagesnummer für alle Presets: **Seed 35** (16 Wagen, 50 % 40-Fuß, 60 t; „Schwer“ 30 % und 40 t). Alle fünf Geschichten tragen an diesem Tag (auch mit 30 s Limit und nach dem
  Beweis, `tests/test_preset_stories.py`); jede Kennzahl liegt zwischen dem 10. und 90. Perzentil der 20 Grundgesamtheits-Tage. Von 60 Seeds tragen nur 35, 25 und 43 alle fünf Geschichten;
  Seed 35 liegt mit 0,10 (Summe der Logarithmen) am nächsten am Median der Kennzahlen.
- An Seed 35 (Reihenfolge / Größe zuerst / Wagenblöcke / Exakt): Locker 40 / 40 / 40 / 40, Üblich 46 / 47 / 48 / 48, Viele Ziele 42 / 45 / 47 / 47 (Schranke ohne Reinheit 48),
  Schwer 45 / 44 / 47 / **48**, Ganz lang 42 / 41 / 46 / 46 (Schranke 48).
- Die „nicht bewiesen“-Anzeige zeigt „Ganz lang“ vor allem in der Stichprobe (70 % der Tage bei 2 s) und im Diagramm (offene Punkte ab 6 Zielen), weniger an dem einen gezeigten Tag.
