"""
Geschwindigkeitsoptimierung (Slow Steaming) - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Welle 3 der Seefracht-Linie: eine Reederei kann Treibstoff sparen, indem sie langsamer faehrt -
Verbrauch steigt mit der dritten Potenz der Geschwindigkeit. Aber manche Haefen haben feste Zeitfenster
(Kaiplatz-Slot, Tide, Anschlussverkehr): wer zu langsam faehrt, verpasst sie. Anders als die ersten beiden
Wellen (Kombinatorik) ist das hier ein stetiges, konvexes Optimierungsproblem (scipy).

Lauffaehig mit: streamlit run app.py
"""
import streamlit as st

import sls_constants as C
import sls_evaluation as E
import sls_visualization as V
from sls_pdf_export import generate_sls_pdf
from sls_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings,
                         randomize_seed, SETTING_SPECS, sync_query_params)
from sls_scenario import make_route
from sls_solve import lateness, solve_constant, solve_exact, solve_myopic, total_cost
from sls_ui_panel import render_comparison_tab, render_metrics, render_policy_panel

st.set_page_config(page_title="Geschwindigkeitsoptimierung - Sebastian Hanisch", layout="wide")

SCENARIO_KEYS = list(SETTING_SPECS)


@st.cache_data(show_spinner=C.SOLVE_SPINNER_TEXT, max_entries=64)
def _compute_shown(n_legs, seed, tight_share, tight_lo, tight_hi, k, r):
    route = make_route(n_legs, seed, k=k, r=r, tight_share=tight_share, tight_lo=tight_lo, tight_hi=tight_hi)
    v_exact = solve_exact(route)
    v_myo = solve_myopic(route)
    v_const = solve_constant(route)
    cost_exact = total_cost(v_exact, route) if v_exact is not None else None
    late_myo, n_late_myo = lateness(v_myo, route)
    late_const, n_late_const = lateness(v_const, route)
    shown = E.RouteResult(
        seed=seed, n_windows=int(route["has_window"].sum()),
        v_exact=tuple(v_exact) if v_exact is not None else None, v_myo=tuple(v_myo), v_const=tuple(v_const),
        cost_exact=cost_exact, cost_myo=total_cost(v_myo, route), cost_const=total_cost(v_const, route),
        late_myo=late_myo, n_late_myo=n_late_myo, late_const=late_const, n_late_const=n_late_const,
    )
    return route, v_exact, v_myo, v_const, shown


@st.cache_data(show_spinner="Rechne Stichprobe (30 Routen) …", max_entries=32)
def _compute_sample(n_legs, tight_share, tight_lo, tight_hi, k, r, n):
    p = E.Params(n_legs, tight_share, tight_lo, tight_hi, k, r)
    return E.sample(p, n)


