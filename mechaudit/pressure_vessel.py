from __future__ import annotations

from math import isclose

from pint import UnitRegistry

from .audit_result import AuditResult
from .case_loader import BenchmarkCase, OutputRecord, QuantityValue
from .stress_concentration import plate_with_hole


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


# Inputs that mark a finite-width holed-plate stress-concentration case, and the
# formula_ids the verifier recognises for it. Either signal is enough to attempt
# the Kt-aware recomputation; both are present in well-formed cases.
PLATE_HOLE_INPUTS = ("plate_width", "hole_diameter", "thickness", "axial_force")
STRESS_CONCENTRATION_FORMULA_IDS = {"net_section_stress", "stress_concentration_peak"}


def compute_plate_with_hole(case: BenchmarkCase) -> dict[str, float]:
    """Recompute net stress, Kt, and peak stress for a holed-plate case in MPa.

    Independent of any LLM output: pulls the geometry/load from ``inputs`` and
    defers to :func:`mechaudit.stress_concentration.plate_with_hole`, the in-repo
    analytically/FEA-validated oracle (Peterson/Heywood Kt). All lengths are
    converted to mm and the force to N so the result is in MPa.
    """
    width = _input(case, "plate_width").to("mm").magnitude
    diameter = _input(case, "hole_diameter").to("mm").magnitude
    thickness = _input(case, "thickness").to("mm").magnitude
    force = _input(case, "axial_force").to("N").magnitude
    res = plate_with_hole(
        width_mm=width,
        hole_diameter_mm=diameter,
        thickness_mm=thickness,
        axial_force_N=force,
    )
    return {
        "kt_net": res.Kt_net,
        "d_over_W": res.d_over_W,
        "net_section_stress_MPa": res.sigma_net_MPa,
        "gross_section_stress_MPa": res.sigma_gross_MPa,
        "peak_stress_MPa": res.sigma_max_MPa,
    }


CANONICAL_STRESS_UNIT = "MPa"

# Maps an LLM output name prefix to the recomputed reference key it should be
# compared against, in canonical (MPa) units. Used by the unit-consistency check.
STRESS_REFERENCE_KEYS = {
    "axial_stress": "axial_stress_MPa",
    "hoop_stress": "hoop_stress_MPa",
    "longitudinal_stress": "longitudinal_stress_MPa",
}


def _formula_ids(case: BenchmarkCase) -> list[str]:
    return [formula.formula_id or "" for formula in case.formulas_used]


def _is_stress_unit(unit: str | None) -> bool:
    """True if ``unit`` is dimensionally a stress/pressure (convertible to MPa)."""
    if not unit:
        return False
    try:
        return Q_(1.0, _unit(unit)).check("[pressure]")
    except Exception:
        return False


def _to_canonical_stress(value: float, unit: str | None) -> float | None:
    """Convert a stress value to MPa, or ``None`` if the unit is unusable."""
    if not unit:
        return None
    try:
        return Q_(value, _unit(unit)).to(CANONICAL_STRESS_UNIT).magnitude
    except Exception:
        return None


def _canonical_output_value(output: OutputRecord) -> float:
    """Magnitude of a stress output in canonical MPa.

    Converts when the unit is a stress unit; otherwise returns the raw value so
    that missing/non-stress units stay the responsibility of the dedicated
    unit-consistency check. For MPa outputs this is a no-op, so existing
    behavior is unchanged.
    """
    if _is_stress_unit(output.unit):
        converted = _to_canonical_stress(output.value, output.unit)
        if converted is not None:
            return converted
    return output.value


def _reference_for_output(name: str, recomputed: dict[str, float | str]) -> float | None:
    """Recomputed reference value (MPa) for an LLM output name, if available."""
    for prefix, key in STRESS_REFERENCE_KEYS.items():
        if name.startswith(prefix):
            value = recomputed.get(key)
            return value if isinstance(value, (int, float)) else None
    return None


