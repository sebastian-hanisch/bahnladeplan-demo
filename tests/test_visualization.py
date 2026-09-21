import pytest

import bahn_constants as C
import bahn_evaluation as E
import bahn_rules as R
import bahn_scenario as SC
import bahn_visualization as V
from bahn_evaluation import ListResult
from bahn_scenario import teu

F_, D_, B_, X_ = C.STRAT_FIFO, C.STRAT_FFD, C.STRAT_BLOCKS, C.STRAT_EXACT
INST = SC.make_instance(16, 4, 120, 50, 60, 35)
PLAN = R.blocks(INST)


def rects(fig):
    return [s for s in fig.layout.shapes if s.type == "rect"]


def trace(fig, name):
    return next(t for t in fig.data if t.name == name)


def lr(seed, **kw):
    vals = dict(fifo=40, ffd=42, blocks=46, exact=46)
    vals.update(kw)
    return ListResult(seed, 58, {F_: vals["fifo"], D_: vals["ffd"], B_: vals["blocks"], X_: vals["exact"]}, {k: True for k in C.STRATEGY_KEYS}, True, "optimal", 48)


# ---------------------------------------------------------------------------------------------------
# Zug-Bild
# ---------------------------------------------------------------------------------------------------
def test_train_figure_draws_one_rect_per_place_and_per_loaded_container():
    fig = V.train_figure(INST, PLAN)
    n_loaded = sum(len(w) for w in PLAN)
    assert len(rects(fig)) == INST.n_wagons * C.PLACES + n_loaded
    colors = [s.fillcolor for s in rects(fig)]
    assert colors.count(C.EMPTY_CELL_COLOR) == INST.n_wagons * C.PLACES


def test_container_rect_width_is_one_place_for_20_and_two_places_for_40():
    fig = V.train_figure(INST, PLAN)
    widths = sorted(round(s.x1 - s.x0, 6) for s in rects(fig) if s.fillcolor != C.EMPTY_CELL_COLOR)
    assert widths.count(round(1 - 2 * V.PAD, 6)) == sum(1 for w in PLAN for _, i in w if teu(INST.boxes[i]) == 1)
    assert widths.count(round(2 - 2 * V.PAD, 6)) == sum(1 for w in PLAN for _, i in w if teu(INST.boxes[i]) == 2)


def test_container_color_is_the_destination_color_and_opacity_grows_with_weight():
    fig = V.train_figure(INST, PLAN)
    boxes = [(INST.boxes[i], k) for k, w in enumerate(PLAN) for _, i in w]
    shapes = [s for s in rects(fig) if s.fillcolor != C.EMPTY_CELL_COLOR]
    assert len(shapes) == len(boxes)
    for shape, (b, _) in zip(shapes, boxes):
        assert shape.fillcolor == C.DEST_COLORS[b[2]]
    light = next(s for s, (b, _) in zip(shapes, boxes) if b[1] == min(bb[1] for bb, _ in boxes))
    heavy = next(s for s, (b, _) in zip(shapes, boxes) if b[1] == max(bb[1] for bb, _ in boxes))
    assert light.opacity < heavy.opacity <= 1.0


def test_weight_labels_match_the_containers_and_wagon_labels_show_the_load():
    fig = V.train_figure(INST, PLAN)
    weights = [str(INST.boxes[i][1]) for w in PLAN for _, i in w]
    assert list(trace(fig, "Gewichte").text) == weights
    loads = [f"{sum(INST.boxes[i][1] for _, i in w)} t" if w else "leer" for w in PLAN]
    assert list(trace(fig, "Wagen").text) == loads


def test_hover_covers_the_whole_rectangle_and_names_destination_length_weight_and_place():
    fig = V.train_figure(INST, PLAN)
    hover = trace(fig, "Container")
    n_loaded = sum(len(w) for w in PLAN)
    assert len(hover.x) == 9 * n_loaded and hover.marker.opacity == 0
    first = next((k, p, i) for k, w in enumerate(PLAN) for p, i in w)
    k, p, i = first
    text = hover.text[0]
    assert f"Ziel {INST.boxes[i][2] + 1}" in text and f"{INST.boxes[i][0]} Fuß" in text and f"{INST.boxes[i][1]} t" in text and f"Wagen {k + 1}" in text
    forty = next((k, p, i) for k, w in enumerate(PLAN) for p, i in w if INST.boxes[i][0] == 40)
    assert any(f"Platz {forty[1] + 1}-{forty[1] + 2}" in t for t in hover.text)


