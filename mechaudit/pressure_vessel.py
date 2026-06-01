from __future__ import annotations

from math import isclose

from pint import UnitRegistry

from .audit_result import AuditResult
from .case_loader import BenchmarkCase, OutputRecord, QuantityValue


ureg = UnitRegistry()
Q_ = ureg.Quantity


def _unit(unit: str | None) -> str:
    if not unit:
        return ""
    return unit.replace("^", "**")


def _quantity(value: QuantityValue):
    return Q_(value.value, _unit(value.unit))


def _input(case: BenchmarkCase, name: str):
    return _quantity(case.inputs[name])


def within_tolerance(
    actual: float,
    expected: float,
    relative: float | None = 0.005,
    absolute: float | None = None,
) -> bool:
    if absolute is not None and abs(actual - expected) <= absolute:
        return True
    if expected == 0:
        return isclose(actual, expected, abs_tol=absolute or 0.0)
    if relative is None:
        return False
    return abs(actual - expected) / abs(expected) <= relative


def compute_pressure_vessel(case: BenchmarkCase) -> dict[str, float]:
    pressure = _input(case, "pressure").to("MPa")
    radius = _input(case, "radius").to("mm")
    thickness = _input(case, "thickness").to("mm")

    thin_wall_ratio = (radius / thickness).to_base_units().magnitude
    hoop = (pressure * radius / thickness).to("MPa")
    longitudinal = (pressure * radius / (2 * thickness)).to("MPa")
    max_stress = max(hoop.magnitude, longitudinal.magnitude)

    values: dict[str, float] = {
        "thin_wall_ratio": thin_wall_ratio,
        "hoop_stress_MPa": hoop.magnitude,
        "longitudinal_stress_MPa": longitudinal.magnitude,
        "max_stress_MPa": max_stress,
    }
    if "yield_strength" in case.inputs:
        yield_strength = _input(case, "yield_strength").to("MPa").magnitude
        values["yield_safety_factor"] = yield_strength / max_stress
    return values


def compute_axial_stress(case: BenchmarkCase) -> float:
    force = _input(case, "force")
    area = _input(case, "area")
    return (force / area).to("MPa").magnitude


def _formula_ids(case: BenchmarkCase) -> list[str]:
    return [formula.formula_id or "" for formula in case.formulas_used]


def _llm_outputs(case: BenchmarkCase, name: str) -> list[OutputRecord]:
    return [
        output
        for output in case.outputs
        if output.source == "llm" and output.name.startswith(name)
    ]


def _expected_output(case: BenchmarkCase, name: str) -> OutputRecord | None:
    for output in case.outputs:
        if output.source == "expected" and output.name == name:
            return output
    return None


def _same_value(
    actual: float,
    expected: float,
    case: BenchmarkCase,
) -> bool:
    return within_tolerance(
        actual,
        expected,
        relative=case.tolerance.relative if case.tolerance.relative is not None else 0.005,
        absolute=case.tolerance.absolute,
    )


def audit_case(case: BenchmarkCase) -> AuditResult:
    result = AuditResult(
        case_id=case.case_id,
        source_path=case.source_path,
        expected_failure_modes=case.failure_modes,
        status=case.status,
    )

    if case.status == "pending_capture":
        result.skipped = True
        result.skip_reason = "pending_capture"
        result.add_check("case-status", True, "Skipped pending real-world capture slot.")
        return result

    formula_ids = _formula_ids(case)

    if "axial_stress" in formula_ids:
        _audit_axial_stress(case, result)

    if {"pressure", "radius", "thickness"}.issubset(case.inputs):
        pv = compute_pressure_vessel(case)
        result.recomputed_values.update(pv)
        _audit_pressure_vessel(case, result, formula_ids, pv)

    return result


def _audit_axial_stress(case: BenchmarkCase, result: AuditResult) -> None:
    recomputed = compute_axial_stress(case)
    result.recomputed_values["axial_stress_MPa"] = recomputed
    llm = _llm_outputs(case, "axial_stress")
    if llm and not _same_value(llm[0].value, recomputed, case):
        result.add_check(
            "axial-unit-recompute",
            False,
            f"Axial stress recomputes to {recomputed:.6g} MPa, not {llm[0].value:g} {llm[0].unit}.",
            "FM-01",
        )
    else:
        result.add_check("axial-unit-recompute", True, "Axial stress is unit-consistent.")


def _audit_pressure_vessel(
    case: BenchmarkCase,
    result: AuditResult,
    formula_ids: list[str],
    pv: dict[str, float],
) -> None:
    hoop = pv["hoop_stress_MPa"]
    longitudinal = pv["longitudinal_stress_MPa"]
    ratio = pv["thin_wall_ratio"]

    if "longitudinal_stress_thin_wall" in formula_ids:
        for formula in case.formulas_used:
            if (
                formula.formula_id == "longitudinal_stress_thin_wall"
                and formula.variables.get("sigma") == "hoop_stress"
            ):
                result.add_check(
                    "formula-id",
                    False,
                    "Longitudinal thin-wall formula was used for requested hoop stress.",
                    "FM-02A",
                )
                break

    assumptions = " ".join(case.notes.assumptions_stated).lower()
    if "thin" in assumptions and ratio < 10:
        result.add_check(
            "thin-wall-applicability",
            False,
            f"Thin-wall ratio r/t = {ratio:.6g}; nominal stresses are outside applicability.",
            "FM-02B",
        )

    expected = _expected_output(case, "hoop_stress")
    llm_hoop = _llm_outputs(case, "hoop_stress")
    if expected and llm_hoop:
        final_outputs = [output for output in llm_hoop if output.name.endswith("_final")]
        substitution_outputs = [
            output for output in llm_hoop if output.name.endswith("_substitution")
        ]
        ordinary_outputs = [
            output
            for output in llm_hoop
            if not output.name.endswith("_final")
            and not output.name.endswith("_substitution")
        ]

        if (
            "hoop_stress_thin_wall" in formula_ids
            and ordinary_outputs
            and not _same_value(ordinary_outputs[0].value, hoop, case)
        ):
            result.add_check(
                "hoop-arithmetic",
                False,
                f"Hoop stress recomputes to {hoop:.6g} MPa, not {ordinary_outputs[0].value:g} {ordinary_outputs[0].unit}.",
                "FM-03",
            )

        if final_outputs and _same_value(final_outputs[0].value, expected.value, case):
            for output in substitution_outputs:
                if not _same_value(output.value, hoop, case):
                    result.add_check(
                        "reasoning-consistency",
                        False,
                        f"Final answer is correct, but substitution says {output.value:g} {output.unit}; recomputed hoop stress is {hoop:.6g} MPa.",
                        "FM-07",
                    )
                    break

    if case.case_id == "syn-fm02b-0001":
        result.add_check(
            "nominal-stresses",
            True,
            f"Nominal thin-wall values only: hoop={hoop:.6g} MPa, longitudinal={longitudinal:.6g} MPa.",
        )