def audit_output_unit_consistency(case: BenchmarkCase, result: AuditResult) -> None:
    """Convert reported output units before comparing, and flag mismatched units.

    Implements the FM-01 "unit conversion before comparison" gap: the verifier
    must not treat an output magnitude as MPa regardless of ``output.unit``. For
    each LLM stress output it (1) converts the reported value into canonical MPa
    and (2) compares against the recomputed reference. The signature of a
    mismatched-unit error is a value whose *bare magnitude* matches the reference
    but whose *unit-converted* value does not — i.e. the right number under the
    wrong unit label (e.g. ``200 psi`` when the answer is ``200 MPa``), or a
    safety comparison made across mismatched units.
    """
    for output in case.outputs:
        if output.source != "llm":
            continue
        reference = _reference_for_output(output.name, result.recomputed_values)
        if reference is None:
            continue

        unit = output.unit
        if not _is_stress_unit(unit):
            # A stress reported with a non-stress (or missing) unit is a
            # dimensional inconsistency with no tolerance.
            if unit is not None:
                result.add_check(
                    "unit-dimensionality",
                    False,
                    f"Output '{output.name}' is a stress but its unit {unit!r} is not a pressure/stress unit.",
                    "FM-01",
                )
            continue

        converted = _to_canonical_stress(output.value, unit)
        if converted is None:
            continue

        converted_matches = _same_value(converted, reference, case)
        bare_matches = _same_value(output.value, reference, case)

        if not converted_matches and bare_matches and unit != CANONICAL_STRESS_UNIT:
            result.add_check(
                "unit-conversion-before-comparison",
                False,
                (
                    f"Output '{output.name}' reads {output.value:g} {unit}, but the "
                    f"recomputed value is {reference:.6g} {CANONICAL_STRESS_UNIT}. "
                    f"The number matches only if units are ignored: {output.value:g} {unit} "
                    f"= {converted:.6g} {CANONICAL_STRESS_UNIT}."
                ),
                "FM-01",
            )


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

    if _is_plate_hole_case(case, formula_ids):
        _audit_stress_concentration(case, result)

    audit_output_unit_consistency(case, result)

    return result


def _is_plate_hole_case(case: BenchmarkCase, formula_ids: list[str]) -> bool:
    """True for a finite-width holed-plate stress-concentration case.

    Requires the geometry/load inputs to be present (so the oracle can run) and
    at least one recognised stress-concentration ``formula_id``. Cases without
    the holed-plate signature (e.g. pressure-vessel or axial cases) are ignored,
    keeping the check from false-positiving on unrelated problem classes.
    """
    if not all(name in case.inputs for name in PLATE_HOLE_INPUTS):
        return False
    return bool(STRESS_CONCENTRATION_FORMULA_IDS.intersection(formula_ids))


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
            _matching_hoop_conventions(_canonical_output_value(final_output), case, pv)
            if final_output is not None
            else {}
        )
        if final_output is not None:
            _record_hoop_match(result, "final", final_matches)

        # A value that matches a convention only when the unit label is ignored
        # is a unit error (FM-01), not arithmetic (FM-03); the unit-consistency
        # check owns it, so suppress the redundant FM-03 here.
        bare_matches_convention = (
            bool(_matching_hoop_conventions(final_output.value, case, pv))
            if final_output is not None
            else False
        )
        if (
            "hoop_stress_thin_wall" in formula_ids
            and final_output is not None
            and not final_matches
            and not bare_matches_convention
        ):
            result.add_check(
                "hoop-arithmetic",
                False,
                f"Hoop stress does not match any accepted convention ({_format_accepted_hoop_values(case, pv)}); reported {final_output.value:g} {final_output.unit}.",
                "FM-03",
            )

        if final_outputs:
            final_named_matches = _matching_hoop_conventions(
                _canonical_output_value(final_outputs[0]), case, pv
            )
        else:
            final_named_matches = {}
        if final_named_matches:
            _record_hoop_match(result, "final", final_named_matches)
            for output in substitution_outputs:
                substitution_matches = _matching_hoop_conventions(
                    _canonical_output_value(output), case, pv
                )
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


