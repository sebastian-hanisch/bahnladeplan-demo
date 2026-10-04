# Bahn-Ladeplan: Wie voll wird der Zug? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-bahnladeplan-demo.streamlit.app/)**

Interaktive Fall-Demo zur **Beladung eines Containerzuges**: Ein Zug besteht aus Wagen mit je drei Plätzen. Jeder Wagen fährt zu **einem** Zielterminal, ein 40-Fuß-Container braucht zwei
benachbarte Plätze, und jeder Wagen trägt nur begrenztes Gewicht. Was nicht mitfährt, wartet auf den nächsten Zug. Die Demo beantwortet: **Wie viele Container schafft ein Zug wirklich, was
verschenkt die Alltagsregel, und was kostet die Zielreinheit?**

Teil des Portfolios für die Website „Sebastian Hanisch – Operations Research und Machine Learning", Welle 4 der Hafen-Linie (Kran → Hinterland; nach der Schiffsstauplanung
`stauplanung-demo`, der Fahrzeug-Demo `fahrzeugflotte-demo`, der Kaiplatz-Demo `robuste-kaiplatz-demo` und der Stapelplanung `stapelplanung-demo`).

## Warum dieses Problem

Die Alltagsregel „erster passender Wagen in Ankunftsreihenfolge“ reißt mit jedem neuen Ziel einen Wagen an und lässt Plätze leer. Eine klügere Regel **füllt je Ziel eigene Wagen und nimmt die
vollsten**: Sie trifft das Optimum fast immer (dieselbe Lehre wie bei der Fahrzeug-Demo: „exakt gegen Heuristik“ ist hier nicht der Aufhänger). Interessant sind zwei andere Fragen: **Wie viele
Plätze verschenkt die Alltagsregel?** (bei 4 Zielen gut 2, bei 8 bis 10 Zielen fast 3 von 48) und **Was kostet die Vorgabe „ein Ziel je Wagen“?** Der Preis der Zielreinheit steigt mit der
Zahl der Ziele.

## Modell

Ein Zug aus *W* Wagen mit je 3 Plätzen (60 Fuß = 3 TEU). Ein Container ist 20 Fuß (ein Platz) oder 40 Fuß (zwei **benachbarte** Plätze), hat ein Gewicht (20 Fuß 6 bis 24 t, 40 Fuß 8 bis 30 t,
ganzzahlig) und ein Zielterminal 1..*D*. **Zielreinheit:** jeder Wagen fährt zu genau einem Ziel (die Wagengruppen werden am Ziel abgekoppelt). **Wagenlast:** die Summe der Gewichte je Wagen
höchstens *PL* (40 bis 70 t). Ziel: möglichst viele **TEU** laden; ist mehr angeboten, als der Zug fasst, wählt der Plan aus. Das Angebot ist ein Prozentsatz der Kapazität, ganzzahlig gebildet
(die kleinste Containerliste, die den Prozentsatz erreicht). Formal im Expander „📐 Mathematische Formulierung“.

## Methodik – vier Verfahren und eine Schranke

Alle Verfahren laden dieselben Container; Referenz aller Vergleiche ist die **Reihenfolge**.

- **Reihenfolge**: Container in Ankunftsreihenfolge, in den ersten Wagen desselben Ziels mit Platz und Last, sonst in einen neuen Wagen. Der Alltag ohne Plan.
- **Größe zuerst**: erst die 40-Fuß-Container, jeweils schwerere zuerst, jeder in den Wagen seines Ziels mit dem wenigsten Restplatz.
- **Wagenblöcke** (eigene Konstruktion): je Ziel per „Größe zuerst“ in eigene Wagen packen (so viele wie nötig), dann die vollsten Wagen wählen, bis der Zug voll ist.
- **Exakt (CP-SAT)**: die größte Zahl geladener TEU; Zeitlimit 4 s live, 30 s auf Knopfdruck. Lädt schon die Regel alles Angebotene oder alle Plätze, ist das Optimum ohne Löser bewiesen; sonst
  steht ein Intervall aus bester Lösung und oberer Schranke, **nie ein unbewiesener Wert als Optimum**.
- **Schranke ohne Zielreinheit** (kein Verfahren): derselbe Zug mit gemischten Wagen. Der Abstand zum Optimum ist der **Preis der Zielreinheit**.

Die **Stichprobe** (20 Tage mit den Seeds 0 bis 19, nicht der eingestellte Seed) und die **Kurve** (geladene TEU über der Zahl der Zielterminals, 7 Zielzahlen × 8 Tage) laufen auf Knopfdruck mit
Fortschrittsbalken (etwa 30 bis 90 s).

## Befunde (gemessen, keine Behauptungen)

16 Wagen (48 Plätze), Angebot 120 %, 50 % 40-Fuß, 60 t je Wagen; Zahlen aus `tools/PRESET_SWEEP.md`, der Vorab-Messreihe (`hafen-planung/messreihe_bahn/ERGEBNIS.md`) und der Kurve der App.