def test_legend_lists_only_present_destinations_and_can_be_switched_off():
    on = V.train_figure(INST, PLAN, legend=True)
    names = [t.name for t in on.data if t.name and t.name.startswith("Ziel")]
    present = sorted({INST.boxes[i][2] for w in PLAN for _, i in w})
    assert names == [f"Ziel {d + 1}" for d in present] and on.layout.showlegend
    assert not V.train_figure(INST, PLAN, legend=False).layout.showlegend


def test_axes_are_fixed_and_the_layout_scales_with_the_number_of_rows():
    fig = V.train_figure(INST, PLAN)
    assert fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange
    small = SC.make_instance(8, 2, 120, 50, 60, 1)
    big = SC.make_instance(30, 2, 120, 50, 60, 1)
    assert V.train_figure(big, R.blocks(big)).layout.height > V.train_figure(small, R.blocks(small)).layout.height


def test_wagon_origin_wraps_into_rows_of_eight_and_never_overlaps():
    origins = [V.wagon_origin(k) for k in range(30)]
    assert len(set(origins)) == 30
    assert V.wagon_origin(0) == (0, 0) and V.wagon_origin(7)[1] == 0 and V.wagon_origin(8) == (0, -V.ROW_HEIGHT)
    assert V.wagon_origin(1)[0] - V.wagon_origin(0)[0] == C.PLACES + V.WAGON_GAP


def test_empty_plan_draws_only_empty_places():
    plan = tuple(() for _ in range(INST.n_wagons))
    fig = V.train_figure(INST, plan)
    assert len(rects(fig)) == INST.n_wagons * C.PLACES and list(trace(fig, "Wagen").text) == ["leer"] * INST.n_wagons


def test_dest_color_wraps_for_more_destinations_than_colors():
    assert V.dest_color(0) == C.DEST_COLORS[0] and V.dest_color(len(C.DEST_COLORS)) == C.DEST_COLORS[0]
    assert len(C.DEST_COLORS) >= C.N_DESTS_RANGE[1] and len(set(C.DEST_COLORS)) == len(C.DEST_COLORS) and len(C.DEST_COLOR_NAMES) == len(C.DEST_COLORS)


# ---------------------------------------------------------------------------------------------------
# Kurve
# ---------------------------------------------------------------------------------------------------
def make_curve():
    pts = (1, 4, 8)
    return E.Curve(pts, {1: (lr(0, exact=48), lr(1, exact=48)), 4: (lr(0, exact=47), lr(1, exact=47)), 8: (lr(0, exact=45), lr(1, exact=46))}, 2)


def test_curve_figure_has_a_line_per_method_and_the_mixed_bound():
    fig = V.curve_figure(make_curve(), dests_current=4, capacity=48)
    assert [t.name for t in fig.data] == [C.STRATEGY_LABELS[k] for k in C.STRATEGY_KEYS] + ["ohne Zielreinheit (Schranke)"]
    assert list(trace(fig, C.STRATEGY_LABELS[X_]).x) == [1, 4, 8] and list(trace(fig, C.STRATEGY_LABELS[X_]).y) == [48.0, 47.0, 45.5]
    assert trace(fig, "ohne Zielreinheit (Schranke)").line.dash == "dash"
    assert fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange


def test_curve_figure_exact_marker_is_open_where_not_all_lists_are_proven():
    cv = make_curve()
    lists = dict(cv.lists)
    lists[8] = (ListResult(0, 58, lr(0).loaded, lr(0).valid, False, "feasible", 48), lr(1))
    fig = V.curve_figure(E.Curve(cv.points, lists, 2), None)
    assert list(trace(fig, C.STRATEGY_LABELS[X_]).marker.symbol) == ["circle", "circle", "circle-open"]
    assert trace(fig, C.STRATEGY_LABELS[F_]).marker.symbol == ("circle", "circle", "circle")


def test_curve_figure_marks_the_current_number_of_destinations_only_when_given():
    assert len(V.curve_figure(make_curve(), 4).layout.shapes) == 1 and len(V.curve_figure(make_curve(), None).layout.shapes) == 0


