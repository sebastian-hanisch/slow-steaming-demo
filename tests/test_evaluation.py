"""Tests fuer sls_evaluation: Stichprobe, Kostenaufschlag/Verspaetungsanteil, gepaartes Urteil,
Diagnose - gegen Direktrechnung und Handrechnung."""
import sls_constants as C
import sls_evaluation as E


def test_route_result_matches_a_direct_solve():
    from sls_scenario import make_route
    from sls_solve import solve_exact, total_cost

    p = E.Params(6, 0.5, 0.95, 1.1)
    r = E.route_result(p, seed=0)
    route = make_route(6, 0, tight_share=0.5, tight_lo=0.95, tight_hi=1.1)
    v_exact = solve_exact(route)
    assert r.cost_exact == total_cost(v_exact, route)


def test_params_from_controls_converts_percent_and_labels():
    p = E.params_from_controls(6, 50, "Mittel", "Standard (v*=18 kn)")
    assert p.n_legs == 6 and p.tight_share == 0.5
    assert (p.tight_lo, p.tight_hi) == C.TIGHTNESS_LEVELS["Mittel"]
    assert p.r == C.RATE_RATIO_LEVELS["Standard (v*=18 kn)"]


def test_cost_gap_pct_is_zero_for_the_exact_policy_itself():
    p = E.Params(6, 0.5, 0.95, 1.1)
    results = E.sample(p, 10)
    assert E.cost_gap_pct(results, C.POLICY_EXACT) == 0.0


def test_cost_gap_pct_matches_hand_computation_on_two_synthetic_results():
    R = E.RouteResult
    results = (
        R(seed=0, n_windows=0, v_exact=(18.0,), v_myo=(18.0,), v_const=(18.0,), cost_exact=100.0, cost_myo=110.0, cost_const=90.0, late_myo=0.0, n_late_myo=0, late_const=0.0, n_late_const=0),
        R(seed=1, n_windows=0, v_exact=(18.0,), v_myo=(18.0,), v_const=(18.0,), cost_exact=200.0, cost_myo=210.0, cost_const=190.0, late_myo=1.0, n_late_myo=1, late_const=0.0, n_late_const=0),
    )
    # mean_exact=150, mean_myo=160 -> gap = 10/150*100 = 6.666...%
    assert abs(E.cost_gap_pct(results, C.POLICY_MYOPIC) - (10.0 / 150.0 * 100.0)) < 1e-9
    assert E.late_share_pct(results, C.POLICY_MYOPIC) == 50.0
    assert E.late_share_pct(results, C.POLICY_CONST) == 0.0
    assert E.infeasible_count(results) == 0


def test_infeasible_routes_are_excluded_from_means_but_counted_separately():
    R = E.RouteResult
    results = (
        R(seed=0, n_windows=1, v_exact=None, v_myo=(18.0,), v_const=(18.0,), cost_exact=None, cost_myo=110.0, cost_const=90.0, late_myo=5.0, n_late_myo=1, late_const=5.0, n_late_const=1),
        R(seed=1, n_windows=0, v_exact=(18.0,), v_myo=(18.0,), v_const=(18.0,), cost_exact=200.0, cost_myo=200.0, cost_const=200.0, late_myo=0.0, n_late_myo=0, late_const=0.0, n_late_const=0),
    )
    assert E.infeasible_count(results) == 1
    assert len(E.feasible(results)) == 1
    assert E.cost_gap_pct(results, C.POLICY_MYOPIC) == 0.0    # nur die feasible Route zaehlt
    assert E.late_share_pct(results, C.POLICY_MYOPIC) == 0.0


def test_cost_gap_pct_and_late_share_are_none_when_nothing_is_feasible():
    R = E.RouteResult
    results = (R(seed=0, n_windows=1, v_exact=None, v_myo=(1.0,), v_const=(1.0,), cost_exact=None, cost_myo=1.0, cost_const=1.0, late_myo=1.0, n_late_myo=1, late_const=1.0, n_late_const=1),)
    assert E.cost_gap_pct(results, C.POLICY_MYOPIC) is None
    assert E.late_share_pct(results, C.POLICY_MYOPIC) is None
    assert E.mean_late(results, C.POLICY_MYOPIC) is None


# ---------------------------------------------------------------------------------------------------
# Gepaartes Urteil
# ---------------------------------------------------------------------------------------------------
def test_verdict_is_better_when_myopic_is_clearly_worse():
    p = E.Params(6, 1.0, 0.95, 1.15)   # viele Fenster, mittlere Enge -> myopisch verpasst oft
    results = E.sample(p, 30)
    v = E.verdict(results)
    assert v.n > 0
    assert v.kind in ("better", "unclear")   # exakt ist nie schlechter als myopisch bei der Verspaetungsrate


def test_verdict_diff_is_never_positive_worse_than_myopic():
    """Exakt ist per Konstruktion nie unzuverlaessiger als myopisch (0 - Anteil_myo_late <= 0)."""
    p = E.Params(6, 0.5, 0.95, 1.1)
    results = E.sample(p, 20)
    v = E.verdict(results)
    assert v.diff <= 0.0


def test_verdict_handles_no_feasible_routes():
    R = E.RouteResult
    results = (R(seed=0, n_windows=1, v_exact=None, v_myo=(1.0,), v_const=(1.0,), cost_exact=None, cost_myo=1.0, cost_const=1.0, late_myo=1.0, n_late_myo=1, late_const=1.0, n_late_const=1),)
    v = E.verdict(results)
    assert v.n == 0 and v.kind == "unclear"


# ---------------------------------------------------------------------------------------------------
# Diagnose
# ---------------------------------------------------------------------------------------------------
def test_diagnose_infeasible_when_shown_route_has_no_exact_solution():
    R = E.RouteResult
    shown = R(seed=0, n_windows=1, v_exact=None, v_myo=(1.0,), v_const=(1.0,), cost_exact=None, cost_myo=1.0, cost_const=1.0, late_myo=1.0, n_late_myo=1, late_const=1.0, n_late_const=1)
    diag = E.diagnose(shown)
    assert diag.kind == "infeasible" and diag.markup_vs_const_pct is None and diag.n_windows_met is None


def test_diagnose_feasible_reports_the_markup_against_constant():
    R = E.RouteResult
    shown = R(seed=0, n_windows=2, v_exact=(1.0,), v_myo=(1.0,), v_const=(1.0,), cost_exact=110.0, cost_myo=110.0, cost_const=100.0, late_myo=0.0, n_late_myo=0, late_const=0.0, n_late_const=0)
    diag = E.diagnose(shown)
    assert diag.kind == "feasible"
    assert abs(diag.markup_vs_const_pct - 10.0) < 1e-9
    assert diag.n_windows_met == 2 and diag.n_windows == 2


def test_sample_uses_seeds_starting_from_the_given_offset_not_the_shown_seed():
    p = E.Params(6, 0.5, 0.95, 1.1)
    results = E.sample(p, 5, start=100)
    assert [r.seed for r in results] == [100, 101, 102, 103, 104]
