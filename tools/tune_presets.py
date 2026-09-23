"""Preset-Abstimmung: prueft sls_constants.PRESETS gegen sls_stories-Kriterien ueber
POPULATION_INSTANCES echte Stichprobenrouten (Muster tools/tune_presets.py aus mehrhafenstau-demo).

Ausserdem ein kleiner Grid-Search-Modus (--search), um Kandidaten fuer ein bestimmtes Preset zu finden
(vor allem fuer "Nicht machbar", das eine echte Solver-Infeasibilitaet braucht statt nur eines
Kosten-/Verspaetungs-Schwellenwerts)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import sls_constants as C  # noqa: E402
import sls_evaluation as E  # noqa: E402
import sls_stories as ST  # noqa: E402


def params_for(n_legs, window_share, tightness, rate_ratio):
    return E.params_from_controls(n_legs, window_share, tightness, rate_ratio)


def check_all():
    all_ok = True
    for name, cfg in C.PRESETS.items():
        p = params_for(cfg["n_legs"], cfg["window_share"], cfg["tightness"], cfg["rate_ratio"])
        pop = E.sample(p, C.POPULATION_INSTANCES)
        print(f"\n=== {name} (n_legs={cfg['n_legs']}, window_share={cfg['window_share']}%, "
              f"tightness={cfg['tightness']}, rate_ratio={cfg['rate_ratio']}, seed={cfg['seed']}) ===")
        for ok, text in ST.criteria(name, pop):
            print(("  OK " if ok else "  FAIL"), text)
            all_ok = all_ok and ok
        shown = E.route_result(p, cfg["seed"])
        for ok, text in ST.shown_criteria(name, shown):
            print(("  OK(shown) " if ok else "  FAIL(shown)"), text)
            all_ok = all_ok and ok
        print(f"  seed >= POPULATION_INSTANCES ({C.POPULATION_INSTANCES}): {'OK' if cfg['seed'] >= C.POPULATION_INSTANCES else 'FAIL'}")
        all_ok = all_ok and cfg["seed"] >= C.POPULATION_INSTANCES
    print("\nALLE PRESETS OK" if all_ok else "\nMINDESTENS EIN PRESET FEHLGESCHLAGEN")
    return all_ok


def search_infeasible():
    """Sucht eine Kombination, die 60/60 Stichprobenrouten fuer 'exakt' nicht machbar macht."""
    print("Suche nach vollstaendig infeasibler Kombination ...")
    for tightness in ("Eng", "Mittel"):
        for rate_ratio in ("Sehr hoch (v*=23 kn)", "Hoch (v*=21 kn)"):
            for window_share in (100, 80):
                for n_legs in (6, 8, 10):
                    p = params_for(n_legs, window_share, tightness, rate_ratio)
                    pop = E.sample(p, C.POPULATION_INSTANCES)
                    n_inf = E.infeasible_count(pop)
                    print(f"n_legs={n_legs} window_share={window_share} tightness={tightness} "
                          f"rate_ratio={rate_ratio}: {n_inf}/{C.POPULATION_INSTANCES} infeasible")
                    if n_inf == C.POPULATION_INSTANCES:
                        print("  -> VOLLSTAENDIG INFEASIBLE, Kandidat gefunden")
                        return dict(n_legs=n_legs, window_share=window_share, tightness=tightness, rate_ratio=rate_ratio)
    print("Keine vollstaendig infeasible Kombination in diesem Suchraster gefunden.")
    return None


if __name__ == "__main__":
    if "--search" in sys.argv:
        search_infeasible()
    else:
        ok = check_all()
        sys.exit(0 if ok else 1)
