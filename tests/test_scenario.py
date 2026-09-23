"""Tests fuer sls_scenario.make_route (unveraendert aus messreihe_speed/speed.py uebernommen)."""
import numpy as np

from sls_scenario import make_route
from sls_solve import economic_speed


def test_make_route_has_the_requested_number_of_legs():
    route = make_route(7, seed=1)
    assert route["n_legs"] == 7
    assert len(route["dist"]) == 7 and len(route["deadline"]) == 7 and len(route["has_window"]) == 7


def test_distances_are_within_the_documented_range():
    route = make_route(10, seed=3)
    assert np.all(route["dist"] >= 200) and np.all(route["dist"] <= 1500)


def test_deadline_is_infinite_exactly_where_has_window_is_false():
    route = make_route(8, seed=4, tight_share=0.5)
    assert np.all(np.isinf(route["deadline"][~route["has_window"]]))
    assert np.all(np.isfinite(route["deadline"][route["has_window"]]))


def test_tight_share_zero_means_no_leg_gets_a_window():
    route = make_route(8, seed=4, tight_share=0.0)
    assert not route["has_window"].any()


def test_tight_share_one_means_every_leg_gets_a_window():
    route = make_route(8, seed=4, tight_share=1.0)
    assert route["has_window"].all()


def test_v_econ_matches_economic_speed_for_the_given_k_and_r():
    route = make_route(5, seed=0, k=2.0, r=8000.0)
    assert route["v_econ"] == economic_speed(2.0, 8000.0)


def test_same_seed_produces_the_same_route():
    a = make_route(6, seed=42)
    b = make_route(6, seed=42)
    assert np.array_equal(a["dist"], b["dist"])
    assert np.array_equal(a["has_window"], b["has_window"])
    assert np.array_equal(a["deadline"], b["deadline"])


def test_different_seeds_produce_different_distances():
    a = make_route(6, seed=1)
    b = make_route(6, seed=2)
    assert not np.array_equal(a["dist"], b["dist"])


def test_distances_span_close_to_the_full_documented_range_across_many_draws():
    """Statistischer Nachweis ueber viele Ziehungen (nicht nur eine Ziehung, die auch bei einer
    verkleinerten Obergrenze zufaellig innerhalb von <=1500 bleiben koennte): das dokumentierte Band
    200-1500 wird tatsaechlich (fast) ausgeschoepft, nicht nur nach oben begrenzt."""
    dists = []
    for seed in range(30):
        route = make_route(10, seed)
        dists.extend(route["dist"])
    assert max(dists) > 1450
    assert min(dists) < 250


def test_looser_factor_band_never_binds_deadlines_below_a_tighter_one():
    """Ein groesserer tight_lo/tight_hi-Faktor macht die Deadline (bei gleichem Seed/has_window) nie
    kleiner - direkte Konsequenz aus deadline = cum_econ * factor."""
    loose = make_route(6, seed=9, tight_share=1.0, tight_lo=1.2, tight_hi=1.2)
    tight = make_route(6, seed=9, tight_share=1.0, tight_lo=0.8, tight_hi=0.8)
    assert np.all(loose["deadline"] > tight["deadline"])