st.title("⛴️ Geschwindigkeitsoptimierung: Fenster halten statt nur sparen")
st.markdown(
    """
Eine Reederei kann Treibstoff sparen, indem sie **langsamer fährt** - der Verbrauch steigt mit der **dritten Potenz** der Geschwindigkeit. Aber manche Häfen haben feste Zeitfenster (Kaiplatz-Slot,
Tide, Anschlussverkehr): wer zu langsam fährt, verpasst sie. Diese Demo zeigt, wie viel es wirklich kostet, jedes **Ankunftsfenster** zuverlässig einzuhalten - und was passiert, wenn man Fenster nur
lokal oder gar nicht berücksichtigt. Wie das Modell funktioniert, steht im Expander "Wie funktioniert diese Demo?" weiter unten, die formale Beschreibung im Expander "📐 Mathematische Formulierung".
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
PRESET_HELP = {
    "Locker": "Fenster binden selten - trotzdem verpasst myopisch schon spürbar oft.",
    "Mittel": "Der Grundfall: reale Lücke zwischen allen drei Politiken.",
    "Eng, machbar": "Nah an der Kapazitätsgrenze, aber exakt schafft es immer noch - konstant fast nie.",
    "Viele Fenster": "Jede Etappe zählt - kaskadierende Effekte werden bei myopisch am deutlichsten.",
    "Nicht machbar": "Ehrlicher Grenzfall: diese Fenster sind mit KEINER Politik einzuhalten, auch nicht mit Vollgas.",
}
preset_names = list(C.PRESETS.keys())
for row in (preset_names[:3], preset_names[3:]):
    cols = st.columns(3)
    for col, name in zip(cols, row):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=PRESET_HELP[name])

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_legs = st.slider("Etappen", *bounds("n_legs_slider"), key="n_legs_slider", help="Routenlänge.")
    window_share = st.slider("Anteil mit Fenster", *bounds("window_share_slider"), key="window_share_slider",
                             step=C.WINDOW_SHARE_STEP, format="%d%%", help="Anteil der Etappen mit hartem spätesten Ankunftsfenster.")
    tightness = st.select_slider("Fenster-Enge", options=list(C.TIGHTNESS_LEVELS), key="tightness_select", help=C.TIGHTNESS_HELP)
    rate_ratio = st.select_slider("Bunker-/Charter-Verhältnis", options=list(C.RATE_RATIO_LEVELS), key="rate_ratio_select", help=C.RATE_RATIO_HELP)
    seed = st.number_input("Seed", *bounds("seed_input"), key="seed_input", step=1, help="Bestimmt Distanzen und welche Etappen ein Fenster bekommen.")
    st.button("🎲 Neue Route", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Seed für die Route.")

sync_query_params({key: st.session_state[key] for key in SCENARIO_KEYS})

n_legs, window_share, seed = int(n_legs), int(window_share), int(seed)
p = E.params_from_controls(n_legs, window_share, tightness, rate_ratio)

route, v_exact, v_myo, v_const, shown = _compute_shown(p.n_legs, seed, p.tight_share, p.tight_lo, p.tight_hi, p.k, p.r)
diag = E.diagnose(shown)

# ---------------------------------------------------------------------------------------------------
# Hauptansicht
# ---------------------------------------------------------------------------------------------------
st.markdown("## 🎯 Werden alle Fenster eingehalten?")
st.caption(f"{n_legs} Etappen, {window_share} % mit Fenster, Fenster-Enge {tightness}, Bunker-/Charter-Verhältnis {rate_ratio}, Seed {seed}.")

metric_rows = [st.columns(2), st.columns(2)]
render_metrics(metric_rows[0] + metric_rows[1], shown, diag)

if diag.kind == "infeasible":
    st.error("⛔ Diese Fenster sind selbst mit Vollgas nicht einzuhalten - mindestens ein Fenster lockern oder die Route verkürzen.")
else:
    markup = diag.markup_vs_const_pct
    if markup is not None and markup > 0.5:
        st.success(f"✅ Machbar: alle {diag.n_windows} Fenster eingehalten, **{markup:.2f} % teurer** als die Politik konstant.")
    elif markup is not None and markup < -0.5:
        st.success(f"✅ Machbar: alle {diag.n_windows} Fenster eingehalten, sogar **{abs(markup):.2f} % billiger** als die Politik konstant (Zufall der Route).")
    else:
        st.success(f"✅ Machbar: alle {diag.n_windows} Fenster eingehalten, bei **praktisch gleichen Kosten** wie die Politik konstant ({markup:+.2f} %).")

st.markdown("#### 🚢 Geschwindigkeitsprofil (alle drei Politiken)")
st.plotly_chart(V.speed_profile_figure(route, v_exact, v_myo, v_const), width="stretch", key="main_profile_chart")
st.caption("Grau hinterlegt = Etappe mit Ankunftsfenster; ✕ = Fenster verpasst (Verspätung in Zeiteinheiten).")

pdf_slot = st.container()

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Kernabschnitt
# ---------------------------------------------------------------------------------------------------
st.markdown("### 📐 Wie viel kostet Zuverlässigkeit wirklich?")
st.markdown(
    """
Kernfrage dieser Demo: wie teuer ist es, **alle** Fenster zuverlässig einzuhalten - im Vergleich zu einer Politik, die Fenster ignoriert (konstant) oder nur lokal beachtet (myopisch)? Die Kostenachse
allein erzählt die falsche Geschichte: der Unterschied ist **klein**. Die Verspätungsachse zeigt den eigentlichen Hook - **nur** die gemeinsame Optimierung hält garantiert alle erreichbaren Fenster ein.
"""
)
sample_results = _compute_sample(p.n_legs, p.tight_share, p.tight_lo, p.tight_hi, p.k, p.r, C.SAMPLE_INSTANCES)
gap_myo = E.cost_gap_pct(sample_results, C.POLICY_MYOPIC)
gap_const = E.cost_gap_pct(sample_results, C.POLICY_CONST)
late_myo = E.late_share_pct(sample_results, C.POLICY_MYOPIC)
late_const = E.late_share_pct(sample_results, C.POLICY_CONST)

st.plotly_chart(V.comparison_bars_figure(gap_myo, gap_const, late_myo, late_const), width="stretch", key="main_comparison_chart")
st.caption(f"Basis: {C.SAMPLE_INSTANCES} Stichprobenrouten derselben Einstellung (nicht der eingestellte Seed), nur die für exakt machbaren. Rechenzeit gemessen: ein solve_exact-Aufruf "
          f"braucht je nach Einstellung und Rechner größenordnungsmäßig 0,1-0,3 s (hier gemessen, 6-7 Etappen), bei nicht machbaren Instanzen spürbar mehr - deshalb der Ladeindikator statt einer Live-Berechnung ohne Anzeige.")

st.markdown("**Urteil über die Stichprobe** (gepaarte Differenz je Route, klar ab mehr als zwei Standardfehlern)")
v = E.verdict(sample_results)
if v.n == 0:
    st.info("ℹ️ Kein Vergleich möglich: keine Route der Stichprobe ist für die Politik exakt machbar.")
elif v.kind == "better":
    st.success(f"✅ **Exakt gegen myopisch**: im Mittel **{abs(v.diff):.1f} Prozentpunkte weniger Verspätungen** je Route (Differenz {v.diff:+.1f}, Standardfehler {v.se:.1f}, n={v.n}).")
elif v.kind == "worse":
    st.warning(f"⚠️ **Exakt gegen myopisch**: im Mittel **{abs(v.diff):.1f} Prozentpunkte mehr Verspätungen** je Route (Differenz {v.diff:+.1f}, Standardfehler {v.se:.1f}, n={v.n}).")
else:
    st.info(f"ℹ️ Kein klarer Unterschied zwischen exakt und myopisch bei dieser Einstellung (Differenz {v.diff:+.1f}, Standardfehler {v.se:.1f}, n={v.n}).")

with pdf_slot:
    st.download_button(
        "📄 Ergebnis als PDF herunterladen",
        data=generate_sls_pdf(n_legs, window_share, tightness, rate_ratio, seed, shown, diag, gap_myo, gap_const,
                              late_myo, late_const, verdict=v),
        file_name="geschwindigkeitsoptimierung_ergebnis.pdf", mime="application/pdf", key="primary_pdf_download",
        help="Route, Kosten je Politik, Diagnose, Zwei-Achsen-Vergleich und die Stichprobe mit Urteil.")

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Politiken im Vergleich
# ---------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – Politiken im Vergleich"):
    tabs = st.tabs([C.POLICY_LABELS[C.POLICY_CONST], C.POLICY_LABELS[C.POLICY_MYOPIC], C.EXACT_TAB_LABEL, C.COMPARISON_TAB_LABEL])
    with tabs[0]:
        render_policy_panel("tab_const", C.POLICY_CONST, route, v_exact, v_myo, v_const, shown)
    with tabs[1]:
        render_policy_panel("tab_myo", C.POLICY_MYOPIC, route, v_exact, v_myo, v_const, shown)
    with tabs[2]:
        render_policy_panel("tab_exact", C.POLICY_EXACT, route, v_exact, v_myo, v_const, shown)
    with tabs[3]:
        render_comparison_tab(gap_myo, gap_const, late_myo, late_const)

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Route und Fenster.** N Etappen mit Distanz d_i; Geschwindigkeit v_i frei wählbar in [10, 24] kn je Etappe. Treibstoffkosten je Etappe ~ Distanz x Geschwindigkeit² (Verbrauch ~ v³, Zeit = Distanz/v),
Charter-/Kapitalkosten ~ Distanz/Geschwindigkeit. Ein Teil der Etappen hat zusätzlich ein hartes **spätestes** Ankunftsfenster (fester Kaiplatz-Slot, Tide, Anschluss) - das bricht die Konstanz der
wirtschaftlichen Geschwindigkeit v* und macht aus der Aufgabe ein echtes, konvexes Optimierungsproblem.

**Die drei Politiken und warum "lokal klug" (myopisch) trotzdem global versagen kann.** Konstant ignoriert Fenster komplett - die Kontrast-Baseline. Myopisch wählt je Etappe lokal die langsamste
Geschwindigkeit, die das EIGENE Fenster gerade noch schafft, ohne spätere Etappen zu berücksichtigen - das kann sich rächen: das Ausreizen des eigenen Fensters (so langsam wie gerade noch möglich) auf einer früheren Etappe kann eine spätere
Etappe unerreichbar machen, selbst mit Vollgas. Exakt optimiert gemeinsam über die ganze Route (trust-constr) und hält alle Fenster ein, wo das physikalisch überhaupt möglich ist.

**Warum die Kostenachse allein die falsche Geschichte erzählt.** Der Kostenunterschied zwischen den Politiken ist klein (myopisch nur 0,6-4,6 % teurer als exakt in den getesteten Einstellungen) - die
quadratische Kostenkurve um v* ist in der Nähe des Optimums flach. Der eigentliche Unterschied ist die **Verspätung**: konstant verpasst Fenster oft in der Mehrheit der Fälle, myopisch trotz lokaler
Vorsicht immer noch spürbar oft. Nur die gemeinsame Optimierung ist zuverlässig UND fast genauso günstig.

**Grenzen dieses Modells** (bewusst so gewählt, damit die Aussage ehrlich bleibt):

- **Nur ein spätestes Fenster je Etappe** (kein frühestes/Warten, keine Liegeplatz-Wartezeit).
- **Distanzen und Fenster-Enge synthetisch erzeugt**, nicht an echten Bunkerpreisen/Charterraten/Hafenfenstern kalibriert.
- **Kein Wetter, keine Strömung, keine Geschwindigkeitsschwankung durch Wellengang.**
- **Rechenzeit bei knappen/nicht machbaren Instanzen ist spürbar höher** als bei komfortablen (der Löser iteriert länger, bevor er aufgibt) - deshalb der Ladeindikator statt reiner Live-Berechnung.
- **Nähe zur Mehrhafen-Stauplanung**: beide behandeln dieselbe Route, aber dort geht es darum WO Container stehen, hier darum WIE SCHNELL das Schiff fährt.
        """
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Route.** Etappe $i \in \{0, \dots, N-1\}$ mit Distanz $d_i$, Geschwindigkeit $v_i \in [v_{\min}, v_{\max}] = [10, 24]$ kn; Kosten je Etappe $k \cdot d_i \cdot v_i^2 + r \cdot d_i / v_i$.

**Wirtschaftliche Geschwindigkeit.** Ohne Nebenbedingung ist $v^\ast = (r / (2k))^{1/3}$ auf JEDER Etappe optimal, unabhängig von der Distanz - aus der Ableitung nach $v_i$ (klassisches Ergebnis der
Schifffahrtsökonomie, Ronen 1982).

**Ankunftsfenster.** Ein Teil der Etappen hat ein hartes spätestes Ankunftsfenster: kumulierte Fahrzeit bis inklusive Etappe $j$ muss $\leq \text{deadline}_j$ sein.

**Mit EINEM bindenden Fenster bei Etappe $j$:** alle Etappen $0..j$ fahren gemeinsam mit $v_j' = (\sum_{i \leq j} d_i) / \text{deadline}_j$ (KKT, ein aktiver Multiplikator), Etappen danach zurück auf $v^\ast$.

**Allgemeiner Fall (mehrere Fenster).** Konvexes Optimierungsproblem, gelöst mit `trust-constr` (scipy); die Handinstanz mit einem Fenster dient als Beweis-Cross-Check
(`tests/test_solve.py::test_hand_derived_single_window_instance`).

**Optimalitäts-Regressionstest.** Für jede Instanz muss der Preis von "exakt" $\leq$ dem Preis jeder anderen zulässigen Lösung sein (z. B. myopisch, wenn sie selbst zufällig alle Fenster einhält) -
dieser Test hat einen echten Implementierungsfehler gefangen (SLSQP + `res.success` verwarf fälschlich gute Kandidaten, siehe README).

Implementiert in `sls_scenario.py` (Route), `sls_solve.py` (`economic_speed`, `solve_constant`, `solve_myopic`, `solve_exact`) und `sls_evaluation.py` (Stichprobe, Kostenaufschlag, Verspätungsanteil,
Urteil, Diagnose).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Seefracht optimieren](https://sebastianhanisch.net/seefracht-optimierung.html)."
)
