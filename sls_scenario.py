"""Szenario: eine Route aus N Etappen mit Distanz d_i und optionalem spaetesten Ankunftsfenster.

UNVERAENDERT aus seefracht-planung/messreihe_speed/speed.py (make_route) uebernommen - gegen die
geschlossene Formel und eine von Hand hergeleitete Handinstanz verifiziert (check.py). Nur ein spaetestes
Fenster je Etappe (kein fruehestes/Warten), siehe Plan Abschnitt 2/13."""
import numpy as np

from sls_solve import economic_speed


def make_route(n_legs, seed, k=1.0, r=11664.0, tight_share=0.5, tight_lo=0.82, tight_hi=1.15):
    """n_legs Etappen, Distanzen 200-1500 sm. tight_share der Etappen bekommt ein spaetestes
    Ankunftsfenster: kumulierte Fahrzeit bis inkl. dieser Etappe bei wirtschaftlicher Geschwindigkeit,
    multipliziert mit einem Faktor in [tight_lo, tight_hi] (< 1 = enger als wirtschaftlich, zwingt zum
    Schnellerfahren; > 1 = lockerer, nie bindend)."""
    rng = np.random.default_rng(seed)
    dist = rng.uniform(200, 1500, n_legs)
    v_econ = economic_speed(k, r)
    cum_econ = np.cumsum(dist / v_econ)
    has_window = rng.random(n_legs) < tight_share
    factor = rng.uniform(tight_lo, tight_hi, n_legs)
    deadline = np.where(has_window, cum_econ * factor, np.inf)
    return dict(n_legs=n_legs, dist=dist, k=k, r=r, deadline=deadline, has_window=has_window,
                v_econ=v_econ)
