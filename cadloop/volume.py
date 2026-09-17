"""Closed-form volume oracles used as CAD acceptance gates.

A rebuild that reports success only proves SOLIDWORKS raised no error. It does
not prove the requested geometry was produced. Each fixture therefore declares
an oracle whose value is compared against measured mass properties.
"""

import math
import re

_DIMENSION = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*mm\s*$", re.IGNORECASE)


class DimensionError(ValueError):
    """Raised when a parameter value is not an explicit millimetre dimension."""


def parse_mm(value):
    """Return millimetres from an explicit dimension string such as "150mm".

    Bare numbers are rejected: an unlabelled value in a job specification is
    ambiguous between the document unit system and the SOLIDWORKS API's metres.
    """
    if isinstance(value, str):
        match = _DIMENSION.match(value)
        if match:
            return float(match.group(1))
    raise DimensionError("expected an explicit millimetre dimension, got %r" % (value,))


def plate_with_center_hole_mm3(parameters):
    """Volume of a rectangular plate with one through hole.

    V = (Length * Width - pi * HoleDiameter^2 / 4) * PlateThickness
    """
    length = parse_mm(parameters["Length"])
    width = parse_mm(parameters["Width"])
    thickness = parse_mm(parameters["PlateThickness"])
    hole_diameter = parse_mm(parameters["HoleDiameter"])

    if hole_diameter >= min(length, width):
        raise DimensionError(
            "hole diameter %.3fmm does not fit within %.3f x %.3fmm"
            % (hole_diameter, length, width)
        )

    hole_area = math.pi * hole_diameter ** 2 / 4.0
    return (length * width - hole_area) * thickness


ORACLES = {
    "plate_with_center_hole": plate_with_center_hole_mm3,
}


def expected_volume_mm3(oracle_name, parameters):
    """Return the expected volume for a named oracle, or raise KeyError."""
    return ORACLES[oracle_name](parameters)


def check_volume(oracle_name, parameters, measured_mm3, tolerance_pct):
    """Compare a measured volume against its oracle.

    Returns a dict describing the comparison. `accepted` is None when no oracle
    is declared, so that an unverified build is never reported as verified.
    """
    if not oracle_name:
        return {
            "oracle": None,
            "accepted": None,
            "measured_mm3": measured_mm3,
            "note": "no oracle declared; volume recorded but not verified",
        }

    expected = expected_volume_mm3(oracle_name, parameters)
    error_pct = abs(measured_mm3 - expected) / expected * 100.0
    return {
        "oracle": oracle_name,
        "accepted": error_pct <= tolerance_pct,
        "expected_mm3": expected,
        "measured_mm3": measured_mm3,
        "error_pct": error_pct,
        "tolerance_pct": tolerance_pct,
    }
