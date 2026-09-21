"""Regler-Spezifikation, Permalink, Presets und Seed-Knopf (Standardmuster aus dem OR-Demo-Portfolio, siehe stau_presets.py)."""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import bahn_constants as C
from bahn_scenario import make_instance


def _view(raw):
    if raw not in C.RIGHT_VIEW_KEYS:
        raise ValueError(raw)
    return raw


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


SETTING_SPECS = {
    "n_wagons_slider": SettingSpec("nw", int, C.N_WAGONS_DEFAULT, *C.N_WAGONS_RANGE, 1),
    "n_dest_slider": SettingSpec("nd", int, C.N_DESTS_DEFAULT, *C.N_DESTS_RANGE, 1),
    "offer_slider": SettingSpec("of", int, C.OFFER_PCT_DEFAULT, *C.OFFER_PCT_RANGE, C.OFFER_PCT_STEP),
    "share40_slider": SettingSpec("s4", int, C.SHARE40_PCT_DEFAULT, *C.SHARE40_PCT_RANGE, C.SHARE40_PCT_STEP),
    "payload_slider": SettingSpec("pl", int, C.PAYLOAD_DEFAULT, *C.PAYLOAD_RANGE, C.PAYLOAD_STEP),
    "seed_input": SettingSpec("seed", int, C.SEED_DEFAULT, *C.SEED_RANGE, 1),
    "view_radio": SettingSpec("vw", _view, C.VIEW_DEFAULT, encoder=str),
}

PRESET_STATE_KEYS = {
    "n_wagons": "n_wagons_slider", "n_dests": "n_dest_slider", "offer_pct": "offer_slider", "share40_pct": "share40_slider", "payload": "payload_slider", "seed": "seed_input",
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def parse_setting(spec, raw):
    """Wert aus der Adresszeile: umwandeln, auf den Bereich begrenzen, auf die Schrittweite runden. None, wenn er sich nicht auswerten lässt."""
    try:
        value = spec.caster(raw)
    except (ValueError, TypeError):
        return None
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
    """values: dict state_key -> aktueller Wert (aus den Widgets, damit dieselbe Änderung, die gerade gerendert wurde, sofort in der Adresszeile landet)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = SETTING_SPECS[state_key].encoder(value)
    except Exception:
        pass


def apply_preset(name):
    for field, state_key in PRESET_STATE_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][field]


def scenario_instance(n_wagons, n_dests, offer_pct, share40_pct, payload, seed):
    return make_instance(int(n_wagons), int(n_dests), int(offer_pct), int(share40_pct), int(payload), int(seed))


def randomize_seed():
    """Würfelt einen neuen Seed für den Tag (jede Instanz ist spielbar)."""
    st.session_state["seed_input"] = random.randint(*C.SEED_RANGE)
