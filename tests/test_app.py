"""AppTest: Skelett und Footer, jedes Preset (inkl. "Nicht machbar" und seiner eigenen Statusmeldung),
Permalink, alle Regler an Min/Max, Kennzahlen im 2 x 2-Raster, die bedingte Meldung in beiden Zustaenden,
Urteil, Vergleichstabelle, PDF, Ladeindikator (statischer Check, siehe unten), Texte."""
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

import sls_constants as C
import sls_evaluation as E
import sls_stories as ST
from sls_presets import SETTING_SPECS

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")
FOOTER = (
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Seefracht optimieren](https://sebastianhanisch.net/seefracht-optimierung.html)."
)


@pytest.fixture(autouse=True)
def clean_cache():
    """st.cache_data ist prozessweit: Tests, die Einstellungen aendern, duerfen keine
    zwischengespeicherten Ergebnisse anderer Tests sehen."""
    import streamlit as st
    st.cache_data.clear()
    yield


def fresh(**query):
    at = AppTest.from_file(APP, default_timeout=180)
    for k, v in query.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def set_and_run(at, **values):
    for key, value in values.items():
        widget = at.number_input if key.endswith("_input") else (at.select_slider if key.endswith("_select") else at.slider)
        widget(key=key).set_value(value).run()
    assert not at.exception, at.exception
    return at


def main_metrics(at):
    return [(m.label, m.value) for m in at.metric[:4]]


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception, at.exception
    return at


def message(at, needle):
    for group in (at.success, at.warning, at.info, at.error):
        for x in group:
            if needle in x.value:
                return x.value
    return None


# ---------------------------------------------------------------------------------------------------
# Skelett
# ---------------------------------------------------------------------------------------------------
def test_skeleton_and_footer():
    at = fresh()
    assert [h.value for h in at.sidebar.header] == ["⚙️ Einstellungen"]        # genau EIN Header
    assert len(at.title) == 1 and "Geschwindigkeitsoptimierung" in at.title[0].value
    assert any(v.value.startswith("## 🎯") for v in at.markdown)
    assert any(v.value.startswith("### 📐") for v in at.markdown)
    assert [e.label for e in at.expander] == ["🔧 Wie wir das erreichen – Politiken im Vergleich", "Wie funktioniert diese Demo?", "📐 Mathematische Formulierung"]
    assert any(c.value == FOOTER for c in at.caption)
    presets = [b.label for b in at.button if b.label in C.PRESETS]
    assert presets == list(C.PRESETS) and len(presets) == 5 and all(len(n) <= 22 for n in presets)
    assert [s.label for s in at.sidebar.slider] == ["Etappen", "Anteil mit Fenster"]
    assert [s.label for s in at.sidebar.select_slider] == ["Fenster-Enge", "Bunker-/Charter-Verhältnis"]
    assert [n.label for n in at.sidebar.number_input] == ["Seed"] and any(b.label == "🎲 Neue Route" for b in at.sidebar.button)


def test_main_metrics_are_2x2_with_the_right_labels():
    at = fresh()
    labels = [m[0] for m in main_metrics(at)]
    assert labels == ["Fenster eingehalten (exakt)", "Kostenaufschlag gegen konstant", "Gesamtkosten (exakt)", "Status"]


def test_charts_are_present_with_unique_keys():
    at = fresh()
    charts = at.get("plotly_chart")
    keys = [c.key for c in charts]
    assert len(set(keys)) == len(keys) and all(keys)
    assert len(keys) == 6   # Hauptprofil, Vergleichsbalken, 3 Politik-Tabs, Vergleichstab


def test_loading_spinner_is_wired_for_the_solve_exact_call():
    """AppTest faengt keine transienten Spinner ab - der Ladeindikator wird deshalb statisch geprueft
    (siehe DEMO-PLAYBOOK/Plan Abschnitt 2/15: Rechenzeit bei knappen/infeasiblen Instanzen ist spuerbar
    hoeher, braucht einen sichtbaren Kurz-Ladeindikator statt Live-ohne-Anzeige)."""
    src = pathlib.Path(APP).read_text(encoding="utf-8")
    assert "show_spinner=C.SOLVE_SPINNER_TEXT" in src
    assert "_compute_shown" in src