def test_curve_figure_skips_a_method_without_any_valid_plan():
    cv = make_curve()
    bad = {p: tuple(ListResult(r.seed, r.offered, r.loaded, dict(r.valid, **{D_: False}), r.proven, r.exact_status, r.mixed_upper) for r in rs) for p, rs in cv.lists.items()}
    assert C.STRATEGY_LABELS[D_] not in [t.name for t in V.curve_figure(E.Curve(cv.points, bad, 2)).data]


# ---------------------------------------------------------------------------------------------------
# Verteilung, Gewinn, Vergleich
# ---------------------------------------------------------------------------------------------------
def test_distribution_figure_stacks_three_shares_per_method():
    rs = [lr(0), lr(1, blocks=40), lr(2, blocks=38), lr(3)]
    dists = [E.distribution(rs, k, F_) for k in (D_, B_, X_)]
    fig = V.distribution_figure(dists)
    assert [t.name for t in fig.data] == ["lädt mehr als die Reihenfolge", "gleich viel", "lädt weniger als die Reihenfolge"]
    assert list(fig.data[0].y) == ["Größe zuerst", "Wagenblöcke", "Exakt"]
    for i in range(3):
        assert abs(sum(t.x[i] for t in fig.data) - 100) < 1e-9
    assert fig.layout.barmode == "stack" and fig.layout.xaxis.fixedrange


def test_gain_figure_shows_median_and_mean():
    rs = [lr(0, blocks=46), lr(1, blocks=40), lr(2, blocks=52)]
    dists = [E.distribution(rs, B_, F_)]
    fig = V.gain_figure(dists)
    assert [t.name for t in fig.data] == ["Median (typische Instanz)", "Mittelwert"] and fig.data[0].y[0] == 6.0 and fig.data[1].y[0] == pytest.approx(6.0)


def test_comparison_figure_has_a_bar_per_method_the_capacity_line_and_optional_mixed_line():
    outs = E.run_methods(INST, 2)
    fig = V.comparison_figure(INST, outs, mixed_upper=48)
    assert [t.y[0] for t in fig.data] == [o.loaded for o in outs]
    lines = [s for s in fig.layout.shapes if s.type == "line"]
    assert sorted(round(s.y0) for s in lines) == [48, 48] and len(fig.layout.annotations) == 2
    assert len([s for s in V.comparison_figure(INST, outs).layout.shapes if s.type == "line"]) == 1


def test_comparison_figure_hatches_a_plan_that_violates_a_condition():
    outs = list(E.run_methods(INST, 2))
    bad_eval = R.Evaluation(outs[0].loaded, 10, 70, ("Last",))
    outs[0] = E.Outcome(outs[0].key, outs[0].label, outs[0].plan, bad_eval)
    fig = V.comparison_figure(INST, outs)
    assert fig.data[0].marker.pattern.shape == "/" and fig.data[1].marker.pattern.shape == ""
    assert any("Schraffiert" in a.text for a in fig.layout.annotations)
    assert "verletzt: Last" in fig.data[0].hovertemplate


def test_comparison_figure_axis_leaves_room_above_the_capacity_line():
    fig = V.comparison_figure(INST, E.run_methods(INST, 2))
    assert tuple(fig.layout.yaxis.range) == (0, 48 * 1.12)


def test_curve_axis_starts_two_below_the_lowest_value_and_ends_one_above_the_capacity():
    fig = V.curve_figure(make_curve(), None, capacity=48)
    assert tuple(fig.layout.yaxis.range) == (38, 49)                                          # tiefster Wert 40 (Reihenfolge) minus 2; Kapazität 48 plus 1
    low = E.Curve((1, 2), {p: tuple(lr(i, fifo=5, ffd=5, blocks=5, exact=5, mixed=6) for i in range(2)) for p in (1, 2)}, 2)
    assert tuple(V.curve_figure(low, None).layout.yaxis.range) == (3, 49)                     # Schranke ohne Reinheit 48 (Hilfsfunktion lr), tiefster Wert 5
    tiny = E.Curve((1, 2), {p: tuple(lr(i, fifo=1, ffd=1, blocks=1, exact=1, mixed=1) for i in range(2)) for p in (1, 2)}, 2)
    assert V.curve_figure(tiny, None).layout.yaxis.range[0] == 0                              # nie unter 0
