from __future__ import annotations

import math

import pytest

from cadloop import volume

AUTHORED = {
    "Length": "100mm",
    "Width": "60mm",
    "PlateThickness": "5mm",
    "HoleDiameter": "8mm",
}
VARIANT = {
    "Length": "150mm",
    "Width": "80mm",
    "PlateThickness": "6mm",
    "HoleDiameter": "10mm",
}


def test_parse_mm_accepts_explicit_millimetres() -> None:
    assert volume.parse_mm("150mm") == pytest.approx(150.0)
    assert volume.parse_mm(" 6.5 MM ") == pytest.approx(6.5)


@pytest.mark.parametrize("value", [150, 150.0, "150", "150 in", "", None, "mm"])
def test_parse_mm_rejects_anything_not_an_explicit_millimetre_dimension(value: object) -> None:
    with pytest.raises(volume.DimensionError):
        volume.parse_mm(value)


def test_authored_default_matches_the_value_measured_on_the_host() -> None:
    # The authored template measured 29748.672587712812 mm3 from SOLIDWORKS mass
    # properties; the oracle must agree with that to well inside the gate.
    assert volume.plate_with_center_hole_mm3(AUTHORED) == pytest.approx(29748.6726, abs=1e-3)


def test_oracle_is_computed_not_tabulated() -> None:
    expected = (150.0 * 80.0 - math.pi * 10.0 ** 2 / 4.0) * 6.0
    assert volume.plate_with_center_hole_mm3(VARIANT) == pytest.approx(expected)


def test_oracle_rejects_a_hole_that_does_not_fit() -> None:
    with pytest.raises(volume.DimensionError):
        volume.plate_with_center_hole_mm3(dict(AUTHORED, HoleDiameter="60mm"))


def test_gate_accepts_a_measurement_inside_tolerance() -> None:
    expected = volume.plate_with_center_hole_mm3(VARIANT)
    check = volume.check_volume("plate_with_center_hole", VARIANT, expected * 1.001, 0.5)
    assert check["accepted"] is True
    assert check["error_pct"] == pytest.approx(0.1, abs=1e-6)


def test_gate_rejects_the_stale_volume_that_a_clean_rebuild_reported() -> None:
    # Regression guard for the run that reported success while returning the
    # template's original volume after being asked for 150 x 80 x 6 mm.
    check = volume.check_volume("plate_with_center_hole", VARIANT, 29748.672587712812, 0.5)
    assert check["accepted"] is False
    assert check["expected_mm3"] == pytest.approx(71528.76, abs=1e-2)
    assert check["error_pct"] > 50


def test_gate_reports_unverified_when_no_oracle_is_declared() -> None:
    check = volume.check_volume(None, VARIANT, 1234.0, 0.5)
    assert check["accepted"] is None
    assert check["measured_mm3"] == pytest.approx(1234.0)


def test_unknown_oracle_name_is_an_error_not_a_pass() -> None:
    with pytest.raises(KeyError):
        volume.check_volume("no_such_oracle", VARIANT, 1234.0, 0.5)
