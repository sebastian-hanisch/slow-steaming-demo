"""Loeser: wirtschaftliche Geschwindigkeit, drei Politiken (konstant/myopisch/exakt).

UNVERAENDERT aus seefracht-planung/messreihe_speed/speed.py uebernommen (economic_speed, solve_constant,
solve_myopic, solve_exact, leg_cost, total_cost, lateness) - bereits gegen die geschlossene Formel, eine
von Hand hergeleitete Handinstanz (KKT) und einen Optimalitaets-Regressionstest verifiziert (check.py,
0 Abweichungen in 61 Instanzen). NICHT neu implementieren.

Ein echter Bug wurde unterwegs gefunden und behoben (siehe ERGEBNIS.md): die urspruengliche Fassung von
solve_exact nutzte SLSQP mit res.success als Auswahlkriterium ueber mehrere Startpunkte. SLSQP meldete
bei etlichen Instanzen faelschlich success=False ("Positive directional derivative for linesearch"),
obwohl der gefundene Punkt bereits (fast) optimal UND zulaessig war - ein bekannter SLSQP-Stall nahe
aktiver Nebenbedingungen. Weil der gute Kandidat verworfen wurde, waehlte der Code einen SCHLECHTEREN
Kandidaten - mit der Folge, dass "exakt" teils teurer als myopisch war, obwohl "exakt" per Definition nie
schlechter sein darf. Fix: trust-constr statt SLSQP + eine EXPLIZITE Zulaessigkeitspruefung am Ergebnis
statt res.success. NICHT wieder auf res.success/SLSQP als alleiniges Kriterium umstellen - siehe
tests/test_solve.py::test_optimality_regression und ERGEBNIS.md fuer die volle Korrektur-Geschichte.

Sicherheitsnetz: trust-constr ist ueber maxiter=500 hart begrenzt (siehe solve_exact) - bei
infeasiblen/knappen Instanzen iteriert der Loeser spuerbar laenger (siehe ERGEBNIS.md), aber nie
unbegrenzt. Deshalb braucht die App einen sichtbaren Kurz-Ladeindikator statt reiner Live-Berechnung
ohne Anzeige (anders als leercontainer-demo/mehrhafenstau-demo)."""
import warnings

import numpy as np
from scipy.optimize import NonlinearConstraint, minimize

from sls_constants import V_MAX, V_MIN


def economic_speed(k, r, v_min=V_MIN, v_max=V_MAX):
    v = (r / (2 * k)) ** (1 / 3)
    return min(max(v, v_min), v_max)


def leg_cost(v, d, k, r):
    return k * d * v ** 2 + r * d / v


def total_cost(v, route):
    return float(np.sum(leg_cost(v, route["dist"], route["k"], route["r"])))


def leg_lateness(v, route):
    """Verspaetung JE Etappe (0, wo kein Fenster bindet oder es eingehalten wird) - fuer die
    Geschwindigkeitsprofil-Grafik (markiert verspaetete Etappen), nicht Teil des urspruenglichen
    speed.py, aber reine Zusatz-Ansicht auf dieselbe Rechnung wie lateness()."""
    cum = np.cumsum(route["dist"] / v)
    return np.where(np.isfinite(route["deadline"]), np.maximum(0.0, cum - route["deadline"]), 0.0)


def lateness(v, route):
    """Summe der Verspaetung an gebundenen Fenstern (0, wenn alle eingehalten) und Anzahl verspaeteter
    Etappen."""
    late = leg_lateness(v, route)
    return float(np.sum(late)), int(np.sum(late > 1e-6))


def solve_constant(route):
    return np.full(route["n_legs"], route["v_econ"])