def _llm_peak_stress(case: BenchmarkCase) -> OutputRecord | None:
    """The LLM's reported peak/maximum hole-edge stress for a holed-plate case.

    Accepts the canonical ``peak_stress`` name or common aliases, preferring a
    value carried in a stress unit. Net-section nominal outputs are excluded so
    the reported peak is compared, not the intermediate.
    """
    candidates = [
        output
        for output in case.outputs
        if output.source == "llm"
        and not output.name.startswith("net_section")
        and (
            output.name.startswith("peak_stress")
            or output.name.startswith("max_stress")
            or output.name.startswith("maximum_stress")
            or output.symbol in {"sigma_max", "σ_max"}
        )
    ]
    if not candidates:
        return None
    with_stress_unit = [o for o in candidates if _is_stress_unit(o.unit)]
    return (with_stress_unit or candidates)[0]


def _audit_stress_concentration(case: BenchmarkCase, result: AuditResult) -> None:
    """Kt-aware check for a finite-width holed plate in axial tension (FM-04).

    Recomputes ``Kt_net``, ``sigma_net`` and ``sigma_max`` from the inputs via the
    in-repo oracle, records them, and compares the LLM's reported peak stress to
    the validated ``sigma_max``. Beyond tolerance it flags ``FM-04`` and names the
    sub-case: peak == net-section nominal => stress concentration omitted;
    otherwise wrong Kt or wrong nominal. A peak within tolerance (the
    ``syn-kt-hole-0001`` control, or any correctly solved case) does not flag.
    """
    sc = compute_plate_with_hole(case)
    result.recomputed_values["stress_concentration_kt_net"] = sc["kt_net"]
    result.recomputed_values["net_section_stress_MPa"] = sc["net_section_stress_MPa"]
    result.recomputed_values["peak_stress_MPa"] = sc["peak_stress_MPa"]

    peak_output = _llm_peak_stress(case)
    if peak_output is None:
        result.add_check(
            "stress-concentration-peak",
            True,
            f"No LLM peak-stress output to check; recomputed sigma_max = {sc['peak_stress_MPa']:.6g} MPa "
            f"(Kt_net = {sc['kt_net']:.4g}, sigma_net = {sc['net_section_stress_MPa']:.6g} MPa).",
        )
        return

    reported = _canonical_output_value(peak_output)
    expected_peak = sc["peak_stress_MPa"]

    if _same_value(reported, expected_peak, case):
        result.add_check(
            "stress-concentration-peak",
            True,
            f"Peak stress {reported:.6g} MPa matches Kt_net*sigma_net = {expected_peak:.6g} MPa "
            f"(Kt_net = {sc['kt_net']:.4g}).",
        )
        return

    if _same_value(reported, sc["net_section_stress_MPa"], case):
        detail = (
            f"reported {reported:.6g} MPa equals the net-section nominal "
            f"sigma_net = {sc['net_section_stress_MPa']:.6g} MPa, so the stress "
            f"concentration (Kt_net = {sc['kt_net']:.4g}) was omitted"
        )
    else:
        detail = (
            f"reported {reported:.6g} MPa matches neither the validated peak "
            f"sigma_max = {expected_peak:.6g} MPa nor the net-section nominal "
            f"sigma_net = {sc['net_section_stress_MPa']:.6g} MPa, indicating a wrong Kt "
            f"or wrong nominal (correct Kt_net = {sc['kt_net']:.4g})"
        )

    result.add_check(
        "stress-concentration-peak",
        False,
        f"Peak hole-edge stress should be Kt_net*sigma_net = {expected_peak:.6g} MPa; {detail}.",
        "FM-04",
    )
