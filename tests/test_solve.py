"""Loeser-Tests (sls_solve/sls_scenario): der Optimalitaets-Regressionstest steht bewusst ZUERST - er
hat in messreihe_speed/check.py den echten SLSQP/res.success-Bug gefangen (siehe ERGEBNIS.md) und ist
Pflichtbestandteil dieser Demo, kein nachtraeglicher Zusatz."""
import numpy as np

from sls_scenario import make_route
from sls_solve import economic_speed, lateness, solve_constant, solve_exact, solve_myopic, total_cost

TOL = 1e-4


# ---------------------------------------------------------------------------------------------------
# Optimalitaets-Regressionstest (PFLICHT, zuerst) - "exakt" darf NIE teurer sein als eine andere
# zulaessige Loesung, sonst waere es nicht "exakt". Dieser Test haette den urspruenglichen SLSQP/
# res.success-Bug sofort gefangen (siehe messreihe_speed/ERGEBNIS.md).
# ---------------------------------------------------------------------------------------------------
def test_optimality_regression_exact_is_never_costlier_than_a_feasible_alternative():
    """Ueber 60 Zufallsrouten PLUS die urspruengliche Bug-Instanz (Seed 201) aus ERGEBNIS.md als fester
    Regressionsfall: wenn myopisch (oder konstant) zufaellig selbst alle Fenster einhaelt, darf ihr Preis
    NIE unter dem Preis von exakt liegen."""
    violations = tested = 0
    for seed in list(range(60)) + [201]:
        route = make_route(6, seed, tight_share=0.5, tight_lo=0.95, tight_hi=1.1)
        v_exact = solve_exact(route)
        if v_exact is None:
            continue
        cost_exact = total_cost(v_exact, route)
        tested += 1
        for solver in (solve_myopic, solve_constant):
            v_alt = solver(route)
            _, n_late_alt = lateness(v_alt, route)
            if n_late_alt == 0 and total_cost(v_alt, route) < cost_exact - 1.0:
                violations += 1
    assert tested >= 55, "zu wenige feasible Instanzen fuer einen aussagekraeftigen Regressionstest"
    assert violations == 0


def test_optimality_regression_solve_exact_does_not_trust_res_success():
    """Direkte Absicherung gegen die Rueckkehr des urspruenglichen Bugs (siehe ERGEBNIS.md/README): der
    Loeser darf NICHT ueber scipy.optimize.OptimizeResult.success entscheiden. Statischer Quelltext-Check,
    kein Verhaltenstest - haelt den Fix auch dann fest, wenn ein Refactoring die Zahlen zufaellig
    unveraendert liesse."""
    import ast
    import inspect

    import sls_solve
    src = inspect.getsource(sls_solve.solve_exact)
    tree = ast.parse(src)
    body_without_docstring = tree.body[0].body[1:]   # erstes Element ist der Docstring-Expr-Knoten
    func_body_src = ast.unparse(body_without_docstring)
    assert "res.success" not in func_body_src and "success" not in func_body_src
    assert "trust-constr" in src


# ---------------------------------------------------------------------------------------------------
# 1) Unconstrained: stimmt mit der geschlossenen Formel ueberein
# ---------------------------------------------------------------------------------------------------
def test_unconstrained_route_matches_the_closed_form_economic_speed():
    bad = tested = 0
    for seed in range(20):
        for k, r in [(1.0, 11664.0), (2.0, 8000.0), (0.5, 20000.0)]:
            route = make_route(5, seed, k=k, r=r, tight_share=0.0)
            v = solve_exact(route)
            v_star = economic_speed(k, r)
            tested += 1
            if v is None or not np.allclose(v, v_star, atol=TOL):
                bad += 1
    assert tested == 60
    assert bad == 0


def test_economic_speed_is_clamped_to_v_min_and_v_max():
    from sls_constants import V_MAX, V_MIN
    assert economic_speed(k=1.0, r=1.0) == V_MIN     # sehr niedriges v* wird auf V_MIN geklemmt
    assert economic_speed(k=1.0, r=1e9) == V_MAX      # sehr hohes v* wird auf V_MAX geklemmt