# ---------------------------------------------------------------------------------------------------
# Presets, Permalink
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_loads_within_widget_bounds_and_shows_its_story(name):
    at = fresh()
    click(at, name)
    preset = C.PRESETS[name]
    assert at.slider(key="n_legs_slider").value == preset["n_legs"]
    assert at.slider(key="window_share_slider").value == preset["window_share"]
    assert at.select_slider(key="tightness_select").value == preset["tightness"]
    assert at.select_slider(key="rate_ratio_select").value == preset["rate_ratio"]
    assert at.number_input(key="seed_input").value == preset["seed"]

    p = E.params_from_controls(preset["n_legs"], preset["window_share"], preset["tightness"], preset["rate_ratio"])
    shown = E.route_result(p, preset["seed"])
    for ok, text in ST.shown_criteria(name, shown):
        assert ok, f"{name}: {text}"

    labels = [m[0] for m in main_metrics(at)]
    values = [m[1] for m in main_metrics(at)]
    assert labels[2] == "Gesamtkosten (exakt)"
    if shown.cost_exact is None:
        assert values[2] == "nicht machbar" and values[3] == "⛔ nicht machbar"
    else:
        assert values[3] == "✅ machbar"


def test_nicht_machbar_preset_shows_its_own_distinct_status_message():
    """Eine echte, neue UI-Situation fuer dieses Portfolio: infeasibel-mit-klarer-Meldung statt eines
    numerischen Ergebnisses."""
    at = fresh()
    click(at, "Nicht machbar")
    main_errors = [e.value for e in at.error if "nicht einzuhalten" in e.value]
    assert len(main_errors) == 1 and "verkürzen" in main_errors[0]
    labels = [m[0] for m in main_metrics(at)]
    values = [m[1] for m in main_metrics(at)]
    assert values[main_metrics(at).__len__() - 1] == "⛔ nicht machbar"
    # Bei "nicht machbar" fehlt der Exakt-Tab-Chart (siehe render_policy_panel: fruehe Rueckkehr nach der Warnung)
    charts = at.get("plotly_chart")
    assert len(charts) == 5
    assert "tab_exact_profile_chart" not in [c.key for c in charts]


def test_permalink_is_clamped_and_ignores_garbage():
    at = fresh(legs="99", ws="abc", seed="junk")
    assert at.slider(key="n_legs_slider").value == C.N_LEGS_RANGE[1]              # geklemmt
    assert at.slider(key="window_share_slider").value == C.WINDOW_SHARE_DEFAULT    # Muell ignoriert
    assert at.number_input(key="seed_input").value == C.SEED_DEFAULT               # Muell ignoriert


def test_permalink_decodes_enum_controls():
    at = fresh(tight="eng", rate="v23")
    assert at.select_slider(key="tightness_select").value == "Eng"
    assert at.select_slider(key="rate_ratio_select").value == "Sehr hoch (v*=23 kn)"


def test_permalink_falls_back_to_default_for_an_unknown_enum_value():
    at = fresh(tight="does-not-exist")
    assert at.select_slider(key="tightness_select").value == C.TIGHTNESS_DEFAULT


def test_permalink_roundtrip_reflects_settings():
    at = fresh(legs="8", ws="30", seed="11")
    assert at.session_state["n_legs_slider"] == 8 and at.session_state["window_share_slider"] == 30
    assert at.session_state["seed_input"] == 11
    for key, spec in SETTING_SPECS.items():
        got = at.query_params[spec.url_param]
        got = got[0] if isinstance(got, list) else got
        assert got == spec.encoder(at.session_state[key]), key


