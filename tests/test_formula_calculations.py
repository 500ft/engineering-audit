from __future__ import annotations

import pytest

from mechaudit.case_loader import BenchmarkCase
from mechaudit.pressure_vessel import compute_pressure_vessel, within_tolerance


def _pressure_vessel_case() -> BenchmarkCase:
    return BenchmarkCase.model_validate(
        {
            "case_id": "formula-check",
            "schema_version": "0.3.0",
            "source_type": "synthetic",
            "status": "complete",
            "source": {
                "kind": "synthetic",
                "description": "Formula-level calculation test.",
                "provenance_tier": "synthetic",
                "raw_output_available": True,
            },
            "prompt_id": "formula_check",
            "problem_statement": "Formula-level pressure-vessel calculation test.",
            "llm_response": {"prompt": "n/a", "response": "n/a"},
            "failure_modes": [],
            "formulas_used": [],
            "inputs": {
                "pressure": {"value": 1.2, "unit": "MPa"},
                "radius": {"value": 50, "unit": "mm"},
                "thickness": {"value": 3, "unit": "mm"},
                "yield_strength": {"value": 120, "unit": "MPa"},
            },
            "outputs": [],
            "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
            "expected_result": {
                "value": 20,
                "unit": "MPa",
                "method": "formula-level calculation test",
                "required_assumptions": ["thin-walled cylinder"],
            },
            "tolerance": {"relative": 0.005, "absolute": None},
            "notes": {},
            "source_path": "tests/test_formula_calculations.py",
        }
    )


def test_pressure_vessel_formula_calculations() -> None:
    values = compute_pressure_vessel(_pressure_vessel_case())

    assert values["thin_wall_ratio"] == pytest.approx(16.667, rel=1e-4)
    assert values["hoop_stress_MPa"] == pytest.approx(20.0)
    assert values["hoop_stress_inner_radius_MPa"] == pytest.approx(20.0)
    assert values["hoop_stress_mean_radius_MPa"] == pytest.approx(20.6)
    assert values["hoop_stress_effective_radius_0p6t_MPa"] == pytest.approx(20.72)
    assert values["longitudinal_stress_MPa"] == pytest.approx(10.0)
    assert values["max_stress_MPa"] == pytest.approx(20.0)
    assert values["yield_safety_factor"] == pytest.approx(6.0)


def test_tolerance_comparison() -> None:
    assert within_tolerance(100.4, 100.0, relative=0.005)
    assert not within_tolerance(101.0, 100.0, relative=0.005)
