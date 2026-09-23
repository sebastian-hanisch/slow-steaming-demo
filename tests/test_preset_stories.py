"""Abnahme der Presets an ECHTEN Daten: jede Geschichte traegt im Mittel ueber POPULATION_INSTANCES
Routen (`sls_stories.criteria`) UND an der einen Route, die das Preset zeigt (`sls_stories.shown_criteria`).
Reproduziert die Abstimmung aus tools/tune_presets.py / tools/PRESET_SWEEP.md."""
import pytest

import sls_constants as C
import sls_evaluation as E
import sls_stories as ST

NAMES = list(C.PRESETS)
_POP = {}


def params(name):
    cfg = C.PRESETS[name]
    return E.params_from_controls(cfg["n_legs"], cfg["window_share"], cfg["tightness"], cfg["rate_ratio"])


def population(name):
    if name not in _POP:
        _POP[name] = E.sample(params(name), C.POPULATION_INSTANCES)
    return _POP[name]


@pytest.mark.parametrize("name", NAMES)
def test_story_holds_on_average_over_the_population(name):
    for ok, text in ST.criteria(name, population(name)):
        assert ok, f"{name}: {text}"


@pytest.mark.parametrize("name", NAMES)
def test_story_holds_at_the_route_the_preset_shows(name):
    seed = C.PRESETS[name]["seed"]
    shown = E.route_result(params(name), seed)
    for ok, text in ST.shown_criteria(name, shown):
        assert ok, f"{name}: {text}"


def test_the_preset_seed_lies_outside_the_population():
    assert all(cfg["seed"] >= C.POPULATION_INSTANCES for cfg in C.PRESETS.values())


def test_criteria_are_not_trivially_true_for_the_wrong_preset():
    """Die Geschichten unterscheiden sich: an den Daten eines anderen Presets kippt mindestens ein
    Kriterium (sonst waeren die Presets austauschbar)."""
    assert not all(ok for ok, _ in ST.criteria("Locker", population("Nicht machbar")))
    assert not all(ok for ok, _ in ST.criteria("Nicht machbar", population("Locker")))
    assert not all(ok for ok, _ in ST.criteria("Eng, machbar", population("Locker")))


def test_artificial_values_tip_each_locker_criterion_exactly_at_its_threshold():
    """Kuenstliche RouteResult-Werte, bei denen jedes Kriterium einzeln an seiner Schwelle kippt (siehe
    DEMO-PLAYBOOK.md: Grenzfaelle mit exakter Gleichheit gezielt testen)."""
    R = E.RouteResult

    def make(n_late_myo, n_late_const):
        return R(seed=0, n_windows=1, v_exact=(18.0,), v_myo=(18.0,), v_const=(18.0,), cost_exact=100.0,
                 cost_myo=100.0, cost_const=100.0, late_myo=1.0 if n_late_myo else 0.0, n_late_myo=n_late_myo,
                 late_const=1.0 if n_late_const else 0.0, n_late_const=n_late_const)

    # 3 von 20 Routen mit myopisch-Verspaetung = 15.0 % -> genau an der ">= 15 %"-Schwelle von "Locker".
    results = tuple(make(1, 0) for _ in range(3)) + tuple(make(0, 0) for _ in range(17))
    assert E.late_share_pct(results, C.POLICY_MYOPIC) == 15.0
    ok_at_threshold = [ok for ok, text in ST.criteria("Locker", results) if "myopisch" in text][0]
    assert ok_at_threshold

    results_below = tuple(make(1, 0) for _ in range(2)) + tuple(make(0, 0) for _ in range(18))
    assert E.late_share_pct(results_below, C.POLICY_MYOPIC) == 10.0
    ok_below = [ok for ok, text in ST.criteria("Locker", results_below) if "myopisch" in text][0]
    assert not ok_below


def test_artificial_values_tip_the_mittel_myopic_criterion_exactly_at_its_threshold():
    """18 von 60 Routen mit myopisch-Verspaetung = genau 30,0 % -> an der "<= 30 %"-Schwelle von
    "Mittel" noch erfuellt; 19 von 60 = 31,7 % -> knapp darueber, nicht mehr erfuellt."""
    R = E.RouteResult

    def make(n_late_myo):
        return R(seed=0, n_windows=1, v_exact=(18.0,), v_myo=(18.0,), v_const=(18.0,), cost_exact=100.0,
                 cost_myo=100.0, cost_const=100.0, late_myo=1.0 if n_late_myo else 0.0, n_late_myo=n_late_myo,
                 late_const=0.0, n_late_const=0)

    at_threshold = tuple(make(1) for _ in range(18)) + tuple(make(0) for _ in range(42))
    assert E.late_share_pct(at_threshold, C.POLICY_MYOPIC) == 30.0
    ok_at = [ok for ok, text in ST.criteria("Mittel", at_threshold) if "myopisch" in text][0]
    assert ok_at

    above_threshold = tuple(make(1) for _ in range(19)) + tuple(make(0) for _ in range(41))
    assert above_threshold[0].n_late_myo == 1
    ok_above = [ok for ok, text in ST.criteria("Mittel", above_threshold) if "myopisch" in text][0]
    assert not ok_above


def test_nicht_machbar_criterion_tips_when_even_one_route_is_feasible():
    R = E.RouteResult
    all_infeasible = tuple(R(seed=i, n_windows=1, v_exact=None, v_myo=(1.0,), v_const=(1.0,), cost_exact=None,
                             cost_myo=1.0, cost_const=1.0, late_myo=1.0, n_late_myo=1, late_const=1.0, n_late_const=1) for i in range(5))
    assert all(ok for ok, _ in ST.criteria("Nicht machbar", all_infeasible))
    one_feasible = all_infeasible[:-1] + (R(seed=4, n_windows=1, v_exact=(1.0,), v_myo=(1.0,), v_const=(1.0,),
                                            cost_exact=1.0, cost_myo=1.0, cost_const=1.0, late_myo=0.0, n_late_myo=0, late_const=0.0, n_late_const=0),)
    assert not all(ok for ok, _ in ST.criteria("Nicht machbar", one_feasible))
