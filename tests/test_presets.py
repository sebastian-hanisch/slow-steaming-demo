"""Regler-Spezifikation, Permalink, Presets (sls_presets) - reine Logik ohne AppTest (Session-State-
abhaengige Funktionen wie apply_preset werden in tests/test_app.py per AppTest geprueft)."""
import sls_constants as C
from sls_presets import bounds, parse_setting, SETTING_SPECS


def test_bounds_reads_spec_range():
    assert bounds("n_legs_slider") == C.N_LEGS_RANGE
    assert bounds("window_share_slider") == C.WINDOW_SHARE_RANGE
    assert bounds("seed_input") == C.SEED_RANGE


# ---------------------------------------------------------------------------------------------------
# Permalink-Parsing: numerische Regler
# ---------------------------------------------------------------------------------------------------
def test_parse_setting_clamps_to_spec_range():
    spec = SETTING_SPECS["n_legs_slider"]
    assert parse_setting(spec, "99") == C.N_LEGS_RANGE[1]
    assert parse_setting(spec, "0") == C.N_LEGS_RANGE[0]


def test_parse_setting_ignores_garbage():
    spec = SETTING_SPECS["seed_input"]
    assert parse_setting(spec, "not-a-number") is None


def test_parse_setting_rejects_non_finite_floats():
    spec = SETTING_SPECS["seed_input"]
    assert parse_setting(spec, "nan") is None


def test_parse_setting_snaps_window_share_to_its_step():
    spec = SETTING_SPECS["window_share_slider"]
    assert parse_setting(spec, "53") == 50    # rundet auf den naechsten 10er-Schritt
    assert parse_setting(spec, "57") == 60


# ---------------------------------------------------------------------------------------------------
# Permalink-Parsing: Enum-Regler (Fenster-Enge, Bunker-/Charter-Verhaeltnis)
# ---------------------------------------------------------------------------------------------------
def test_parse_setting_decodes_the_short_tightness_key():
    spec = SETTING_SPECS["tightness_select"]
    assert parse_setting(spec, "eng") == "Eng"
    assert parse_setting(spec, "locker") == "Locker"


def test_parse_setting_falls_back_to_default_for_unknown_tightness_key():
    spec = SETTING_SPECS["tightness_select"]
    assert parse_setting(spec, "garbage") == C.TIGHTNESS_DEFAULT


def test_parse_setting_decodes_the_short_rate_ratio_key():
    spec = SETTING_SPECS["rate_ratio_select"]
    assert parse_setting(spec, "v23") == "Sehr hoch (v*=23 kn)"


def test_parse_setting_falls_back_to_default_for_unknown_rate_ratio_key():
    spec = SETTING_SPECS["rate_ratio_select"]
    assert parse_setting(spec, "") == C.RATE_RATIO_DEFAULT


def test_setting_specs_encoder_roundtrips_every_tightness_level():
    spec = SETTING_SPECS["tightness_select"]
    for label in C.TIGHTNESS_LEVELS:
        assert parse_setting(spec, spec.encoder(label)) == label


def test_setting_specs_encoder_roundtrips_every_rate_ratio_level():
    spec = SETTING_SPECS["rate_ratio_select"]
    for label in C.RATE_RATIO_LEVELS:
        assert parse_setting(spec, spec.encoder(label)) == label


# ---------------------------------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------------------------------
def test_every_preset_has_all_five_fields_within_spec_bounds():
    for name, preset in C.PRESETS.items():
        assert set(preset) == {"n_legs", "window_share", "tightness", "rate_ratio", "seed"}
        assert C.N_LEGS_RANGE[0] <= preset["n_legs"] <= C.N_LEGS_RANGE[1]
        assert C.WINDOW_SHARE_RANGE[0] <= preset["window_share"] <= C.WINDOW_SHARE_RANGE[1]
        assert preset["tightness"] in C.TIGHTNESS_LEVELS
        assert preset["rate_ratio"] in C.RATE_RATIO_LEVELS
        assert C.SEED_RANGE[0] <= preset["seed"] <= C.SEED_RANGE[1]


def test_preset_seeds_lie_outside_the_population():
    assert all(preset["seed"] >= C.POPULATION_INSTANCES for preset in C.PRESETS.values())


def test_preset_names_are_short_for_the_button_row():
    assert all(len(name) <= 22 for name in C.PRESETS)
    assert len(C.PRESETS) == 5