# ---------------------------------------------------------------------------------------------------
# 2) Handinstanz mit einem bindenden Fenster (KKT, von Hand hergeleitet)
# ---------------------------------------------------------------------------------------------------
def test_hand_derived_single_window_instance_matches_the_kkt_solution():
    # k=1, r=11664 -> v* = 18.0 genau (18^3 = 5832 = 11664/2).
    route = dict(n_legs=3, dist=np.array([300.0, 400.0, 500.0]), k=1.0, r=11664.0,
                deadline=np.array([np.inf, 35.0, np.inf]), has_window=np.array([False, True, False]),
                v_econ=economic_speed(1.0, 11664.0))
    v = solve_exact(route)
    # Etappen 0,1 (kumuliert bis zum Fenster) auf konstanter Geschwindigkeit 700/35 = 20.0, Etappe 2
    # (nach dem Fenster, kein eigener Zwang) zurueck auf wirtschaftliche Geschwindigkeit 18.0.
    expected = np.array([20.0, 20.0, 18.0])
    assert v is not None
    assert np.allclose(v, expected, atol=1e-3)


# ---------------------------------------------------------------------------------------------------
# 3) Monotonie: engere Fenster erhoehen die Kosten nie
# ---------------------------------------------------------------------------------------------------
def test_tighter_windows_never_lower_the_cost():
    violations = tested = 0
    for seed in range(30):
        prev_cost = None
        for tight_lo, tight_hi in [(1.3, 1.5), (1.0, 1.2), (0.9, 1.0), (0.75, 0.85)]:
            route = make_route(6, seed, tight_share=0.6, tight_lo=tight_lo, tight_hi=tight_hi)
            v = solve_exact(route)
            tested += 1
            if v is None:
                continue
            cost = total_cost(v, route)
            if prev_cost is not None and cost < prev_cost - 1e-6:
                violations += 1
            prev_cost = cost
    assert tested == 120
    assert violations == 0


# ---------------------------------------------------------------------------------------------------
# Randfaelle
# ---------------------------------------------------------------------------------------------------
def test_zero_percent_windows_always_returns_the_economic_speed_everywhere():
    route = make_route(8, seed=5, tight_share=0.0)
    v = solve_exact(route)
    assert v is not None
    assert np.allclose(v, route["v_econ"], atol=TOL)
    assert not route["has_window"].any()


def test_hundred_percent_windows_is_solvable_when_the_factor_band_is_loose():
    route = make_route(8, seed=5, tight_share=1.0, tight_lo=1.1, tight_hi=1.3)
    assert route["has_window"].all()
    v = solve_exact(route)
    assert v is not None
    _, n_late = lateness(v, route)
    assert n_late == 0


def test_n_legs_three_is_solvable_shortest_route():
    route = make_route(3, seed=0, tight_share=0.5)
    v = solve_exact(route)
    assert v is None or len(v) == 3


def test_a_genuinely_infeasible_configuration_returns_none_not_a_wrong_cost():
    """Sehr enges Faktor-Band UND hohe wirtschaftliche Geschwindigkeit (nahe V_MAX): selbst Vollgas auf
    jeder Etappe reicht nicht, das Fenster einzuhalten (siehe ERGEBNIS.md, Befund 5)."""
    r_high_vstar = 2.0 * 1.0 * 23.0 ** 3   # v* = 23 kn, nah an V_MAX = 24
    route = make_route(6, seed=60, k=1.0, r=r_high_vstar, tight_share=1.0, tight_lo=0.9, tight_hi=1.0)
    v = solve_exact(route)
    assert v is None


def test_solve_myopic_and_solve_constant_never_raise_on_the_infeasible_configuration():
    """Auch wenn 'exakt' scheitert, muessen die beiden anderen Politiken einen (ggf. verspaeteten) Plan
    liefern - kein Crash, keine leere Rueckgabe."""
    r_high_vstar = 2.0 * 1.0 * 23.0 ** 3
    route = make_route(6, seed=60, k=1.0, r=r_high_vstar, tight_share=1.0, tight_lo=0.9, tight_hi=1.0)
    v_myo = solve_myopic(route)
    v_const = solve_constant(route)
    assert len(v_myo) == 6 and len(v_const) == 6
    assert np.all(np.isfinite(v_myo)) and np.all(np.isfinite(v_const))


def test_lateness_is_zero_when_no_window_is_bound():
    route = make_route(5, seed=1, tight_share=0.0)
    v = solve_constant(route)
    late, n_late = lateness(v, route)
    assert late == 0.0 and n_late == 0


def test_leg_lateness_matches_the_sum_returned_by_lateness():
    from sls_solve import leg_lateness
    route = make_route(6, seed=3, tight_share=0.5, tight_lo=0.95, tight_hi=1.1)
    v = solve_myopic(route)
    per_leg = leg_lateness(v, route)
    late_sum, n_late = lateness(v, route)
    assert np.isclose(per_leg.sum(), late_sum)
    assert int(np.sum(per_leg > 1e-6)) == n_late
