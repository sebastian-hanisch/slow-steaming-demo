"""Orakel-Test mit anderem Rechenweg: Lagrange-Dualität in den Fahrzeiten t_i = d_i/v_i (dort sind die Fenster linear). Der Dualwert ist eine
untere Schranke jeder zulässigen Lösung; stimmt der Kostenwert von solve_exact damit überein, ist er bewiesen optimal. Außerdem: "nicht machbar"
genau dann, wenn schon Höchstgeschwindigkeit ein Fenster verfehlt."""
import numpy as np
import pytest

pytest.importorskip("scipy")
from scipy.optimize import minimize

from sls_constants import V_MAX, V_MIN
from sls_scenario import make_route
from sls_solve import economic_speed, solve_exact, total_cost


def _dual_bound(route):
    d, k, r, dl = route["dist"], route["k"], route["r"], route["deadline"]
    n = len(d)
    lo, hi = d / V_MAX, d / V_MIN
    idx = [i for i in range(n) if np.isfinite(dl[i])]

    def legs(mu):
        t = np.clip((2 * k * d ** 3 / (r + mu)) ** (1 / 3), lo, hi)
        return t, k * d ** 3 / t ** 2 + (r + mu) * t

    def mu_of(lam):
        full = np.zeros(n)
        full[idx] = lam
        return np.cumsum(full[::-1])[::-1]

    def negq(z):
        lam = z * r
        t, val = legs(mu_of(lam))
        grad = (np.cumsum(t)[idx] - dl[idx]) * r
        return -(val.sum() - lam @ dl[idx]), -grad

    if not idx:
        return legs(np.zeros(n))[1].sum()
    res = minimize(negq, np.zeros(len(idx)), jac=True, bounds=[(0, None)] * len(idx), method="L-BFGS-B", options=dict(maxiter=5000, ftol=1e-15, gtol=1e-12, maxcor=30))
    return -res.fun


CASES = [dict(n_legs=n, seed=s, tight_share=share, tight_lo=lo, tight_hi=hi, r=r)
         for n, s, share, lo, hi, r in [(6, 201, 0.5, 0.95, 1.1, 11664.0), (6, 201, 0.4, 0.9, 1.0, 11664.0), (7, 233, 1.0, 0.95, 1.1, 2 * 15.0 ** 3),
                                        (4, 7, 1.0, 0.95, 1.1, 11664.0), (9, 3, 0.8, 0.9, 1.0, 2 * 21.0 ** 3), (5, 11, 0.6, 1.0, 1.3, 2 * 12.0 ** 3),
                                        (8, 5, 1.0, 0.9, 1.0, 11664.0), (10, 2, 0.5, 0.9, 1.0, 11664.0), (3, 4, 1.0, 0.9, 1.0, 2 * 23.0 ** 3),
                                        (6, 60, 1.0, 0.9, 1.0, 2 * 23.0 ** 3), (7, 8, 0.0, 0.9, 1.0, 11664.0), (5, 9, 0.7, 0.82, 1.15, 11664.0)]]


@pytest.mark.parametrize("c", CASES)
def test_solve_exact_matches_the_lagrange_dual_certificate_or_is_correctly_infeasible(c):
    route = make_route(c["n_legs"], c["seed"], r=c["r"], tight_share=c["tight_share"], tight_lo=c["tight_lo"], tight_hi=c["tight_hi"])
    fast_ok = bool(np.all(np.cumsum(route["dist"] / V_MAX) <= route["deadline"] + 1e-9))
    v = solve_exact(route)
    if not fast_ok:
        assert v is None                                                                    # unerreichbar: schon V_MAX verfehlt ein Fenster
        return
    assert v is not None
    assert np.all(v >= V_MIN - 1e-9) and np.all(v <= V_MAX + 1e-9)
    assert np.all(np.cumsum(route["dist"] / v) <= route["deadline"] + 1e-6)
    q = _dual_bound(route)
    assert total_cost(v, route) >= q * (1 - 1e-9)                                           # keine zulässige Lösung unter der Dualschranke
    assert total_cost(v, route) == pytest.approx(q, rel=1e-6)                                 # ... und solve_exact erreicht sie


def test_unconstrained_cost_equals_the_closed_form():
    route = make_route(6, 1, tight_share=0.0)
    v = solve_exact(route)
    ve = economic_speed(route["k"], route["r"])
    assert np.allclose(v, ve, atol=1e-6)
    assert total_cost(v, route) == pytest.approx(float(np.sum(route["k"] * route["dist"] * ve ** 2 + route["r"] * route["dist"] / ve)), rel=1e-9)
