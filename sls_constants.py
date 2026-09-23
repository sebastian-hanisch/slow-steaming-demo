"""Konstanten der Geschwindigkeitsoptimierungs-Demo (Welle 3 Seefracht-Linie).

Modell und Zahlen aus messreihe_speed/ (siehe seefracht-planung/plan_speed.html, ERGEBNIS.md). Presets
werden mit tools/tune_presets.py gegen die Abnahmekriterien in sls_stories.py geprueft; die Werte hier
sind das Ergebnis dieser Abstimmung (siehe tools/PRESET_SWEEP.md). Anders als bei den ersten beiden
Seefracht-Wellen: ein stetiges, konvexes Optimierungsproblem (scipy), nicht Kombinatorik."""

# --- Modellgrenzen (aus messreihe_speed/speed.py, unveraendert) -----------------------------------------
V_MIN, V_MAX = 10.0, 24.0
K_DEFAULT = 1.0            # Treibstoffkosten-Koeffizient, immer 1.0 (nur R variiert -> Bunker-/Charter-Verhaeltnis)
R_DEFAULT = 11664.0        # Charter-Tagesrate: mit K_DEFAULT ergibt das v* = 18.0 kn genau (18^3 = 11664/2)

# --- Regler ------------------------------------------------------------------------------------------
N_LEGS_RANGE, N_LEGS_DEFAULT = (3, 10), 6
WINDOW_SHARE_RANGE, WINDOW_SHARE_STEP, WINDOW_SHARE_DEFAULT = (0, 100), 10, 50   # Prozent
SEED_RANGE, SEED_DEFAULT = (0, 9999), 0

# Fenster-Enge: 3 Stufen statt Freitext-Faktor-Band (Plan Abschnitt 5/15) - verhindert versehentlich
# extrem enge/unmoegliche Einstellungen ohne Kontext im Regler-Hilfetext. Faktor < 1 = enger als
# wirtschaftlich (zwingt zum Schnellerfahren), > 1 = lockerer (nie bindend).
TIGHTNESS_LEVELS = {
    "Locker": (1.0, 1.3),
    "Mittel": (0.95, 1.1),
    "Eng": (0.9, 1.0),
}
TIGHTNESS_DEFAULT = "Mittel"
TIGHTNESS_HELP = "Faktor-Band der Deadlines relativ zur wirtschaftlichen Fahrzeit. \"Eng\" kann in Kombination mit hohem Bunker-/Charter-Verhältnis unerreichbar werden."
TIGHTNESS_URL_KEYS = {"Locker": "locker", "Mittel": "mittel", "Eng": "eng"}

# Bunker-/Charter-Verhaeltnis: vordefinierte Stufen um den Standardwert (v* = 18 kn), verschieben die
# wirtschaftliche Geschwindigkeit v* selbst (hoehere Charterrate relativ zu den Bunkerkosten = schneller
# wirtschaftlich). r = 2*k*v^3 bei K_DEFAULT=1.0.
RATE_RATIO_LEVELS = {
    "Sehr niedrig (v*=12 kn)": 2 * K_DEFAULT * 12.0 ** 3,
    "Niedrig (v*=15 kn)": 2 * K_DEFAULT * 15.0 ** 3,
    "Standard (v*=18 kn)": R_DEFAULT,
    "Hoch (v*=21 kn)": 2 * K_DEFAULT * 21.0 ** 3,
    "Sehr hoch (v*=23 kn)": 2 * K_DEFAULT * 23.0 ** 3,
}
RATE_RATIO_DEFAULT = "Standard (v*=18 kn)"
RATE_RATIO_HELP = "Verhältnis Charterrate/Bunkerkosten; verschiebt die wirtschaftliche Geschwindigkeit v* selbst - zeigt, dass der Zuverlässigkeits-Hook unabhängig vom Kostenniveau trägt."
RATE_RATIO_URL_KEYS = {
    "Sehr niedrig (v*=12 kn)": "v12", "Niedrig (v*=15 kn)": "v15", "Standard (v*=18 kn)": "v18",
    "Hoch (v*=21 kn)": "v21", "Sehr hoch (v*=23 kn)": "v23",
}

# --- Loeser-Sicherheitsnetz ------------------------------------------------------------------------------
# Kein zusaetzliches Zeitlimit noetig: solve_exact begrenzt trust-constr bereits hart ueber maxiter=500
# (siehe sls_solve.py) - bei infeasiblen/knappen Instanzen iteriert der Loeser laenger, bevor er aufgibt
# (siehe ERGEBNIS.md), aber die Obergrenze an Iterationen bleibt fest, kein unbegrenztes Haengen moeglich.
SOLVE_SPINNER_TEXT = "Löser rechnet (bei engen Fenstern kann es spürbar länger dauern als sonst in diesem Portfolio) …"

