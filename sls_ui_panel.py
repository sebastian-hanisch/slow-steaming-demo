"""Wiederverwendbares Panel: Kennzahlen (2 x 2), Politik-Tabs (Konstant/Myopisch/Exakt/Vergleich) -
Plan Abschnitt 6/8."""
import pandas as pd
import streamlit as st

import sls_constants as C
import sls_visualization as V


def fmt_pct(v, sign=False):
    if v is None:
        return "–"
    return f"{v:+.1f} %" if sign else f"{v:.1f} %"


def fmt_cost(v):
    return "–" if v is None else f"{v:,.0f}".replace(",", ".")


def render_metrics(columns, shown, diag):
    """Vier Kennzahlen (Plan Abschnitt 6): Fenster eingehalten (von N, exakt), Kostenaufschlag gegen
    konstant, Gesamtkosten (exakt), Status."""
    m = columns
    windows_txt = "–" if diag.n_windows_met is None else f"{diag.n_windows_met} / {diag.n_windows}"
    m[0].metric("Fenster eingehalten (exakt)", windows_txt, help="Anzahl eingehaltener Ankunftsfenster von insgesamt N auf der gezeigten Route (Politik exakt).")
    m[1].metric("Kostenaufschlag gegen konstant", fmt_pct(diag.markup_vs_const_pct, sign=True), delta_color="inverse",
                help="(Kosten exakt - Kosten konstant) / Kosten konstant. Kann leicht negativ sein - konstant ignoriert Fenster und ist deshalb manchmal minimal billiger.")
    m[2].metric("Gesamtkosten (exakt)", fmt_cost(shown.cost_exact) if shown.cost_exact is not None else "nicht machbar",
                help="Treibstoff- und Charterkosten der Politik exakt auf der gezeigten Route.")
    status_txt = "✅ machbar" if diag.kind == "feasible" else "⛔ nicht machbar"
    m[3].metric("Status", status_txt, help="Ob die Politik exakt alle Ankunftsfenster dieser Route einhalten kann.")


def render_policy_panel(prefix, policy, route, v_exact, v_myo, v_const, shown):
    """Beschreibung, Kennzahl und Geschwindigkeitsprofil einer Politik (je Tab im Politik-Expander)."""
    st.markdown(C.POLICY_DESCRIPTIONS[policy])
    v_map = {C.POLICY_EXACT: v_exact, C.POLICY_MYOPIC: v_myo, C.POLICY_CONST: v_const}
    cost_map = {C.POLICY_EXACT: shown.cost_exact, C.POLICY_MYOPIC: shown.cost_myo, C.POLICY_CONST: shown.cost_const}
    n_late_map = {C.POLICY_EXACT: 0 if shown.cost_exact is not None else None, C.POLICY_MYOPIC: shown.n_late_myo, C.POLICY_CONST: shown.n_late_const}
    v, cost, n_late = v_map[policy], cost_map[policy], n_late_map[policy]
    if policy == C.POLICY_EXACT and v is None:
        st.warning("⚠️ Diese Fenster sind selbst mit Vollgas nicht einzuhalten - keine Lösung für diese Politik auf der gezeigten Route.")
        return
    col1, col2 = st.columns(2)
    col1.metric("Gesamtkosten", fmt_cost(cost))
    col2.metric("Fenster verpasst", str(n_late) if n_late is not None else "–")
    only_exact = v if policy == C.POLICY_EXACT else None
    only_myo = v if policy == C.POLICY_MYOPIC else None
    only_const = v if policy == C.POLICY_CONST else None
    st.plotly_chart(V.speed_profile_figure(route, only_exact, only_myo, only_const), width="stretch", key=f"{prefix}_profile_chart")


def render_comparison_tab(gap_myo, gap_const, late_myo, late_const):
    rows = []
    for policy in (C.POLICY_EXACT, C.POLICY_MYOPIC, C.POLICY_CONST):
        gap = 0.0 if policy == C.POLICY_EXACT else (gap_myo if policy == C.POLICY_MYOPIC else gap_const)
        late = 0.0 if policy == C.POLICY_EXACT else (late_myo if policy == C.POLICY_MYOPIC else late_const)
        rows.append({
            "Politik": C.POLICY_LABELS[policy],
            "Kostenaufschlag gegen exakt": "–" if gap is None else f"{gap:+.2f} %",
            "Verspätungsanteil (Stichprobe)": "–" if late is None else f"{late:.1f} %",
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.plotly_chart(V.comparison_bars_figure(gap_myo, gap_const, late_myo, late_const), width="stretch", key="comparison_tab_bars_chart")
    st.caption(f"Basis: {C.SAMPLE_INSTANCES} Stichprobenrouten derselben Einstellung (nicht der eingestellte Seed), nur die für exakt machbaren.")
