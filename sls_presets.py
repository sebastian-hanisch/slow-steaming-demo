"""Regler-Spezifikation, Permalink, Presets und Seed-Knopf (Standardmuster aus dem OR-Demo-Portfolio,
siehe mhs_presets.py in mehrhafenstau-demo). Zwei der fuenf Regler sind Stufen-Enums (Fenster-Enge,
Bunker-/Charter-Verhaeltnis) statt Zahlenbereiche - eigene, kurze URL-Schluessel statt der Klartext-Labels
(siehe TIGHTNESS_URL_KEYS/RATE_RATIO_URL_KEYS in sls_constants.py)."""
import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import sls_constants as C


def _int_text(value):
    return str(int(value))


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None
    step: Optional[int] = None
    encoder: Callable = _int_text


def _enum_caster(url_keys, default_label):
    reverse = {v: k for k, v in url_keys.items()}

    def cast(raw):
        return reverse.get(str(raw), default_label)
    return cast


def _enum_encoder(url_keys):
    def enc(label):
        return url_keys.get(label, next(iter(url_keys.values())))
    return enc


SETTING_SPECS = {
    "n_legs_slider": SettingSpec("legs", int, C.N_LEGS_DEFAULT, *C.N_LEGS_RANGE, 1),
    "window_share_slider": SettingSpec("ws", int, C.WINDOW_SHARE_DEFAULT, *C.WINDOW_SHARE_RANGE, C.WINDOW_SHARE_STEP),
    "tightness_select": SettingSpec("tight", _enum_caster(C.TIGHTNESS_URL_KEYS, C.TIGHTNESS_DEFAULT), C.TIGHTNESS_DEFAULT,
                                     encoder=_enum_encoder(C.TIGHTNESS_URL_KEYS)),
    "rate_ratio_select": SettingSpec("rate", _enum_caster(C.RATE_RATIO_URL_KEYS, C.RATE_RATIO_DEFAULT), C.RATE_RATIO_DEFAULT,
                                      encoder=_enum_encoder(C.RATE_RATIO_URL_KEYS)),
    "seed_input": SettingSpec("seed", int, C.SEED_DEFAULT, *C.SEED_RANGE, 1),
}

PRESET_STATE_KEYS = {
    "n_legs": "n_legs_slider", "window_share": "window_share_slider", "tightness": "tightness_select",
    "rate_ratio": "rate_ratio_select", "seed": "seed_input",
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def parse_setting(spec, raw):
    """Wert aus der Adresszeile: umwandeln, ggf. auf den Bereich begrenzen/runden. None, wenn er sich
    nicht auswerten laesst (nur fuer numerische Regler - Enum-Regler fallen bei Muell auf ihren Default
    zurueck, siehe _enum_caster)."""
    try:
        value = spec.caster(raw)
    except (ValueError, TypeError):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    if spec.step and spec.step > 1 and spec.lo is not None:
        value = spec.lo + round((value - spec.lo) / spec.step) * spec.step
        value = min(spec.hi, value)
    return value


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            value = parse_setting(spec, qp[spec.url_param])
            if value is not None:
                st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """values: dict state_key -> aktueller Wert (aus den Widgets)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = SETTING_SPECS[state_key].encoder(value)
    except Exception:
        pass


def apply_preset(name):
    for field, state_key in PRESET_STATE_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][field]


def randomize_seed():
    """Wuerfelt einen neuen Seed fuer die Route (Distanzen, welche Etappen ein Fenster bekommen)."""
    st.session_state["seed_input"] = random.randint(*C.SEED_RANGE)