# --- Auswertung -----------------------------------------------------------------------------------------
SAMPLE_INSTANCES = 30         # Instanzen je Urteil im Kernabschnitt (Plan Abschnitt 6)
POPULATION_INSTANCES = 60     # Instanzen fuer die Preset-Abnahme (Plan Abschnitt 7; reproduziert
                               # messreihe_speed/sweep.py range(60))
VERDICT_Z = 2.0                # klar ab mehr als VERDICT_Z Standardfehlern der gepaarten Differenz

# --- Bausteine (Plan Abschnitt 3): drei Politiken statt einer Reglerfamilie -----------------------------
POLICY_CONST, POLICY_MYOPIC, POLICY_EXACT = "konstant", "myopisch", "exakt"
POLICY_KEYS = (POLICY_CONST, POLICY_MYOPIC, POLICY_EXACT)
POLICY_LABELS = {POLICY_CONST: "🐌 Konstant", POLICY_MYOPIC: "👁️ Myopisch", POLICY_EXACT: "🎯 Exakt (gemeinsam optimiert)"}
POLICY_SHORT = {POLICY_CONST: "Konstant", POLICY_MYOPIC: "Myopisch", POLICY_EXACT: "Exakt"}
POLICY_DESCRIPTIONS = {
    POLICY_CONST: "Fährt immer mit der wirtschaftlichen Geschwindigkeit v*, Fenster komplett ignoriert. Die "
                  "Kontrast-Baseline: zeigt, wie oft reines Kostensparen die Fenster kostet.",
    POLICY_MYOPIC: "Wählt je Etappe lokal die langsamste Geschwindigkeit, die das EIGENE Fenster gerade noch "
                   "schafft, ohne spätere Etappen zu berücksichtigen. Die \"naheliegend kluge\" Regel - trägt "
                   "trotzdem einen echten Zuverlässigkeits-Nachteil.",
    POLICY_EXACT: "Konvexe Optimierung über die ganze Route (trust-constr), hält alle Fenster ein, wo "
                  "physikalisch überhaupt möglich (bis V_MAX). Die operative Empfehlung der Hauptansicht.",
}
EXACT_TAB_LABEL = POLICY_LABELS[POLICY_EXACT]
COMPARISON_TAB_LABEL = "📊 Vergleich"

# --- Darstellung ----------------------------------------------------------------------------------------
POLICY_COLORS = {POLICY_EXACT: "#2e7d4f", POLICY_MYOPIC: "#c0392b", POLICY_CONST: "#9aa5b4"}
CURRENT_MARK_COLOR = "#1f3a5f"
CHART_HEIGHT = 380

# --- Presets (Plan Abschnitt 7; per tools/tune_presets.py abgestimmt) -----------------------------------
# Jedes Preset legt Etappen, Fensteranteil (%), Fenster-Enge-Stufe, Bunker-/Charter-Stufe und einen Seed
# fest, der AUSSERHALB der Populations-Stichprobe (POPULATION_INSTANCES) liegt.
PRESETS = {
    "Locker": dict(n_legs=6, window_share=50, tightness="Locker", rate_ratio="Standard (v*=18 kn)", seed=201),
    "Mittel": dict(n_legs=6, window_share=50, tightness="Mittel", rate_ratio="Standard (v*=18 kn)", seed=201),
    "Eng, machbar": dict(n_legs=6, window_share=40, tightness="Eng", rate_ratio="Standard (v*=18 kn)", seed=201),
    # n_legs=7 (nicht 6) und rate_ratio="Niedrig" (nicht "Standard") - siehe README, Abschnitt
    # "Befunde und Korrekturen gegenueber dem Plan": bei n_legs=6 liessen sich "Kostenaufschlag >= 3 %"
    # und "Verspaetungsanteil >= 45 %" mit den 3 kanonischen Fenster-Enge-Stufen nicht gleichzeitig
    # erreichen (echter Zielkonflikt, per tune_presets.py empirisch bestaetigt).
    "Viele Fenster": dict(n_legs=7, window_share=100, tightness="Mittel", rate_ratio="Niedrig (v*=15 kn)", seed=233),
    "Nicht machbar": dict(n_legs=6, window_share=100, tightness="Eng", rate_ratio="Sehr hoch (v*=23 kn)", seed=60),
}
