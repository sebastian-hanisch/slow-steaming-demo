"""Abnahmekriterien der Presets (Detailplan plan_speed.html, Abschnitt 7): welche Geschichte erzaehlt
jedes Beispielszenario, und woran erkennt man, dass sie traegt?

Einzige Quelle fuer `tools/tune_presets.py` (Abstimmung) und `tests/test_preset_stories.py` (Abnahme).
`criteria()`: Population-Kriterien (POPULATION_INSTANCES Routen) direkt aus dem Detailplan Abschnitt 7.
`shown_criteria()`: Kriterien an der EINEN gezeigten Route - zeigt sie den behaupteten Kontrast, nicht
die Populationsrate (die auf einer Route nicht definiert ist)?"""
import sls_constants as C
import sls_evaluation as E


def _pct(v):
    return "–" if v is None else f"{v:.1f} %"


def criteria(name, results):
    """Population-Kriterien ueber `results` (Liste von RouteResult, ueblicherweise POPULATION_INSTANCES
    Routen). Rueckgabe: Liste (erfuellt, Text)."""
    myo_late = E.late_share_pct(results, C.POLICY_MYOPIC)
    const_late = E.late_share_pct(results, C.POLICY_CONST)
    myo_gap = E.cost_gap_pct(results, C.POLICY_MYOPIC)
    n_infeasible = E.infeasible_count(results)
    n = len(results)

    if name == "Locker":
        return [(myo_late is not None and myo_late >= 15.0, f"myopisch Verspätungsanteil >= 15 %: {_pct(myo_late)}"),
                (const_late is not None and const_late == 0.0, f"konstant Verspätungsanteil = 0 %: {_pct(const_late)}"),
                (n_infeasible == 0, f"alle {n} Stichproben-Routen machbar: {n - n_infeasible}/{n}")]
    if name == "Mittel":
        return [(const_late is not None and const_late >= 50.0, f"konstant Verspätungsanteil >= 50 %: {_pct(const_late)}"),
                (myo_late is not None and myo_late <= 30.0, f"myopisch Verspätungsanteil <= 30 %: {_pct(myo_late)}"),
                (myo_gap is not None and myo_gap <= 3.0, f"Kostenaufschlag myopisch <= 3 %: {_pct(myo_gap)}")]
    if name == "Eng, machbar":
        return [(const_late is not None and const_late >= 85.0, f"konstant Verspätungsanteil >= 85 %: {_pct(const_late)}"),
                (n_infeasible == 0, f"alle {n} Stichproben-Routen für exakt machbar: {n - n_infeasible}/{n}")]
    if name == "Viele Fenster":
        return [(myo_late is not None and myo_late >= 45.0, f"myopisch Verspätungsanteil >= 45 %: {_pct(myo_late)}"),
                (myo_gap is not None and myo_gap >= 3.0, f"Kostenaufschlag myopisch >= 3 %: {_pct(myo_gap)}")]
    if name == "Nicht machbar":
        return [(n_infeasible == n, f"0 von {n} Stichproben-Routen machbar: {n - n_infeasible}/{n}")]
    raise KeyError(name)


def shown_criteria(name, shown):
    """Kriterien an der EINEN gezeigten Route (shown = ein RouteResult)."""
    feasible = shown.cost_exact is not None
    if name == "Locker":
        return [(feasible, "exakt auf der gezeigten Route machbar"),
                (feasible and shown.cost_myo > shown.cost_exact, "myopisch auf der gezeigten Route teurer als exakt")]
    if name == "Mittel":
        return [(feasible, "exakt auf der gezeigten Route machbar"),
                (shown.n_late_const > 0, f"konstant verpasst auf der gezeigten Route mindestens ein Fenster: {shown.n_late_const}")]
    if name == "Eng, machbar":
        return [(feasible, "exakt auf der gezeigten Route trotz enger Fenster machbar"),
                (shown.n_late_const > 0, f"konstant verpasst auf der gezeigten Route mindestens ein Fenster: {shown.n_late_const}")]
    if name == "Viele Fenster":
        return [(feasible, "exakt auf der gezeigten Route machbar"),
                (shown.n_late_myo > 0, f"myopisch verpasst auf der gezeigten Route mindestens ein Fenster: {shown.n_late_myo}")]
    if name == "Nicht machbar":
        return [(not feasible, "exakt auf der gezeigten Route NICHT machbar (Status \"nicht machbar\" statt eines Kostenwerts)")]
    raise KeyError(name)
