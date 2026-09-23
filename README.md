# Geschwindigkeitsoptimierung: Fenster halten statt nur sparen – Streamlit-Demo

*(noch nicht deployed)*

Interaktive Fall-Demo zur **Geschwindigkeitsoptimierung (Slow Steaming)** einer Reederei: Treibstoffverbrauch steigt mit der dritten Potenz der Geschwindigkeit – langsamer fahren spart viel. Aber manche
Häfen haben feste Zeitfenster (Kaiplatz-Slot, Tide, Anschlussverkehr): wer zu langsam fährt, verpasst sie. Die Demo beantwortet: **Wie viel kostet es wirklich, jedes Ankunftsfenster zuverlässig
einzuhalten – und was passiert, wenn man Fenster nur lokal oder gar nicht berücksichtigt?**

Teil des Portfolios für die Website „Sebastian Hanisch – Operations Research und Machine Learning", **Welle 3 der Seefracht-Linie** (Schwesterlinie zur Hafen-Linie), koppelt an die Mehrhafen-Stauplanung
(dieselben Distanzen/Zeitfenster je Etappe) – dort geht es darum **WO** Container in der Bucht stehen, hier darum **WIE SCHNELL** das Schiff fährt. Anders als die ersten beiden Wellen der Seefracht-Linie
(reine Kombinatorik) ist das hier ein **stetiges, konvexes Optimierungsproblem** (scipy) – ein bewusster Kontrast zum Rest der Linie. Vehikel: eine Route aus N Etappen mit Distanz d_i, Geschwindigkeit v_i
frei wählbar je Etappe.

## Warum dieses Problem

Ein reiner „Politik A gegen Politik B"-Kostenvergleich wäre die falsche Geschichte: der Kostenunterschied zwischen den drei Politiken ist **klein** (myopisch nur 0,6–4,6 % teurer als exakt in den
getesteten Einstellungen; die quadratische Kostenkurve um die wirtschaftliche Geschwindigkeit v* ist in ihrer Nähe flach). Der eigentliche Hook ist **Zuverlässigkeit**: eine Politik, die Fenster
komplett ignoriert (konstant), verpasst sie oft in der Mehrheit der Fälle; selbst die „naheliegend kluge" myopische Regel (lokal die langsamste noch fensterkonforme Geschwindigkeit) verpasst sie
immer noch spürbar oft, weil unnötige lokale Vorsicht sich auf spätere Etappen fortpflanzen kann. **Nur die gemeinsame Optimierung hält garantiert alle erreichbaren Fenster ein – bei fast identischen
Kosten.**

## Befunde/Korrekturen aus der Vorab-Messreihe

Zwei Dinge hat die Vorab-Messreihe (`seefracht-planung/messreihe_speed/`) am ursprünglichen Plan geändert:

1. **Der Hook ist Zuverlässigkeit, nicht Kostenersparnis** – wie oben beschrieben; die Kostenachse allein wäre irreführend gewesen.
2. **Ein echter Implementierungsfehler wurde gefunden und behoben.** Die erste Fassung von `solve_exact` nutzte scipy SLSQP mit `res.success` als Auswahlkriterium über mehrere Startpunkte. SLSQP
   meldete bei etlichen Instanzen **fälschlich `success=False`** ("Positive directional derivative for linesearch"), obwohl der gefundene Punkt bereits (fast) optimal UND zulässig war – ein bekannter
   SLSQP-Stall nahe aktiver Nebenbedingungen. Der Code verwarf dadurch den guten Kandidaten und wählte einen **schlechteren** – mit der Folge, dass „exakt" teils **teurer als myopisch** war, obwohl
   „exakt" per Definition nie schlechter sein darf. Der Bug hatte außerdem die gemessene Unerreichbarkeits-Rate massiv verfälscht (47–93 % statt tatsächlich 0 % im getesteten Bereich locker bis eng).
   **Fix:** `trust-constr` statt SLSQP, Auswahl über eine explizite Zulässigkeitsprüfung am Ergebnis statt `res.success`. Siehe `tests/test_solve.py::test_optimality_regression_*` – dieser Test hätte
   den Bug sofort gefangen und ist deshalb ein **Pflichtbestandteil** dieser Demo, kein nachträglicher Zusatz.

## Modell

