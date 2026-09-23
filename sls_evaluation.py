"""Auswertung: Stichprobe von Routen, Kostenaufschlag/Verspaetungsanteil je Politik, gepaartes Urteil
(exakt gegen myopisch), Diagnose (bedingte Meldung). Reine Rechnung ohne Streamlit.

Alle populationsweiten Prozentwerte (Kostenaufschlag, Verspaetungsanteil) werden - wie in
messreihe_speed/sweep.py - ueber die FEASIBLE Teilmenge der Stichprobe berechnet (Routen, an denen
solve_exact ueberhaupt eine zulaessige Loesung findet); infeasible Routen werden separat gezaehlt
(infeasible_count), nicht stillschweigend ignoriert."""
import math
import statistics
from dataclasses import dataclass
from typing import NamedTuple, Optional

import sls_constants as C
from sls_scenario import make_route
from sls_solve import lateness, solve_constant, solve_exact, solve_myopic, total_cost


class Params(NamedTuple):
    """Alle Rohwerte, die eine Route bestimmen (ohne Seed) - entkoppelt von den UI-Reglerstufen."""
    n_legs: int
    tight_share: float
    tight_lo: float
    tight_hi: float
    k: float = C.K_DEFAULT
    r: float = C.R_DEFAULT


def params_from_controls(n_legs, window_share_pct, tightness_label, rate_ratio_label, k=C.K_DEFAULT):
    """Wandelt die Reglerwerte (Etappen, Anteil mit Fenster in %, Fenster-Enge-Stufe, Bunker-/
    Charter-Stufe) in die rohen Szenario-Parameter um."""
    lo, hi = C.TIGHTNESS_LEVELS[tightness_label]
    r = C.RATE_RATIO_LEVELS[rate_ratio_label]
    return Params(int(n_legs), window_share_pct / 100.0, lo, hi, k, r)


@dataclass(frozen=True)
class RouteResult:
    seed: int
    n_windows: int
    v_exact: Optional[tuple]
    v_myo: tuple
    v_const: tuple
    cost_exact: Optional[float]     # None = bei dieser Route/Einstellung nicht machbar
    cost_myo: float
    cost_const: float
    late_myo: float
    n_late_myo: int
    late_const: float
    n_late_const: int


def route_result(p, seed):
    route = make_route(p.n_legs, seed, k=p.k, r=p.r, tight_share=p.tight_share, tight_lo=p.tight_lo, tight_hi=p.tight_hi)
    v_exact = solve_exact(route)
    v_myo = solve_myopic(route)
    v_const = solve_constant(route)
    cost_exact = total_cost(v_exact, route) if v_exact is not None else None
    late_myo, n_late_myo = lateness(v_myo, route)
    late_const, n_late_const = lateness(v_const, route)
    return RouteResult(
        seed=seed, n_windows=int(route["has_window"].sum()),
        v_exact=tuple(v_exact) if v_exact is not None else None, v_myo=tuple(v_myo), v_const=tuple(v_const),
        cost_exact=cost_exact, cost_myo=total_cost(v_myo, route), cost_const=total_cost(v_const, route),
        late_myo=late_myo, n_late_myo=n_late_myo, late_const=late_const, n_late_const=n_late_const,
    )


def sample(p, n=C.SAMPLE_INSTANCES, start=0):
    """n Routen (Seeds start..start+n-1, unabhaengig vom eingestellten Seed) mit den Einstellungen p."""
    return tuple(route_result(p, seed) for seed in range(start, start + n))


def feasible(results):
    return [r for r in results if r.cost_exact is not None]


def infeasible_count(results):
    return sum(1 for r in results if r.cost_exact is None)


def mean_cost(results, policy):
    feas = feasible(results)
    if not feas:
        return None
    values = {C.POLICY_EXACT: [r.cost_exact for r in feas], C.POLICY_MYOPIC: [r.cost_myo for r in feas],
              C.POLICY_CONST: [r.cost_const for r in feas]}[policy]
    return statistics.fmean(values)


def cost_gap_pct(results, policy):
    """Prozentualer Kostenaufschlag von `policy` gegenueber exakt, auf Basis der MITTEL-Kosten ueber die
    feasible Teilmenge (wie messreihe_speed/sweep.py: (mean_policy - mean_exact) / mean_exact * 100)."""
    m_exact = mean_cost(results, C.POLICY_EXACT)
    m_policy = mean_cost(results, policy)
    if m_exact is None or m_policy is None or m_exact == 0:
        return None
    return (m_policy - m_exact) / m_exact * 100.0


def late_share_pct(results, policy):
    """Anteil der FEASIBLE Routen (exakt loesbar), auf denen `policy` mindestens ein Fenster verpasst."""
    feas = feasible(results)
    if not feas:
        return None
    n_late_attr = {C.POLICY_MYOPIC: "n_late_myo", C.POLICY_CONST: "n_late_const"}[policy]
    return 100.0 * sum(1 for r in feas if getattr(r, n_late_attr) > 0) / len(feas)


def mean_late(results, policy):
    feas = feasible(results)
    if not feas:
        return None
    late_attr = {C.POLICY_MYOPIC: "late_myo", C.POLICY_CONST: "late_const"}[policy]
    return statistics.fmean(getattr(r, late_attr) for r in feas)


# ---------------------------------------------------------------------------------------------------
# Gepaartes Urteil: exakt gegen myopisch bei der Verspaetungsrate (nur feasible Routen)
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Verdict:
    kind: str        # "better" (exakt zuverlaessiger) | "worse" | "unclear"
    diff: float        # exakt minus myopisch (Prozentpunkte Verspaetungsrate je Route, negativ = exakt besser)
    se: float
    n: int


def _se(d):
    return statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else 0.0


def verdict(results):
    """Gepaarte Differenz (exakt-Verspaetungsindikator minus myopisch-Verspaetungsindikator) x 100, nur
    ueber Routen, an denen exakt ueberhaupt feasible ist (exakt ist per Konstruktion nie verspaetet, wenn
    feasible - die Differenz ist deshalb -100 x Anteil der Routen, an denen myopisch verspaetet)."""
    feas = feasible(results)
    if not feas:
        return Verdict("unclear", 0.0, 0.0, 0)
    d = [0.0 - (100.0 if r.n_late_myo > 0 else 0.0) for r in feas]
    diff, se = statistics.fmean(d), _se(d)
    if se == 0:
        kind = "unclear" if diff == 0 else "better"
    else:
        kind = "unclear" if abs(diff) <= C.VERDICT_Z * se else ("better" if diff < 0 else "worse")
    return Verdict(kind, diff, se, len(feas))


# ---------------------------------------------------------------------------------------------------
# Diagnose (bedingte Meldung, Plan Abschnitt 6): machbar/nicht machbar der GEZEIGTEN Route
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Diagnosis:
    kind: str                  # "infeasible" | "feasible"
    markup_vs_const_pct: Optional[float]   # (cost_exact - cost_const) / cost_const * 100
    n_windows_met: Optional[int]
    n_windows: int


def diagnose(shown):
    if shown.cost_exact is None:
        return Diagnosis("infeasible", None, None, shown.n_windows)
    markup = ((shown.cost_exact - shown.cost_const) / shown.cost_const * 100.0) if shown.cost_const else 0.0
    return Diagnosis("feasible", markup, shown.n_windows, shown.n_windows)