def solve_myopic(route):
    """Je Etappe lokal: wenn ein Fenster bindet, die langsamste Geschwindigkeit, die es gerade noch
    einhaelt (spart Treibstoff, ohne zukuenftige Etappen zu beruecksichtigen); sonst wirtschaftliche
    Geschwindigkeit. Kennt nur die eigene Restdistanz und die verbleibende Zeit bis zum EIGENEN Fenster,
    nicht die Kette der spaeteren Fenster."""
    v = np.zeros(route["n_legs"])
    elapsed = 0.0
    for i in range(route["n_legs"]):
        d = route["dist"][i]
        if np.isfinite(route["deadline"][i]):
            remaining = route["deadline"][i] - elapsed
            needed = d / remaining if remaining > 0 else V_MAX * 10  # Fenster schon verpasst -> Vollgas
            v_i = min(max(needed, V_MIN), V_MAX)
        else:
            v_i = route["v_econ"]
        v[i] = v_i
        elapsed += d / v_i
    return v


def solve_exact(route, n_starts=1, seed=0):
    """Konvexes Problem, skalierte Variablen (v_i / V_MAX, siehe feedback_scipy_nlp_variable_scaling).
    trust-constr konvergiert auf denselben Startpunkten sauber (Restverletzung < 1e-9) und wird deshalb
    allein verwendet; Auswahl unter mehreren Startpunkten ueber eine EXPLIZITE Zulaessigkeitspruefung am
    Ergebnis, nicht ueber res.success (siehe Moduldocstring/ERGEBNIS.md). Gibt None zurueck, wenn keiner
    der Startpunkte einen zulaessigen Punkt liefert (Route bei dieser Einstellung nicht machbar)."""
    n = route["n_legs"]
    d, k, r, deadline = route["dist"], route["k"], route["r"], route["deadline"]
    lo, hi = V_MIN / V_MAX, 1.0

    def objective(x):
        v = x * V_MAX
        return np.sum(k * d * v ** 2 + r * d / v)

    def objective_grad(x):
        v = x * V_MAX
        dv = 2 * k * d * v - r * d / v ** 2
        return dv * V_MAX

    cons_list = []
    for i in range(n):
        if np.isfinite(deadline[i]):
            def cons(x, i=i):
                v = x * V_MAX
                cum = np.sum(d[:i + 1] / v[:i + 1])
                return deadline[i] - cum

            def cons_jac(x, i=i):
                v = x * V_MAX
                g = np.zeros(n)
                g[:i + 1] = d[:i + 1] / v[:i + 1] ** 2 * V_MAX
                return g

            cons_list.append((cons, cons_jac))

    def feasible(x, tol=1e-6):
        return all(c[0](x) >= -tol for c in cons_list)

    trust_constr = None
    if cons_list:
        def cons_vec(x):
            return np.array([c(x) for c, _ in cons_list])

        def cons_jac_vec(x):
            return np.array([j(x) for _, j in cons_list])

        trust_constr = [NonlinearConstraint(cons_vec, 0, np.inf, jac=cons_jac_vec)]

    rng = np.random.default_rng(seed)
    best_x, best_fun = None, None
    with warnings.catch_warnings():
        # trust-constr warnt harmlos ("delta_grad == 0.0"), wenn ein Startpunkt bereits (nahezu) am
        # Optimum liegt und die Quasi-Newton-Hesse-Aktualisierung degeneriert - kein Rechenfehler.
        warnings.filterwarnings("ignore", category=UserWarning)
        for s in range(n_starts):
            x0 = rng.uniform(lo, hi, n) if s > 0 else np.full(n, min(max(route["v_econ"] / V_MAX, lo), hi))
            if trust_constr:
                res = minimize(objective, x0, jac=objective_grad, method="trust-constr",
                                bounds=[(lo, hi)] * n, constraints=trust_constr,
                                options=dict(maxiter=500, gtol=1e-12, xtol=1e-14))
            else:
                res = minimize(objective, x0, jac=objective_grad, method="SLSQP",
                                bounds=[(lo, hi)] * n, options=dict(maxiter=300, ftol=1e-12))
            if feasible(res.x):
                fun = objective(res.x)
                if best_fun is None or fun < best_fun:
                    best_x, best_fun = res.x, fun
    if best_x is None:
        return None
    return best_x * V_MAX