Route mit N Etappen, Distanz $d_i$, Geschwindigkeit $v_i \in [10, 24]$ kn frei wählbar je Etappe. Treibstoffkosten je Etappe $k \cdot d_i \cdot v_i^2$ (Verbrauch ~ $v^3$, Zeit = $d_i/v_i$),
Charter-/Kapitalkosten $r \cdot d_i / v_i$ (Tagesrate × Fahrzeit) – beide konvex in $v_i$. Ohne Nebenbedingung ist die kostenoptimale Geschwindigkeit auf **jeder** Etappe konstant und
distanzunabhängig: $v^\ast = (r/2k)^{1/3}$, die klassische „wirtschaftliche Geschwindigkeit" der Schifffahrtsökonomie (Ronen 1982). Ein Teil der Etappen hat zusätzlich ein hartes **spätestes**
Ankunftsfenster – das bricht die Konstanz von $v^\ast$ und macht aus der Aufgabe ein echtes, konvexes Optimierungsproblem. Formal im Expander „📐 Mathematische Formulierung" der App.

## Methodik – drei Bausteine statt einer Reglerfamilie

Wie bei der Mehrhafen-Stauplanung sind das drei Bausteine, kein stetiger Regler:

- **🐌 Konstant**: immer wirtschaftliche Geschwindigkeit v*, Fenster komplett ignoriert – die Kontrast-Baseline.
- **👁️ Myopisch**: je Etappe lokal die langsamste Geschwindigkeit, die das EIGENE Fenster gerade noch schafft, ohne spätere Etappen zu berücksichtigen – die „naheliegend kluge" Regel, trägt trotzdem
  einen echten Zuverlässigkeits-Nachteil.
- **🎯 Exakt (gemeinsam optimiert)**: konvexe Optimierung über die ganze Route (`trust-constr`), hält alle Fenster ein, wo das physikalisch überhaupt möglich ist – die operative Empfehlung der
  Hauptansicht.

**Kernlogik unverändert übernommen**: `sls_scenario.py` (`make_route`) und `sls_solve.py` (`economic_speed`, `solve_constant`, `solve_myopic`, `solve_exact`) sind direkt aus
`seefracht-planung/messreihe_speed/speed.py` übernommen – bereits gegen die geschlossene Formel, eine von Hand hergeleitete KKT-Handinstanz und den Optimalitäts-Regressionstest verifiziert
(`messreihe_speed/check.py`, 0 Abweichungen in 61 Instanzen).

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen mit `python -m pytest tests/` nachvollziehbar (`test_solve.py`, `test_preset_stories.py`).

| Frage | Befund | Test |
|---|---|---|
| Stimmt der Löser ohne Fenster mit der geschlossenen Formel überein? | Ja: 60/60 Instanzen (3 k/r-Kombinationen × 20 Seeds), 0 Abweichungen von $v^\ast$ | `test_solve.py::test_unconstrained_route_matches_the_closed_form_economic_speed` |
| Stimmt die Handinstanz mit einem bindenden Fenster (KKT)? | Ja: erwartete Geschwindigkeiten [20,0, 20,0, 18,0] kn exakt getroffen | `test_solve.py::test_hand_derived_single_window_instance_matches_the_kkt_solution` |
| Erhöhen engere Fenster die Kosten nie? | Ja: 120/120 geprüfte Lösungen, 0 Monotonie-Verletzungen | `test_solve.py::test_tighter_windows_never_lower_the_cost` |
| Ist „exakt" jemals teurer als eine andere zulässige Lösung? | Nein: 0 Verletzungen über 61 Instanzen (60 Zufallsrouten + die ursprüngliche Bug-Instanz Seed 201) | `test_solve.py::test_optimality_regression_exact_is_never_costlier_than_a_feasible_alternative` |
| Wie klein ist der Kostenaufschlag wirklich? | Myopisch 0,62–4,54 % teurer als exakt (Presets); konstant sogar bis 0,32 % *billiger* (ignoriert Fenster) | `test_preset_stories.py` |
| Wie groß ist die Verspätungslücke? | Konstant verpasst Fenster in 0–100 % der Fälle (preset-abhängig); myopisch noch in 21,7–51,7 % | `test_preset_stories.py` |
| Erkennt der Löser echte Unerreichbarkeit zuverlässig? | Ja: 60/60 Stichprobenrouten korrekt als „nicht machbar" erkannt (Preset „Nicht machbar"), 0 falsche Kostenwerte | `test_preset_stories.py`, `test_solve.py::test_a_genuinely_infeasible_configuration_returns_none_not_a_wrong_cost` |

