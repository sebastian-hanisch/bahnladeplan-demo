"""Tests der Regler-Spezifikation: Permalink-Auswertung (begrenzen, einrasten, Müll ignorieren), Presets innerhalb der Reglergrenzen, Konsistenz mit den Konstanten."""

import bahn_constants as C
import bahn_presets as P
import bahn_scenario as SC

S = P.SETTING_SPECS


def test_parse_clamps_to_range():
    spec = S["n_wagons_slider"]
    assert P.parse_setting(spec, "99") == C.N_WAGONS_RANGE[1] and P.parse_setting(spec, "-5") == C.N_WAGONS_RANGE[0] and P.parse_setting(spec, "12") == 12
    d = S["n_dest_slider"]
    assert P.parse_setting(d, "0") == 1 and P.parse_setting(d, "11") == 10
    assert P.parse_setting(S["payload_slider"], "100") == 70 and P.parse_setting(S["payload_slider"], "1") == 40


def test_parse_snaps_to_step_from_lower_bound():
    offer, share, payload = S["offer_slider"], S["share40_slider"], S["payload_slider"]
    assert P.parse_setting(offer, "123") == 120 and P.parse_setting(offer, "126") == 130 and P.parse_setting(offer, "80") == 80 and P.parse_setting(offer, "150") == 150
    assert P.parse_setting(share, "44") == 40 and P.parse_setting(share, "46") == 50 and P.parse_setting(share, "99") == 100
    assert P.parse_setting(payload, "42") == 40 and P.parse_setting(payload, "43") == 45 and P.parse_setting(payload, "69") == 70


def test_parse_ignores_garbage():
    for key in ("n_wagons_slider", "seed_input", "offer_slider"):
        assert P.parse_setting(S[key], "abc") is None and P.parse_setting(S[key], None) is None and P.parse_setting(S[key], "") is None
    assert P.parse_setting(S["view_radio"], "junk") is None
    assert P.parse_setting(S["view_radio"], "fifo") is None                   # die Referenz steht immer links, ist keine Wahl rechts
    assert P.parse_setting(S["view_radio"], "exact") == "exact" and P.parse_setting(S["view_radio"], "blocks") == "blocks"


def test_step_grid_starts_at_the_lower_bound_not_at_zero():
    spec = P.SettingSpec("x", int, 1, 1, 21, 5)
    assert [P.parse_setting(spec, str(v)) for v in (1, 3, 4, 7, 9, 14, 19, 21)] == [1, 1, 6, 6, 11, 16, 21, 21]


def test_specs_match_constants_and_defaults_inside_bounds():
    assert S["n_wagons_slider"].default == C.N_WAGONS_DEFAULT and S["seed_input"].default == C.SEED_DEFAULT and S["payload_slider"].default == C.PAYLOAD_DEFAULT
    for key, spec in S.items():
        assert P.bounds(key) == (spec.lo, spec.hi)
        if spec.lo is not None:
            assert spec.lo <= spec.default <= spec.hi
            if spec.step and spec.step > 1:
                assert (spec.default - spec.lo) % spec.step == 0
    assert len({spec.url_param for spec in S.values()}) == len(S)
    assert S["view_radio"].default in C.RIGHT_VIEW_KEYS and C.BASELINE not in C.RIGHT_VIEW_KEYS


def test_every_preset_is_inside_bounds_on_the_step():
    assert list(C.PRESETS) == ["Locker", "Üblich", "Viele Ziele", "Schwer", "Ganz lang"] and all(len(n) <= 16 for n in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == set(P.PRESET_STATE_KEYS)
        for field, state_key in P.PRESET_STATE_KEYS.items():
            spec = S[state_key]
            assert spec.lo <= p[field] <= spec.hi, (name, field)
            if spec.step and spec.step > 1:
                assert (p[field] - spec.lo) % spec.step == 0, (name, field)


def test_encoders_roundtrip_through_parse():
    for key, spec in S.items():
        assert P.parse_setting(spec, spec.encoder(spec.default)) == spec.default
    assert S["seed_input"].encoder(4.0) == "4"


def test_scenario_instance_matches_make_instance_and_casts():
    assert P.scenario_instance(16.0, 4.0, 120.0, 50.0, 60.0, 31.0) == SC.make_instance(16, 4, 120, 50, 60, 31)


def test_every_slider_combination_is_a_valid_instance_range():
    for w in (C.N_WAGONS_RANGE[0], C.N_WAGONS_RANGE[1]):
        for d in range(C.N_DESTS_RANGE[0], C.N_DESTS_RANGE[1] + 1):
            assert len(SC.make_instance(w, d, C.OFFER_PCT_RANGE[0], C.SHARE40_PCT_RANGE[0], C.PAYLOAD_RANGE[0], 0).boxes) >= 1


def test_url_parameter_names_are_fixed():
    assert {spec.url_param for spec in S.values()} == {"nw", "nd", "of", "s4", "pl", "seed", "vw"}
    assert S["payload_slider"].url_param == "pl" and S["n_dest_slider"].hi == C.N_DESTS_RANGE[1] and S["n_wagons_slider"].hi == C.N_WAGONS_RANGE[1]
    assert P.PRESET_STATE_KEYS["share40_pct"] == "share40_slider" and P.PRESET_STATE_KEYS["offer_pct"] == "offer_slider"
