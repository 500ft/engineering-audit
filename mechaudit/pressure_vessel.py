from __future__ import annotations

from math import isclose

from pint import UnitRegistry

from .audit_result import AuditResult
from .case_loader import BenchmarkCase, OutputRecord, QuantityValue


ureg = UnitRegistry()
Q_ = ureg.Quantity

DEFAULT_HOOP_CONVENTIONS = ["inner_radius"]
HOOP_CONVENTION_RESULT_KEYS = {
    "inner_radius": "hoop_stress_inner_radius_MPa",
    "mean_radius": "hoop_stress_mean_radius_MPa",
    "effective_radius_0p6t": "hoop_stress_effective_radius_0p6t_MPa",
}


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
    hoop_inner = (pressure * radius / thickness).to("MPa")
    hoop_mean = (pressure * (radius + 0.5 * thickness) / thickness).to("MPa")
    hoop_effective = (pressure * (radius + 0.6 * thickness) / thickness).to("MPa")
    longitudinal = (pressure * radius / (2 * thickness)).to("MPa")
    max_stress = max(hoop_inner.magnitude, longitudinal.magnitude)

    values: dict[str, float] = {
        "thin_wall_ratio": thin_wall_ratio,
        "hoop_stress_MPa": hoop_inner.magnitude,
        "hoop_stress_inner_radius_MPa": hoop_inner.magnitude,
        "hoop_stress_mean_radius_MPa": hoop_mean.magnitude,
        "hoop_stress_effective_radius_0p6t_MPa": hoop_effective.magnitude,
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


def _accepted_hoop_conventions(case: BenchmarkCase) -> list[str]:
    return list(case.tolerance.accepted_conventions or DEFAULT_HOOP_CONVENTIONS)


def _hoop_convention_values(pv: dict[str, float], case: BenchmarkCase) -> dict[str, float]:
    return {
        convention: pv[HOOP_CONVENTION_RESULT_KEYS[convention]]
        for convention in _accepted_hoop_conventions(case)
    }


def _matching_hoop_conventions(
    value: float,
    case: BenchmarkCase,
    pv: dict[str, float],
) -> dict[str, float]:
    return {
        convention: convention_value
        for convention, convention_value in _hoop_convention_values(pv, case).items()
        if _same_value(value, convention_value, case)
    }


def _format_accepted_hoop_values(case: BenchmarkCase, pv: dict[str, float]) -> str:
    return ", ".join(
        f"{convention}={value:.6g} MPa"
        for convention, value in _hoop_convention_values(pv, case).items()
    )


def _record_hoop_match(
    result: AuditResult,
    output_kind: str,
    matches: dict[str, float],
) -> None:
    if not matches:
        result.recomputed_values[f"hoop_stress_{output_kind}_matched_convention"] = "none"
        return
    result.recomputed_values[f"hoop_stress_{output_kind}_matched_convention"] = ",".join(matches)


def _matches_differ_beyond_tolerance(
    left: dict[str, float],
    right: dict[str, float],
    case: BenchmarkCase,
) -> bool:
    return all(
        not _same_value(left_value, right_value, case)
        for left_value in left.values()
        for right_value in right.values()
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
            targets_hoop_stress = (
                "hoop" in formula.purpose.lower()
                or "hoop_stress" in formula.variables.values()
            )
            if (
                formula.formula_id == "longitudinal_stress_thin_wall"
                and targets_hoop_stress
            ):
                result.add_check(
                    "formula-id",
                    False,
                    "Longitudinal thin-wall formula was used for requested hoop stress.",
                    "FM-02A",
                )
                break

    assumptions = " ".join(case.notes.assumptions_stated).lower()
    thin_wall_assumed = "thin" in assumptions
    thin_wall_invalid = thin_wall_assumed and ratio < 10
    if thin_wall_invalid:
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
        final_output = (
            ordinary_outputs[0]
            if ordinary_outputs
            else (final_outputs[0] if final_outputs else None)
        )
        final_matches = (
            _matching_hoop_conventions(final_output.value, case, pv)
            if final_output is not None
            else {}
        )
        if final_output is not None:
            _record_hoop_match(result, "final", final_matches)

        if (
            "hoop_stress_thin_wall" in formula_ids
            and final_output is not None
            and not final_matches
        ):
            result.add_check(
                "hoop-arithmetic",
                False,
                f"Hoop stress does not match any accepted convention ({_format_accepted_hoop_values(case, pv)}); reported {final_output.value:g} {final_output.unit}.",
                "FM-03",
            )

        if final_outputs:
            final_named_matches = _matching_hoop_conventions(final_outputs[0].value, case, pv)
        else:
            final_named_matches = {}
        if final_named_matches:
            _record_hoop_match(result, "final", final_named_matches)
            for output in substitution_outputs:
                substitution_matches = _matching_hoop_conventions(output.value, case, pv)
                _record_hoop_match(result, "substitution", substitution_matches)
                if not substitution_matches:
                    result.add_check(
                        "reasoning-consistency",
                        False,
                        f"Final answer matches an accepted convention, but substitution says {output.value:g} {output.unit}; accepted values are {_format_accepted_hoop_values(case, pv)}.",
                        "FM-07",
                    )
                    break
                if (
                    set(substitution_matches) != set(final_named_matches)
                    and _matches_differ_beyond_tolerance(substitution_matches, final_named_matches, case)
                ):
                    result.add_check(
                        "reasoning-consistency",
                        False,
                        f"Substitution convention {','.join(substitution_matches)} differs from final convention {','.join(final_named_matches)}.",
                        "FM-07",
                    )
                    break

    if thin_wall_invalid:
        result.add_check(
            "nominal-stresses",
            True,
            f"Nominal thin-wall values only: hoop={hoop:.6g} MPa, longitudinal={longitudinal:.6g} MPa.",
        )
