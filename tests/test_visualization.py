"""Tests fuer sls_visualization: fixedrange auf allen Achsen, Anzahl der Spuren, verspaetete Etappen
markiert."""
import sls_constants as C
import sls_evaluation as E
from sls_scenario import make_route
from sls_solve import solve_constant, solve_exact, solve_myopic
from sls_visualization import comparison_bars_figure, speed_profile_figure


def _all_axes_fixed(fig):
    for axis_name in fig.layout:
        if axis_name.startswith("xaxis") or axis_name.startswith("yaxis"):
            axis = getattr(fig.layout, axis_name)
            if axis is not None:
                assert axis.fixedrange is True, axis_name


def test_speed_profile_figure_locks_all_axes():
    route = make_route(6, seed=0, tight_share=0.5, tight_lo=0.95, tight_hi=1.1)
    v_exact, v_myo, v_const = solve_exact(route), solve_myopic(route), solve_constant(route)
    fig = speed_profile_figure(route, v_exact, v_myo, v_const)
    _all_axes_fixed(fig)


def test_speed_profile_figure_handles_a_missing_exact_solution():
    route = make_route(6, seed=60, k=1.0, r=2 * 23.0 ** 3, tight_share=1.0, tight_lo=0.9, tight_hi=1.0)
    v_myo, v_const = solve_myopic(route), solve_constant(route)
    fig = speed_profile_figure(route, None, v_myo, v_const)   # exakt nicht machbar
    _all_axes_fixed(fig)
    names = [t.name for t in fig.data if t.name]
    assert C.POLICY_LABELS[C.POLICY_EXACT] not in names


def test_speed_profile_figure_has_one_line_trace_per_policy():
    route = make_route(6, seed=0, tight_share=0.5, tight_lo=0.95, tight_hi=1.1)
    v_exact, v_myo, v_const = solve_exact(route), solve_myopic(route), solve_constant(route)
    fig = speed_profile_figure(route, v_exact, v_myo, v_const)
    names = {t.name for t in fig.data if t.name}
    assert names == {C.POLICY_LABELS[C.POLICY_EXACT], C.POLICY_LABELS[C.POLICY_MYOPIC], C.POLICY_LABELS[C.POLICY_CONST]}


def test_speed_profile_figure_marks_late_legs_for_myopic():
    """Bekannte Instanz (Beispielroute Seed 233, n_legs=7 nach der Preset-Abstimmung): myopisch verpasst
    mindestens ein Fenster trotz Vollgas anderswo."""
    p = E.params_from_controls(7, 100, "Mittel", "Niedrig (v*=15 kn)")
    route = make_route(p.n_legs, 233, k=p.k, r=p.r, tight_share=p.tight_share, tight_lo=p.tight_lo, tight_hi=p.tight_hi)
    v_myo = solve_myopic(route)
    fig = speed_profile_figure(route, None, v_myo, None)
    marker_traces = [t for t in fig.data if t.mode == "markers+text"]
    assert marker_traces, "erwarte mindestens eine 'verspaetet'-Markierung auf dieser bekannten Route"


def test_comparison_bars_figure_locks_all_axes_including_the_secondary_one():
    fig = comparison_bars_figure(gap_myo=2.5, gap_const=-0.3, late_myo=25.0, late_const=60.0)
    _all_axes_fixed(fig)
    assert "yaxis2" in fig.layout


def test_comparison_bars_figure_handles_none_values_without_raising():
    fig = comparison_bars_figure(gap_myo=None, gap_const=None, late_myo=None, late_const=None)
    assert len(fig.data) == 2
