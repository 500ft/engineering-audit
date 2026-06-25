"""Tests for the unit-conversion-before-comparison verifier check (FM-01)."""

from __future__ import annotations

from typing import Any

import pytest

from mechaudit.case_loader import BenchmarkCase
from mechaudit.pressure_vessel import (
    audit_case,
    audit_output_unit_consistency,
    compute_pressure_vessel,
)
from mechaudit.audit_result import AuditResult


def _pv_case(hoop_value: float, hoop_unit: str | None) -> BenchmarkCase:
    """Thin-wall PV case (recomputed hoop = 20 MPa) with one LLM hoop output."""
    data: dict[str, Any] = {
        "case_id": "unit-check",
        "schema_version": "0.3.0",
        "source_type": "synthetic",
        "status": "complete",
        "source": {
            "kind": "synthetic",
            "description": "Unit-consistency test case.",
            "provenance_tier": "synthetic",
            "raw_output_available": True,
        },
        "prompt_id": "unit_check",
        "problem_statement": "Hoop stress for a thin-walled pressure vessel.",
        "llm_response": {"prompt": "n/a", "response": "n/a"},
        "expected_result": {
            "value": 20,
            "unit": "MPa",
            "method": "sigma_h = p r / t",
            "required_assumptions": [],
        },
        "failure_modes": [],
        "formulas_used": [
            {
                "id": "eq1",
                "formula_id": "hoop_stress_thin_wall",
                "equation": "sigma_h = p * r / t",
                "purpose": "Compute hoop stress",
                "variables": {"sigma_h": "hoop_stress", "p": "pressure", "r": "radius", "t": "thickness"},
            }
        ],
        "inputs": {
            "pressure": {"value": 1.2, "unit": "MPa"},
            "radius": {"value": 50, "unit": "mm"},
            "thickness": {"value": 3, "unit": "mm"},
        },
        "outputs": [
            {"name": "hoop_stress", "symbol": "sigma_h", "value": hoop_value, "unit": hoop_unit, "source": "llm"},
            {"name": "hoop_stress", "symbol": "sigma_h", "value": 20, "unit": "MPa", "source": "expected"},
        ],
        "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
        "tolerance": {"relative": 0.005, "absolute": None, "policy": "docs/tolerance_policy.md"},
        "notes": {},
        "source_path": "tests/test_unit_consistency.py",
    }
    return BenchmarkCase.model_validate(data)


def _detected(case: BenchmarkCase) -> set[str]:
    return set(audit_case(case).detected_failure_modes)


def test_correct_mpa_value_does_not_flag_fm01() -> None:
    # Right number, right unit: no unit failure.
    assert "FM-01" not in _detected(_pv_case(20.0, "MPa"))


def test_right_number_wrong_unit_flags_fm01() -> None:
    # 20 psi labeled where the answer is 20 MPa: the magnitude matches only if
    # units are ignored. This is the mismatched-unit comparison FM-01 targets.
    assert "FM-01" in _detected(_pv_case(20.0, "psi"))


def test_correctly_converted_value_does_not_flag_fm01() -> None:
    # 20 MPa correctly expressed in psi (~2900.75 psi) is unit-consistent.
    psi = 20.0 * 145.0377377
    assert "FM-01" not in _detected(_pv_case(psi, "psi"))


def test_stress_with_non_stress_unit_flags_fm01() -> None:
    # A hoop stress reported in millimetres is dimensionally inconsistent.
    assert "FM-01" in _detected(_pv_case(20.0, "mm"))


def test_check_reports_conversion_in_message() -> None:
    case = _pv_case(20.0, "psi")
    result = AuditResult(
        case_id=case.case_id,
        source_path=case.source_path,
        expected_failure_modes=case.failure_modes,
    )
    result.recomputed_values.update(compute_pressure_vessel(case))
    audit_output_unit_consistency(case, result)

    flagged = [c for c in result.checks if c.detected_failure_mode == "FM-01"]
    assert flagged
    assert "MPa" in flagged[0].message
    assert "psi" in flagged[0].message


def test_kpa_label_on_mpa_answer_flags_fm01() -> None:
    # 20 kPa where the answer is 20 MPa: off by 1000x, same signature.
    assert "FM-01" in _detected(_pv_case(20.0, "kPa"))


def test_no_reference_quantity_means_no_unit_flag() -> None:
    # An LLM output whose name has no recomputed reference is not unit-checked.
    case = _pv_case(20.0, "psi")
    case.outputs[0].name = "unrelated_quantity"
    assert "FM-01" not in _detected(case)