## Ehrliche Grenzen

- **Nur ein spätestes Fenster je Etappe** (kein frühestes/Warten, keine Liegeplatz-Wartezeit).
- **Distanzen und Fenster-Enge synthetisch erzeugt**, nicht an echten Bunkerpreisen/Charterraten/Hafenfenstern kalibriert.
- **Kein Wetter, keine Strömung, keine Geschwindigkeitsschwankung durch Wellengang.**
- **Rechenzeit bei knappen/nicht machbaren Instanzen ist spürbar höher** als bei komfortablen (der Löser iteriert länger, bevor er aufgibt, siehe ERGEBNIS.md) – deshalb der sichtbare Ladeindikator
  (`st.cache_data(show_spinner=...)`) statt einer Live-Berechnung ohne Anzeige, anders als bei `leercontainer-demo`/`mehrhafenstau-demo`. `trust-constr` ist zusätzlich über `maxiter=500` hart begrenzt –
  ein Sicherheitsnetz, das ein Hängen der UI bei einer pathologischen Reglerkombination verhindert.
- **`n_starts=1`** (ein Startpunkt) reicht laut Regressionstest für alle geprüften Instanzen, ist aber keine bewiesene Garantie für jede denkbare Parameterkombination.
- **Nähe zur Mehrhafen-Stauplanung**: beide behandeln dieselbe Route, aber dort geht es um die Platzierung der Container, hier um die Geschwindigkeit des Schiffs – bewusst nicht technisch gekoppelt
  (Konvention: eigenständige Demos).

## Befunde und Korrekturen gegenüber dem Plan

- **„Viele Fenster"-Preset braucht 7 statt 6 Etappen.** Der Plan zitiert für dieses Preset ein Faktor-Band (0,95–1,15), das keiner der drei kanonischen Fenster-Enge-Stufen dieser App entspricht
  (Locker 1,0–1,3 / Mittel 0,95–1,1 / Eng 0,9–1,0 – bewusst als feste Stufen umgesetzt, siehe „Regler" unten). Mit den drei kanonischen Stufen und `n_legs=6` ließen sich die beiden Abnahmekriterien
  „Kostenaufschlag myopisch ≥ 3 %" UND „Verspätungsanteil myopisch ≥ 45 %" empirisch **nicht gleichzeitig** erreichen (`tools/tune_presets.py` zeigt einen echten Zielkonflikt: bei `n_legs=6` sinkt der
  Kostenaufschlag, sobald der Verspätungsanteil über 45 % steigt, und umgekehrt, über den gesamten getesteten Bereich von Fenster-Enge und Bunker-/Charter-Verhältnis). Bei `n_legs=7` verschwindet der
  Zielkonflikt (myopisch verpasst öfter UND kostet spürbar mehr, weil mehr Etappen mehr Gelegenheit für kaskadierende Fehlentscheidungen bieten) – gemessen 51,7 % Verspätungsanteil, 4,54 % Kostenaufschlag,
  beide klar über der Schwelle. Die gezeigte Beispielroute bleibt trotzdem **Seed 233** (zufällig auch bei `n_legs=7` eine gute, klar erzählte Instanz) – dieselbe Seed-Zahl wie im ursprünglichen Plan,
  aber jetzt für eine 7- statt 6-Etappen-Route.
- **Fünf statt drei Stufen für „Bunker-/Charter-Verhältnis" gewählt.** Der Plan lässt die genaue Stufenzahl offen ("vordefinierte Stufen um den Standardwert"). Fünf Stufen (v* = 12/15/18/21/23 kn)
  erwiesen sich als nötig, um sowohl das „Nicht machbar"-Preset (siehe unten) als auch das abgestimmte „Viele Fenster"-Preset zu erreichen, ohne die Fenster-Enge-Stufen selbst aufzuweichen.
- **„Nicht machbar" erreicht über eine hohe wirtschaftliche Geschwindigkeit, nicht über ein viertes Fenster-Enge-Extremum.** Der Plan zitiert für dieses Preset ein Faktor-Band (0,45–0,55), deutlich
  enger als die „Eng"-Stufe dieser App (0,9–1,0) – das hätte eine vierte, nur für ein Preset sichtbare Fenster-Enge-Stufe gebraucht und damit die bewusste Drei-Stufen-Beschränkung unterlaufen (Plan
  Abschnitt 5/15: verhindert versehentlich extrem enge/unmögliche Einstellungen ohne Kontext). Stattdessen nutzt das Preset einen Mechanismus, den der Plan selbst als Regler vorsieht, aber nicht für
  diesen Zweck einplant: bei fester „Eng"-Stufe (0,9–1,0) und 100 % Fensteranteil macht eine hohe wirtschaftliche Geschwindigkeit (v* = 23 kn, nah an V_MAX = 24 kn) selbst das lockerste Fenster der
  Stufe physikalisch unerreichbar (Herleitung: die geforderte Durchschnittsgeschwindigkeit bis zu einem Fenster ist ungefähr $v^\ast/\text{Faktor}$; bei $v^\ast$ nah an $V_{\max}$ und Faktor < 1 bleibt
  kein Spielraum mehr). Empirisch bestätigt (`tools/tune_presets.py --search`): 60/60 Stichprobenrouten nicht machbar, ohne die drei kanonischen Fenster-Enge-Stufen anzutasten.

