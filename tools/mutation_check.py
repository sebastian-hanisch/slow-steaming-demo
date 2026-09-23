"""Fehler-Einbau-Test: baut einzelne Fehler in die Module ein und prueft, ob die Tests (ohne AppTests,
die sind zu langsam fuer 20+ Mutanten) sie finden.

Aufruf (im Projektordner): ./venv/Scripts/python.exe tools/mutation_check.py [Teilstring des Dateinamens]
Jeder Mutant ersetzt genau eine Stelle; Ueberlebende sind entweder gleichwertig (kein sichtbarer
Unterschied) oder eine Luecke der Tests. Die Kopie liegt in einem temporaeren Ordner;
PYTHONDONTWRITEBYTECODE=1, damit veralteter Bytecode keine Ueberlebenden vortaeuscht; Quelltexte als
LF (Windows-Python schreibt sonst CRLF und die Zeichenketten unten finden nichts)."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
TIMEOUT = 240

MUTANTS = [
    # sls_solve.py - Kernloeser, siehe ERGEBNIS.md (echter Bug wurde hier schon einmal gefunden)
    ("sls_solve.py", "if best_fun is None or fun < best_fun:", "if best_fun is None or fun > best_fun:"),
    ("sls_solve.py", "return min(max(v, v_min), v_max)", "return max(max(v, v_min), v_max)"),
    ("sls_solve.py", "dv = 2 * k * d * v - r * d / v ** 2", "dv = 2 * k * d * v + r * d / v ** 2"),
    ("sls_solve.py", "return deadline[i] - cum", "return cum - deadline[i]"),
    ("sls_solve.py", "needed = d / remaining if remaining > 0 else V_MAX * 10", "needed = d / remaining if remaining >= 0 else V_MAX * 10"),
    ("sls_solve.py", "return np.where(np.isfinite(route[\"deadline\"]), np.maximum(0.0, cum - route[\"deadline\"]), 0.0)",
                     "return np.where(np.isfinite(route[\"deadline\"]), np.minimum(0.0, cum - route[\"deadline\"]), 0.0)"),
    ("sls_solve.py", "return all(c[0](x) >= -tol for c in cons_list)", "return all(c[0](x) >= tol for c in cons_list)"),
    # sls_scenario.py
    ("sls_scenario.py", "dist = rng.uniform(200, 1500, n_legs)", "dist = rng.uniform(200, 1000, n_legs)"),
    ("sls_scenario.py", "has_window = rng.random(n_legs) < tight_share", "has_window = rng.random(n_legs) <= tight_share"),
    ("sls_scenario.py", "deadline = np.where(has_window, cum_econ * factor, np.inf)", "deadline = np.where(has_window, np.inf, cum_econ * factor)"),
    # sls_evaluation.py
    ("sls_evaluation.py", "return (m_policy - m_exact) / m_exact * 100.0", "return (m_exact - m_policy) / m_exact * 100.0"),
    ("sls_evaluation.py", "return 100.0 * sum(1 for r in feas if getattr(r, n_late_attr) > 0) / len(feas)",
                          "return 100.0 * sum(1 for r in feas if getattr(r, n_late_attr) >= 0) / len(feas)"),
    ("sls_evaluation.py", "kind = \"unclear\" if diff == 0 else \"better\"", "kind = \"unclear\" if diff == 0 else \"worse\""),
    ("sls_evaluation.py", "kind = \"unclear\" if abs(diff) <= C.VERDICT_Z * se else (\"better\" if diff < 0 else \"worse\")",
                          "kind = \"unclear\" if abs(diff) < C.VERDICT_Z * se else (\"better\" if diff < 0 else \"worse\")"),
    ("sls_evaluation.py", "markup = ((shown.cost_exact - shown.cost_const) / shown.cost_const * 100.0) if shown.cost_const else 0.0",
                          "markup = ((shown.cost_const - shown.cost_exact) / shown.cost_const * 100.0) if shown.cost_const else 0.0"),
    # sls_stories.py
    ("sls_stories.py", "(myo_late is not None and myo_late >= 15.0,", "(myo_late is not None and myo_late > 15.0,"),
    ("sls_stories.py", "(const_late is not None and const_late == 0.0,", "(const_late is not None and const_late <= 0.0,"),
    ("sls_stories.py", "(myo_late is not None and myo_late <= 30.0,", "(myo_late is not None and myo_late < 30.0,"),
    ("sls_stories.py", "return [(n_infeasible == n, f\"0 von {n} Stichproben-Routen machbar: {n - n_infeasible}/{n}\")]",
                       "return [(n_infeasible >= n, f\"0 von {n} Stichproben-Routen machbar: {n - n_infeasible}/{n}\")]"),
    # sls_presets.py
    ("sls_presets.py", "value = max(spec.lo, value)\n    if spec.hi is not None:", "value = value\n    if spec.hi is not None:"),
    ("sls_presets.py", "value = spec.lo + round((value - spec.lo) / spec.step) * spec.step",
                       "value = spec.lo + int((value - spec.lo) / spec.step) * spec.step"),
]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sls_mut_"))
    for f in ROOT.glob("*.py"):
        shutil.copy(f, tmp / f.name)
    shutil.copytree(ROOT / "tests", tmp / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    for f in tmp.glob("*.py"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    survivors, errors, killed = [], [], 0
    for n, (name, old, new) in enumerate(MUTANTS, 1):
        if only and only not in name:
            continue
        path = tmp / name
        original = path.read_bytes().decode("utf-8")
        if original.count(old) != 1:
            errors.append((n, name, old[:60], original.count(old)))
            continue
        path.write_bytes(original.replace(old, new).encode("utf-8"))
        try:
            r = subprocess.run([PY, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "tests", "--ignore=tests/test_app.py"],
                               cwd=tmp, env=env, capture_output=True, text=True, timeout=TIMEOUT)
            survived = r.returncode == 0
        except subprocess.TimeoutExpired:
            survived = False           # Endlosschleife gilt als gefunden
            print(f"[{n:3d}] Zeitueberschreitung (als gefunden gezaehlt)  {name}", flush=True)
        path.write_bytes(original.encode("utf-8"))
        if survived:
            survivors.append((n, name, old[:70], new[:70]))
            print(f"[{n:3d}] UEBERLEBT  {name}: {old[:60]!r} -> {new[:60]!r}", flush=True)
        else:
            killed += 1
            print(f"[{n:3d}] gefunden  {name}", flush=True)
    print(f"\n{killed} gefunden, {len(survivors)} ueberlebt, {len(errors)} Fehler in der Mutantenliste")
    for e in errors:
        print("  FEHLER (Stelle nicht eindeutig gefunden):", e)
    shutil.rmtree(tmp, ignore_errors=True)
    return len(survivors) == 0 and len(errors) == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
