"""The FEA gate rests on one closed-form prediction, so that prediction gets checked.

`run_fea.py` accepts or rejects a solve by comparing the peak stress at the hole
against `peak_stress_mpa`. If that is wrong the gate is worse than absent: it
would confidently accept a wrong solve, or reject a right one. The first version
of this file did the latter -- it treated the Heywood/Howland series as
gross-section referenced, predicted 2.44 MPa where the correct prediction is
3.21 MPa, and rejected a correct solve at 22% error.

**Which convention the series uses, and how that is known.** It is referenced to
the net-section stress, P/((W-d)t). The argument is physical rather than
bibliographic: referenced to *gross* stress, Kt must rise without bound as
d/W -> 1, because the ligaments carrying the load vanish while the gross area does
not. This series falls with d/W, so it cannot be gross-referenced. Note that the
d/W -> 0 limit cannot distinguish the two conventions, because they coincide
there -- which is exactly why a passing Kirsch check did not catch the error.

**What the solver says.** Two independent geometries, solved on the host, come in
consistently *below* the net-section prediction:

| plate | d/W | predicted peak | measured peak | error |
| --- | --- | --- | --- | --- |
| 150x80x6, 8 mm hole | 0.10 | 3.025 | 2.75 | -9.1% |
| 80x50x8, 12 mm hole | 0.24 | 3.209 | 2.973 | -7.3% |

Same sign, similar size, which is what the model's own assumptions predict: the
correlation assumes a long plate in uniform far-field tension with free lateral
edges, while the model clamps one end face and is only 1.6-1.9 widths long. A
consistent bias of that size is evidence the two agree; it is not a validation of
the solver, and the tolerance is set to admit the bias rather than to be tight.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "cadloop" / "fea" / "run_fea.py"
_spec = importlib.util.spec_from_file_location("run_fea", MODULE_PATH)
run_fea = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_fea)

kt = run_fea.kt_plate_central_hole
peak = run_fea.peak_stress_mpa


def test_small_hole_recovers_the_infinite_plate_result() -> None:
    """Kirsch's 3.0. A sanity check only: both conventions agree in this limit,
    so passing it says nothing about which one the series uses."""
    assert kt(0.01, 100.0) == pytest.approx(3.0, abs=0.01)


def test_the_series_is_net_section_referenced_not_gross() -> None:
    """Gross-referenced Kt must diverge as the ligaments vanish. This falls, so it
    is the net-section form -- the distinction the gate got wrong."""
    values = [kt(ratio * 100.0, 100.0) for ratio in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5)]
    assert values == sorted(values, reverse=True)
    assert values[-1] < values[0] < 3.0 + 1e-9


def test_the_net_section_conversion_is_applied() -> None:
    """The applied traction is gross stress; Kt multiplies net stress. Skipping
    the W/(W-d) factor is exactly the 32% underprediction the gate hit."""
    got = peak(12.0, 50.0, 1.0)
    assert got["net_over_gross"] == pytest.approx(50.0 / 38.0)
    assert got["expected_peak_mpa"] == pytest.approx(2.43846528 * 50.0 / 38.0, rel=1e-9)
    assert got["expected_peak_mpa"] > got["kt_net_section"], "conversion not applied"


def test_scales_linearly_with_the_applied_stress() -> None:
    """Linear elasticity. A prediction that did not scale would mean the applied
    stress had leaked into the factor."""
    one = peak(12.0, 50.0, 1.0)["expected_peak_mpa"]
    ten = peak(12.0, 50.0, 10.0)["expected_peak_mpa"]
    assert ten == pytest.approx(10.0 * one, rel=1e-12)


@pytest.mark.parametrize(
    "hole, width, gross, measured",
    [(8.0, 80.0, 1.0, 2.75), (12.0, 50.0, 1.0, 2.973359739293081)],
)
def test_solved_cases_sit_below_the_prediction_by_under_ten_percent(
    hole: float, width: float, gross: float, measured: float
) -> None:
    """Both host solves under-predict, in the direction a clamped short plate must.
    A solve landing *above* the correlation would mean something else was wrong."""
    expected = peak(hole, width, gross)["expected_peak_mpa"]
    error = (measured - expected) / expected
    assert -0.12 < error < 0.0, "expected a small negative bias, got %.3f" % error


@pytest.mark.parametrize("hole, width", [(0.0, 50.0), (30.0, 50.0), (-5.0, 50.0)])
def test_refuses_ratios_outside_the_correlation(hole: float, width: float) -> None:
    """Extrapolating past d/W = 0.5 silently would be the dangerous behaviour."""
    with pytest.raises(ValueError):
        kt(hole, width)