## Regler

| Key | Beschriftung | Bereich (Default) | Wirkung |
|---|---|---|---|
| `n_legs_slider` | Etappen | 3–10 (6) | Routenlänge |
| `window_share_slider` | Anteil mit Fenster | 0–100 %, Schritt 10 (50 %) | Anteil der Etappen mit hartem Ankunftsfenster |
| `tightness_select` | Fenster-Enge | Locker / Mittel / Eng (Mittel) | Faktor-Band der Deadlines relativ zur wirtschaftlichen Fahrzeit; „Eng" kann in Kombination mit hohem Bunker-/Charter-Verhältnis unerreichbar werden |
| `rate_ratio_select` | Bunker-/Charter-Verhältnis | 5 Stufen (v* = 12/15/18/21/23 kn), Standard v* = 18 kn | verschiebt die wirtschaftliche Geschwindigkeit v* selbst |
| `seed_input` | Seed | 0–9999 (0) | bestimmt Distanzen und welche Etappen ein Fenster bekommen |
| 🎲 Neue Route | Button | – | würfelt den Seed |

Fenster-Enge und Bunker-/Charter-Verhältnis sind bewusst **Stufen** statt Freitext-Faktor-Bänder – einfacher zu erklären, verhindert versehentlich extrem enge/unmögliche Einstellungen ohne Kontext im
Regler-Hilfetext. Permalink spiegelt alle fünf Werte in der Adresszeile.

## Tests

`python -m pytest tests/ -v` – 113 Tests, rund 5 Minuten (die meisten AppTest-Läufe brauchen mehrere echte `solve_exact`-Aufrufe; „Nicht machbar" allein braucht deutlich länger, weil jede infeasible
Instanz den Löser bis `maxiter=500` laufen lässt statt früh abzubrechen). Zusammensetzung:

- **Löser** (`test_solve.py`): **Optimalitäts-Regressionstest zuerst** (61 Instanzen inkl. der ursprünglichen Bug-Instanz), statischer Quelltext-Check gegen die Rückkehr des `res.success`-Bugs,
  geschlossene Formel ohne Fenster (60 Instanzen), Handinstanz (KKT), Monotonie (120 Instanzen), Randfälle (0 %/100 % Fenster, N=3, eine echte Infeasible-Konfiguration).
- **Szenario** (`test_scenario.py`): Struktur der Route, Determinismus, `tight_share`-Randfälle, Faktor-Band-Monotonie.
- **Auswertung** (`test_evaluation.py`): Stichprobe/Kostenaufschlag/Verspätungsanteil gegen Handrechnung auf künstlichen `RouteResult`-Werten, Ausschluss infeasibler Routen aus den Mittelwerten,
  gepaartes Urteil (exakt ist nie unzuverlässiger als myopisch), Diagnose in beiden Zuständen.
