"""Plotly-Figuren der Geschwindigkeitsoptimierung: Geschwindigkeitsprofil (Politik je Etappe, verspaetete
Etappen markiert) und Zwei-Achsen-Vergleich (Kostenaufschlag % und Verspaetungsanteil % je Politik).

Konventionen des Portfolios: Achsen `fixedrange` (Touch-Scrollen), Vorlage plotly_white, Marker-Linien
konsistent gruen/rot/grau ueber alle drei Politiken. Plotly wird erst in den Funktionen importiert, damit
die reine Rechnung ohne Plotly testbar bleibt."""
import numpy as np

import sls_constants as C
from sls_solve import leg_lateness

LEGEND_BOTTOM = dict(orientation="h", yref="container", yanchor="bottom", y=0.0, x=0)


def _lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


# ---------------------------------------------------------------------------------------------------
# Geschwindigkeitsprofil (Hauptansicht und Politik-Tabs)
# ---------------------------------------------------------------------------------------------------
def speed_profile_figure(route, v_exact, v_myo, v_const):
    """v_exact kann None sein (nicht machbar) - dann wird nur myopisch/konstant gezeigt."""
    import plotly.graph_objects as go

    n = route["n_legs"]
    legs = list(range(1, n + 1))
    fig = go.Figure()

    def add_line(v, policy):
        if v is None:
            return
        v = np.asarray(v)
        fig.add_trace(go.Scatter(x=legs, y=v, mode="lines+markers", name=C.POLICY_LABELS[policy],
                                 line=dict(color=C.POLICY_COLORS[policy], width=2.5), marker=dict(size=7),
                                 hovertemplate=f"<b>{C.POLICY_LABELS[policy]}</b><br>Etappe %{{x}}<br>%{{y:.1f}} kn<extra></extra>"))
        late = leg_lateness(v, route)
        late_legs = [(i + 1, v[i], late[i]) for i in range(n) if late[i] > 1e-6]
        if late_legs:
            fig.add_trace(go.Scatter(
                x=[x for x, _, _ in late_legs], y=[y for _, y, _ in late_legs], mode="markers+text",
                marker=dict(size=13, color=C.POLICY_COLORS[policy], symbol="x", line=dict(width=2, color="white")),
                text=[f"verspätet ({d:.1f})" for _, _, d in late_legs], textposition="top center",
                textfont=dict(size=10, color=C.POLICY_COLORS[policy]), showlegend=False,
                hovertemplate="verspätet um %{customdata:.1f}<extra></extra>", customdata=[d for _, _, d in late_legs]))

    add_line(v_const, C.POLICY_CONST)
    add_line(v_myo, C.POLICY_MYOPIC)
    add_line(v_exact, C.POLICY_EXACT)

    has_window = route["has_window"]
    for i in range(n):
        if has_window[i]:
            fig.add_vrect(x0=i + 1 - 0.4, x1=i + 1 + 0.4, fillcolor="#f0f2f5", opacity=0.5, layer="below", line_width=0)

    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT, margin=dict(t=30, b=45), legend=LEGEND_BOTTOM,
                      hovermode="closest", xaxis_title="Etappe (grau hinterlegt = mit Ankunftsfenster)", yaxis_title="Geschwindigkeit (kn)")
    fig.update_xaxes(tickmode="array", tickvals=legs)
    fig.update_yaxes(range=[C.V_MIN - 1, C.V_MAX + 1])
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Zwei-Achsen-Vergleich: Kostenaufschlag % (klein) und Verspaetungsanteil % (gross) je Politik
# ---------------------------------------------------------------------------------------------------
def comparison_bars_figure(gap_myo, gap_const, late_myo, late_const):
    import plotly.graph_objects as go

    labels = [C.POLICY_SHORT[C.POLICY_MYOPIC], C.POLICY_SHORT[C.POLICY_CONST]]
    gaps = [gap_myo if gap_myo is not None else 0.0, gap_const if gap_const is not None else 0.0]
    lates = [late_myo if late_myo is not None else 0.0, late_const if late_const is not None else 0.0]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=gaps, name="Kostenaufschlag gegen exakt (%)", marker_color="#8a94a3",
                         yaxis="y1", hovertemplate="%{x}<br>Kostenaufschlag %{y:.2f} %<extra></extra>",
                         text=[f"{g:+.1f} %" for g in gaps], textposition="outside"))
    fig.add_trace(go.Bar(x=labels, y=lates, name="Verspätungsanteil (%)", marker_color="#c0392b",
                         yaxis="y2", hovertemplate="%{x}<br>Verspätungsanteil %{y:.1f} %<extra></extra>",
                         text=[f"{l:.0f} %" for l in lates], textposition="outside"))

    fig.update_layout(
        template="plotly_white", height=C.CHART_HEIGHT, margin=dict(t=30, b=45), legend=LEGEND_BOTTOM,
        barmode="group", xaxis_title="Politik",
        yaxis=dict(title="Kostenaufschlag gegen exakt (%)", rangemode="tozero", side="left"),
        yaxis2=dict(title="Verspätungsanteil (%)", rangemode="tozero", overlaying="y", side="right", range=[0, 100]),
    )
    return _lock_axes(fig)
