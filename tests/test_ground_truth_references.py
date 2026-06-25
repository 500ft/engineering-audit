"""Independent validation of the analytically/FEA-grade ground-truth references.

These tests are the in-repo "oracle" check behind the `syn-kt-hole-0001` and
`syn-cantilever-0001` benchmark cases. They confirm the cited reference numbers
are reproducible from first principles, and they validate each correlation
against an independent anchor:

- the Peterson/Heywood Kt fit against the Kirsch d/W -> 0 limit (Kt -> 3.0);
- the cantilever tip deflection against a numerical double-integration of the
  beam curvature.

No model output is involved; these are ground-truth controls, not wild captures.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mechaudit.case_loader import load_case_file
from mechaudit.pressure_vessel import audit_case
from mechaudit.stress_concentration import (
    end_loaded_cantilever,
    kt_plate_with_hole_net,
    plate_with_hole,
)


ROOT = Path(__file__).resolve().parents[1]


# --- Stress-concentration (Kt) ground truth ---------------------------------


def test_kt_fit_recovers_kirsch_infinite_plate_limit() -> None:
    # As d/W -> 0, the net-section Peterson/Heywood fit must approach the
    # Kirsch infinite-plate factor of 3.0. The empirical fit recovers this anchor
    # to within ~0.4% (its limit is 3.004, the known small offset of the fit).
    limit = kt_plate_with_hole_net(1e-9)
    assert limit == pytest.approx(3.0, rel=5e-3)
    assert abs(limit - 3.0) < 0.01


def test_plate_with_hole_reference_values() -> None:
    res = plate_with_hole(
        width_mm=80.0,
        hole_diameter_mm=20.0,
        thickness_mm=5.0,
        axial_force_N=18.0e3,
    )
    assert res.d_over_W == pytest.approx(0.25)
    assert res.Kt_net == pytest.approx(2.432375, abs=1e-6)
    assert res.sigma_net_MPa == pytest.approx(60.0)
    assert res.sigma_gross_MPa == pytest.approx(45.0)
    assert res.sigma_max_MPa == pytest.approx(145.9425, abs=1e-4)


def test_plate_with_hole_gross_and_net_are_consistent() -> None:
    # sigma_max computed via the gross-referenced Kt must equal the net route.
    res = plate_with_hole(
        width_mm=80.0,
        hole_diameter_mm=20.0,
        thickness_mm=5.0,
        axial_force_N=18.0e3,
    )
    via_gross = res.Kt_gross * res.sigma_gross_MPa
    assert via_gross == pytest.approx(res.sigma_max_MPa, rel=1e-9)


def test_kt_case_matches_reference_and_is_clean_control() -> None:
    case = load_case_file(ROOT / "benchmark" / "synthetic" / "syn-kt-hole-0001.md")
    ref = plate_with_hole(
        width_mm=80.0, hole_diameter_mm=20.0, thickness_mm=5.0, axial_force_N=18.0e3
    )

    expected = next(
        o for o in case.outputs if o.source == "expected" and o.name == "peak_stress"
    )
    assert expected.value == pytest.approx(ref.sigma_max_MPa, abs=1e-4)

    result = audit_case(case)
    assert result.detected_failure_modes == []
    assert result.passed


# --- Cantilever bending ground truth ----------------------------------------


def test_cantilever_reference_values() -> None:
    res = end_loaded_cantilever(
        load_N=500.0,
        length_mm=300.0,
        width_mm=20.0,
        height_mm=10.0,
        youngs_modulus_MPa=200.0e3,
    )
    assert res.moment_of_inertia_mm4 == pytest.approx(1666.6667, abs=1e-3)
    assert res.fixed_end_moment_Nmm == pytest.approx(150000.0)
    assert res.sigma_max_MPa == pytest.approx(450.0)
    assert res.tip_deflection_mm == pytest.approx(13.5)


def test_cantilever_stress_two_formulas_agree() -> None:
    # sigma_max = M c / I must equal 6 P L / (b h^2).
    P, L, b, h = 500.0, 300.0, 20.0, 10.0
    res = end_loaded_cantilever(
        load_N=P, length_mm=L, width_mm=b, height_mm=h, youngs_modulus_MPa=200.0e3
    )
    closed_form = 6.0 * P * L / (b * h**2)
    assert res.sigma_max_MPa == pytest.approx(closed_form, rel=1e-12)


def test_cantilever_deflection_matches_numerical_double_integration() -> None:
    # Independent oracle: integrate v'' = M(x)/(E I) twice along the beam.
    P, L, b, h, E = 500.0, 300.0, 20.0, 10.0, 200.0e3
    res = end_loaded_cantilever(
        load_N=P, length_mm=L, width_mm=b, height_mm=h, youngs_modulus_MPa=E
    )
    inertia = b * h**3 / 12.0

    x = np.linspace(0.0, L, 200_001)
    moment = P * (L - x)            # bending moment magnitude from the fixed end
    curvature = moment / (E * inertia)
    slope = np.concatenate(([0.0], np.cumsum((curvature[:-1] + curvature[1:]) / 2 * np.diff(x))))
    deflection = np.concatenate(([0.0], np.cumsum((slope[:-1] + slope[1:]) / 2 * np.diff(x))))

    assert deflection[-1] == pytest.approx(res.tip_deflection_mm, rel=1e-4)


def test_cantilever_case_matches_reference_and_is_clean_control() -> None:
    case = load_case_file(ROOT / "benchmark" / "synthetic" / "syn-cantilever-0001.md")
    ref = end_loaded_cantilever(
        load_N=500.0,
        length_mm=300.0,
        width_mm=20.0,
        height_mm=10.0,
        youngs_modulus_MPa=200.0e3,
    )

    stress_expected = next(
        o for o in case.outputs if o.source == "expected" and o.name == "bending_stress"
    )
    defl_expected = next(
        o for o in case.outputs if o.source == "expected" and o.name == "tip_deflection"
    )
    assert stress_expected.value == pytest.approx(ref.sigma_max_MPa)
    assert defl_expected.value == pytest.approx(ref.tip_deflection_mm)

    result = audit_case(case)
    assert result.detected_failure_modes == []
    assert result.passed