- **Figuren** (`test_visualization.py`): Geschwindigkeitsprofil, Zwei-Achsen-Vergleich – alle Achsen fest (`fixedrange`, auch die sekundäre Y-Achse), verspätete Etappen markiert.
- **Regler** (`test_presets.py`): Permalink-Parsing/-Klemmen/-Runden für numerische UND Enum-Regler (kurze URL-Schlüssel, Fallback auf Default bei Datenmüll), Presets innerhalb ihrer Grenzen.
- **Presets** (`test_preset_stories.py`): Geschichte im Mittel von 60 Routen UND an der gezeigten Route für alle 5 Presets, Seeds außerhalb der Population, künstliche Werte, die jedes Kriterium
  einzeln an seiner Schwelle kippen lassen.
- **PDF** (`test_pdf_export.py`): Sonderzeichen-Bereinigung (fpdf2 stürzt bei „–", „€", Emoji ab), Inhalt für machbare UND infeasible Diagnose.
- **End-to-End** (`test_app.py`, AppTest): Skelett und Footer, jedes Preset (inkl. „Nicht machbar" mit seiner eigenen, klar unterscheidbaren Statusmeldung statt eines Kostenwerts), Permalink
  (inkl. Enum-Decodierung), alle Regler an Min/Max, die bedingte Meldung in beiden Zuständen, Urteil in allen drei Zuständen, Vergleichstabelle, PDF (auch im infeasiblen Fall), Texte, statischer
  Nachweis, dass der Ladeindikator (`show_spinner=C.SOLVE_SPINNER_TEXT`) tatsächlich am `solve_exact`-Aufruf hängt.

Zusätzlich ein Fehler-Einbau-Test (`tools/mutation_check.py`, 21 Mutanten über `sls_solve`, `sls_scenario`, `sls_evaluation`, `sls_stories`, `sls_presets`): erster Lauf **12 gefunden, 9 überlebt, 0 Fehler
in der Mutantenliste.** Drei der neun Überlebenden waren echte Testlücken (Distanz-Obergrenze nur locker statt eng geprüft, zwei exakte Schwellenwerte ohne künstlichen Grenzfalltest) – dafür wurden drei
gezielte Tests ergänzt (`test_distances_span_close_to_the_full_documented_range_across_many_draws`, `test_verdict_is_unclear_exactly_at_the_two_standard_error_threshold`,
`test_artificial_values_tip_the_mittel_myopic_criterion_exactly_at_its_threshold`); alle drei Mutationen wurden danach einzeln direkt (ohne den vollen, mehrere Sekunden je Mutant kostenden
Testsuite-Durchlauf) gegen die neuen Tests nachgerechnet und nachweislich gefangen – ein vollständiger zweiter 21-Mutanten-Lauf wurde aus Zeitgründen nicht wiederholt (jeder Mutant startet eine eigene
pytest-Subprocess mit mehreren echten `solve_exact`-Aufrufen, rund 3–4 Minuten je Mutant). Die verbleibenden sechs Überlebenden sind gleichwertig (kein sichtbarer Unterschied im Verhalten):

- `solve_exact`: `fun < best_fun` → `fun > best_fun` beim Kandidatenvergleich überlebt, weil die App/alle Tests `n_starts=1` verwenden (ein einziger Startpunkt) – der Vergleich wird bei nur einem
  Kandidaten nie ausgewertet (`best_fun is None` ist immer wahr beim ersten und einzigen Aufruf).
- `solve_myopic`: `remaining > 0` → `remaining >= 0` überlebt, weil `remaining == 0.0` exakt nur bei einem Gleitkomma-Nulltreffer einträte – mit stetig verteilten Zufallsdistanzen praktisch
  Wahrscheinlichkeit 0.
- `make_route`: `rng.random(n_legs) < tight_share` → `<=` überlebt aus demselben Grund (stetige Gleichverteilung, exakter Treffer auf `tight_share` praktisch ausgeschlossen).
- `verdict`: `"better"` → `"worse"` im `se == 0`-Zweig überlebt, weil die Differenz in diesem Zweig durch die Konstruktion (`0 - 100×Verspätungsanteil`) nie positiv sein kann – der `"worse"`-Fall ist
  in diesem Zweig unerreichbarer Code.
- `sls_stories`: `const_late == 0.0` → `<= 0.0` überlebt, weil ein Verspätungsanteil (Prozentsatz) konstruktionsbedingt nie negativ werden kann – beide Vergleiche sind identisch.
- `sls_stories`: `n_infeasible == n` → `>= n` überlebt, weil `n_infeasible` (eine Zählung unter `n` Routen) `n` nie überschreiten kann – beide Vergleiche sind identisch.

## Dateistruktur

| Datei | Inhalt | Herkunft |
|---|---|---|
| `app.py` | Streamlit-Hauptablauf: Presets, Sidebar, Hauptansicht, Kernabschnitt, Politik-Tabs, Texte | neu |
| `sls_constants.py` | Regler-Grenzen, Fenster-Enge-/Bunker-Charter-Stufen, `PRESETS`, Farben, feste Modellparameter | neu |
| `sls_presets.py` | `SETTING_SPECS` (inkl. Enum-Regler mit kurzen URL-Schlüsseln), Permalink, Presets, Seed-Knopf | Muster `mhs_presets.py` |
| `sls_scenario.py` | Route (`make_route`) | `messreihe_speed/speed.py`, unverändert |
| `sls_solve.py` | `economic_speed`, `solve_constant`, `solve_myopic`, `solve_exact` (`trust-constr`) | `messreihe_speed/speed.py`, unverändert (plus `leg_lateness`-Zusatzansicht für die Grafik) |
| `sls_evaluation.py` | Stichprobe, Kostenaufschlag/Verspätungsanteil je Politik, gepaartes Urteil, Diagnose | Muster `mhs_evaluation.py` |
| `sls_visualization.py` | Geschwindigkeitsprofil, Zwei-Achsen-Vergleich (alle Achsen fest, sekundäre Y-Achse) | Muster `mhs_visualization.py` |
| `sls_ui_panel.py` | Kennzahlen (2×2), Politik-Panel (je Tab), Vergleichstabelle | Muster `mhs_ui_panel.py` |
| `sls_pdf_export.py` | PDF-Export (`fpdf2`, Sonderzeichen-Bereinigung) | Muster `mhs_pdf_export.py` |
| `sls_stories.py` | Abnahmekriterien der Presets (Population UND gezeigte Route) | Muster `mhs_stories.py` |
| `tools/tune_presets.py` | Preset-Abstimmung/-Prüfung, Grid-Suche für die infeasible Kombination | neu |
| `tools/mutation_check.py` | Fehler-Einbau-Test | Muster `mhs`/`tools/mutation_check.py` |
| `tests/` | siehe oben | neu |

## Bewusst nicht umgesetzt (mögliche Erweiterungen)

- **Beidseitige Zeitfenster** (frühestes UND spätestes Fenster, Liegeplatz-Wartezeit) statt nur eines spätesten Fensters je Etappe.
- **Wetter-/Strömungseinfluss** auf die tatsächliche Fahrzeit bei eingestellter Geschwindigkeit.
- **Kalibrierung an echten Bunkerpreisen/Charterraten/Hafenfenstern** statt synthetisch erzeugter Parameter.
- **Mehrere Schiffe/Flottenplanung** – diese Demo behandelt eine einzelne Route.
- **Prognoseunschärfe der Fenster selbst** (die Fenster gelten hier als sicher bekannt).

## Verwandte Demos mit demselben mathematischen Modell

Verschiedene Themen im Portfolio teilen (fast) dasselbe Modell. Vor einer neuen Demo-Idee deshalb das
Modell vergleichen, nicht die Kulisse (Stand 2026-09-23):

- **CO2-optimale Fahrgeschwindigkeit im Straßenverkehr** (Pollution-Routing, `vrp_demo`) ist dasselbe Geschwindigkeitsmodell
  mit Lkw statt Schiff: kubische bis quadratische Verbrauchskosten, Zeitfenster je Etappe, gemeinsame gegen lokale
  Berücksichtigung. Als Dopplung verworfen. Neu wäre nur die Kopplung mit der Tourenwahl. Die Befunde dieser Demo
  (kleiner Kostenunterschied, der Hook ist die Zuverlässigkeit der Fenster) sind dafür der Ausgangspunkt.

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `python -m pytest tests/ -v`. Preset-Abstimmung: `python tools/tune_presets.py`. Infeasible-Kombination suchen: `python tools/tune_presets.py --search`. Fehler-Einbau: `python tools/mutation_check.py`.

---

Gebaut mit Streamlit, Plotly, scipy und fpdf2.