| Frage | Befund |
|---|---|
| **Was verschenkt die Alltagsregel?** | Bei 4 Zielen lädt die Reihenfolge im Mittel 45,2 von 48 Plätzen, Größe zuerst 45,7, Wagenblöcke und Exakt **47,4**; bei 8 Zielen 42,7 / 43,0 / **45,4**; bei 10 Zielen 42,3 / 43,2 / **45,4**. Bei einem Ziel entfällt die Zielreinheit (Preis 0); die Verfahren laden dann meist, aber nicht an jedem Tag gleich viel (bei 120 % Angebot weichen die Regeln an etwa 3 % der Tage ab, bei 100 % an etwa 29 %). |
| **Trifft die kluge Regel das Optimum?** | Ja, an allen 20 Tagen jedes Presets außer „Schwer“: Wagenblöcke = Exakt (bei den unbewiesenen Tagen: kein Löser fand mehr). |
| **Was kostet die Zielreinheit?** | Schranke ohne Reinheit minus Optimum im Mittel: 0,1 bei 4 Zielen und Angebot 80 %, 0,45 bei 4 Zielen, **2,4 bei 8 Zielen, 2,65 bei 10 Zielen** (Kurve: 0 bei einem bis drei Zielen). |
| **Wann schlägt Exakt die Blockregel?** | Nur wenn das Gewicht bindet: mit wenigen 40-Fuß-Containern (30 %) und 40 t je Wagen an 40 % der Tage (+0,6 TEU im Mittel). Bei 45 t und 50 % 40-Fuß an keinem von 20 Tagen. |
| **Wie weit reicht der Löser?** | Bewiesen an allen Tagen bis 4 Zielen; bei 6 Zielen an 88 %, bei 8 an 38 %, bei 10 an 25 % (2 s Limit, 16 Wagen). Dort steht ein Intervall. |
| **Presets** | Eine gemeinsame Tagesnummer (Seed 35) für alle fünf; jede Kennzahl zwischen dem 10. und 90. Perzentil der Grundgesamtheit. „Schwer“ weicht mit 30 % 40-Fuß und 40 t vom Plan ab (bei 45 t zeigte sich kein Effekt). |

## Ehrliche Grenzen

- **Ein Zug, eine Abfahrt, keine Zeitachse.** Alle Container sind da, bevor der Zug beladen wird; eine Online-Beladung (Container kommen nach und nach) ist nicht modelliert.
- **Keine Achslast und Lastverteilung im Wagen**, nur die Summe je Wagen; keine Reefer, kein Gefahrgut, nur 60-Fuß-Wagen mit drei Plätzen.
- **Die Zielreinheit ist eine Modellannahme**; in der Praxis gibt es auch gemischte Wagen und Umsetzen unterwegs. Die Schranke ohne Reinheit zeigt genau, was die Annahme kostet.
- **Die Regel Wagenblöcke ist meine Konstruktion**; der Abstand zum Optimum ist klein und wird so erzählt.
- Alle Zahlen sind **Größenordnungen aus einer Simulation mit zufälligen Tagen, keine Messung an echten Zügen.**

## Design-Entscheidungen und Funde

**Der Aufhänger wurde nach der Messung verschoben.** Der Plan sah „Alltagsregel gegen exakten Löser“ vor; gemessen ist die kluge Regel fast optimal. Die Demo erzählt deshalb, was die
Alltagsregel verschenkt und was die Zielreinheit kostet, und sagt im Plan wie im Text, dass dies die schwächste der Hafen-Demos ist.

**„Schwer“ nach der Messung angepasst.** Der Plan-Effekt („Blöcke unter dem Optimum bei 45 t“) ließ sich mit dem gebauten Zufallsstrom nicht reproduzieren; ein Raster fand ihn bei wenigen
40-Fuß-Containern und 40 t. Ein Preset soll zeigen, was gemessen ist.

**Beweislage vor Wert.** Das Optimum kann hier nur eine **untere Schranke** sein (maximiert wird): der Exakt-Wert trägt „≥“, das Intervall steht im Tooltip. Die Schranke ohne Reinheit ist eine
obere Schranke; der Preis der Reinheit ist bei unbewiesenem Exakt daher eine Obergrenze und steht mit „≤“ bzw. „höchstens“.

**Das Urteil kennt drei Zustände.** „Mehr“, „weniger“ und „kein klarer Unterschied“ (größer als zwei Standardfehler der gepaarten Differenz), jeweils mit dem Anteil der Tage, an denen es umgekehrt
ist, und der Verteilung (mehr / gleich / weniger, Median gegen Mittel). Nur Tage, an denen beide Verfahren zulässig sind, gehen ein.