def test_new_route_button_changes_only_the_seed():
    at = fresh()
    before = {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"}
    click(at, "🎲 Neue Route")
    assert {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"} == before
    assert C.SEED_RANGE[0] <= at.session_state["seed_input"] <= C.SEED_RANGE[1]


# ---------------------------------------------------------------------------------------------------
# Regler an den Grenzen
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key,value", [("n_legs_slider", 3), ("n_legs_slider", 10), ("window_share_slider", 0), ("window_share_slider", 100)])
def test_every_slider_works_at_its_minimum_and_maximum(key, value):
    at = set_and_run(fresh(), **{key: value})
    assert at.session_state[key] == value and len(at.metric) >= 4


@pytest.mark.parametrize("key,value", [("tightness_select", "Locker"), ("tightness_select", "Eng"),
                                       ("rate_ratio_select", "Sehr niedrig (v*=12 kn)"), ("rate_ratio_select", "Sehr hoch (v*=23 kn)")])
def test_every_select_slider_works_at_its_extremes(key, value):
    at = set_and_run(fresh(), **{key: value})
    assert at.session_state[key] == value and len(at.metric) >= 4


def test_seed_input_works_at_its_minimum_and_maximum():
    at = set_and_run(fresh(), seed_input=C.SEED_RANGE[0])
    assert at.session_state["seed_input"] == C.SEED_RANGE[0]
    at = set_and_run(fresh(), seed_input=C.SEED_RANGE[1])
    assert at.session_state["seed_input"] == C.SEED_RANGE[1]


def test_extreme_combination_runs_without_exception():
    at = fresh(legs="3", ws="0", seed="0")
    assert not at.exception
    at = fresh(legs="10", ws="100", tight="eng", rate="v23", seed="9999")
    assert not at.exception


# ---------------------------------------------------------------------------------------------------
# Bedingte Meldung
# ---------------------------------------------------------------------------------------------------
def test_message_feasible_when_windows_are_reachable():
    at = fresh()
    click(at, "Locker")
    msg = message(at, "Machbar")
    assert msg is not None


def test_message_infeasible_when_windows_are_not_reachable():
    at = fresh()
    click(at, "Nicht machbar")
    msg = message(at, "nicht einzuhalten")
    assert msg is not None


# ---------------------------------------------------------------------------------------------------
# Kernabschnitt: Urteil
# ---------------------------------------------------------------------------------------------------
def test_verdict_sentence_present_with_the_right_label():
    at = fresh()
    texts = [x.value for group in (at.success, at.warning, at.info) for x in group if "gegen myopisch" in x.value]
    assert len(texts) >= 1
    assert any("Exakt gegen myopisch" in t for t in texts)


def _fake_verdict(monkeypatch, kind, diff, se=1.0, n=20):
    import sls_evaluation as E_mod
    monkeypatch.setattr(E_mod, "verdict", lambda res: E_mod.Verdict(kind, diff, se, n))


def test_verdict_sentence_better_and_worse(monkeypatch):
    _fake_verdict(monkeypatch, "better", -30.0)
    at = fresh()
    assert any("weniger Verspätungen" in x.value for x in at.success)
    _fake_verdict(monkeypatch, "worse", 30.0)
    at = fresh()
    assert any("mehr Verspätungen" in x.value for x in at.warning)


def test_verdict_sentence_unclear(monkeypatch):
    _fake_verdict(monkeypatch, "unclear", 0.2)
    at = fresh()
    assert any("Kein klarer Unterschied" in x.value for x in at.info)


def test_verdict_sentence_no_comparable_routes(monkeypatch):
    _fake_verdict(monkeypatch, "unclear", 0.0, se=0.0, n=0)
    at = fresh()
    assert any("Kein Vergleich möglich" in x.value for x in at.info)


# ---------------------------------------------------------------------------------------------------
# Politik-Tabs, Vergleichstabelle, PDF, Texte
# ---------------------------------------------------------------------------------------------------
def test_comparison_table_has_one_row_per_policy():
    at = fresh()
    dfs = at.dataframe
    comparison_df = dfs[-1].value
    assert list(comparison_df["Politik"]) == [C.POLICY_LABELS[C.POLICY_EXACT], C.POLICY_LABELS[C.POLICY_MYOPIC], C.POLICY_LABELS[C.POLICY_CONST]]
    assert "Verspätungsanteil (Stichprobe)" in comparison_df.columns


def test_each_policy_tab_shows_a_speed_profile_when_feasible():
    at = fresh()
    charts = at.get("plotly_chart")
    keys = {c.key for c in charts}
    assert {"tab_const_profile_chart", "tab_myo_profile_chart", "tab_exact_profile_chart"} <= keys


def test_pdf_download_button_is_offered():
    at = fresh()
    buttons = at.get("download_button")
    assert len(buttons) == 1 and buttons[0].proto.label == "📄 Ergebnis als PDF herunterladen"


def test_pdf_download_button_is_offered_for_the_infeasible_preset_too():
    at = fresh()
    click(at, "Nicht machbar")
    buttons = at.get("download_button")
    assert len(buttons) == 1


def test_texts_state_the_model_and_the_limits():
    at = fresh()
    text = "\n".join(m.value for m in at.expander[1].markdown)
    for needle in ("wirtschaftliche", "myopisch", "Ankunftsfenster", "Wetter"):
        assert needle in text, needle
    math_text = "\n".join(m.value for m in at.expander[2].markdown)
    for needle in ("v^\\ast", "trust-constr", "KKT", "Optimalitäts-Regressionstest"):
        assert needle in math_text, needle