**CI-robuste Preset-Tests von Anfang an.** Aus der Schiffsstau-Demo: der Löser beweist auf einem langsamen Rechner in 2 s weniger als lokal. Die Preset-Tests rechnen den gezeigten Tag mit
großzügigem Limit, die Schwellen für Exakt stehen mit Abstand, und die Kurven-Tests der App laufen mit verkleinerter Kurve. Der Fehler-Einbau-Test läuft mit `PYTHONDONTWRITEBYTECODE=1` (gleich lange
Mutanten in derselben Sekunde ließen Python sonst alten Bytecode nutzen).

## Tests

`python -m pytest tests/ -v` – 473 Tests, rund 7 Minuten. Zusammensetzung:

- **Regeln:** Bewertung Bedingung für Bedingung (Plätze, Nachbarschaft der 40-Fuß-Container, Wagenlast auch an der Grenze, Zielreinheit), jede Regel liefert einen zulässigen Plan innerhalb der
  Schranke (60 Zufallsinstanzen), keine Regel schlägt das Brute-Force-Optimum auf 50 Kleinstinstanzen, gemessene Rangfolge der Regeln.
- **Exakt:** CP-SAT gegen Brute Force auf 120 Kleinstinstanzen und die Schranke ohne Reinheit auf 60 (mit Prüfung, dass die Vergleiche nicht leer laufen), „Optimum ≥ jede Regel“, Monotonie,
  Abkürzung ohne Löser, Rückfall auf die Regel, Intervall und Beweis mit ersetztem Löser.
- **Auswertung:** Kennzahlen, Kurve gegen Direktrechnungen, Urteil in drei Zuständen und an der Schwelle, Verteilung, Preis der Reinheit, Kante.
- **Figuren:** Zug-Bild aus den Ergebnisobjekten (ein Rechteck je Platz und Container, Breite 1 oder 2 Plätze, Hover über das ganze Rechteck), Kurve mit offenen und gefüllten Punkten.
- **Presets:** Geschichte am gezeigten Tag, im Mittel von 20 Tagen, typisch je Kennzahl; Kriterien an ihren Schwellen mit künstlichen Werten.
- **PDF:** Inhalt Zelle für Zelle, genaue Sonderzeichen (fpdf2 stürzt bei „–“, „€“ und Emoji ab), Abschnitte nicht über Seitenumbrüche zerteilt.
- **End-to-End (AppTest):** Skelett und Footer, jedes Preset, Permalink, alle Regler an Min und Max, längster und kürzester Zug, Stichprobe und Kurve, Urteil in allen Zuständen, Exakt-Tab, PDF.

Zusätzlich wurde jedes Modul mit **eingebauten Fehlern** geprüft; die verbleibenden Überlebenden sind nachweislich gleichwertig oder betreffen reine Seitenumbruch-Schutzabstände.

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Hauptablauf: Presets, Sidebar, Hauptansicht, Zug-Blick, Kernabschnitt, Methodenvergleich, Texte |
| `bahn_constants.py` | Regler-Grenzen, `PRESETS`, Verfahren, Farben, feste Parameter (Plätze je Wagen, Gewichtsbereiche, Zeitlimits) |
| `bahn_presets.py` | `SETTING_SPECS`, Permalink (Begrenzen und Einrasten), Presets, Seed-Knopf |
| `bahn_scenario.py` | Instanz aus den Reglern (Container, Gewichte, Ziele), triviale Schranke |
| `bahn_rules.py` | Bewertung eines Plans, Reihenfolge, Größe zuerst, Wagenblöcke |
| `bahn_exact.py` | CP-SAT-Modell, Zeitlimit, Intervall, Abkürzung, Schranke ohne Zielreinheit |
| `bahn_evaluation.py` | Kennzahlen, Stichprobe, Kurve über die Zahl der Ziele, gepaarte Differenz, Verteilung, Urteil |
| `bahn_visualization.py` | Zug-Bild, Kurve, Verteilung, Vergleich (alle Achsen fest) |
| `bahn_ui_panel.py` | Panel je Verfahren und Exakt-Tab |
| `bahn_pdf_export.py` | PDF-Ergebnis (`fpdf2`, Kernschrift, Sonderzeichen-Bereinigung) |
| `bahn_stories.py` | Abnahmekriterien der Presets (Quelle für Werkzeug und Tests) |
| `tools/tune_presets.py`, `tools/PRESET_SWEEP.md` | Preset-Abstimmung und ihr Bericht |
| `tests/` | siehe oben |

## Bewusst nicht umgesetzt (mögliche Erweiterungen)

- **Zeitachse** (Ankunft der Container, Abfahrtszeiten mehrerer Züge, Online-Beladung; Kopplung an die Stapelplanung über die Abrufreihenfolge).
- **Achslast und Lastverteilung im Wagen, Reefer, Gefahrgut, Wagentypen mit anderen Plätzen.**
- **Gemischte Wagen mit Umsetzen unterwegs** und Kranzeiten.
- **Kalibrierung an echten Zügen.**

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `python -m pytest tests/ -v`. Preset-Abstimmung: `python tools/tune_presets.py population|seeds`.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Hafenlogistik optimieren](https://sebastianhanisch.net/hafenlogistik-optimierung.html).
