"""Independent, analytically-validated reference solutions for ground-truth cases.

These are the in-repo "oracle" computations behind the FEA/analytically-validated
ground-truth benchmark cases (`syn-kt-*`, `syn-cantilever-*`). They are NOT wild
model captures and produce no model output — they compute the trusted answer that
such ground-truth cases are scored against, from first principles, with citations.

Two families are covered:

1. Stress-concentration factor (Kt) for a finite-width flat plate with a central
   transverse circular hole in uniaxial tension. The Kt correlation is the
   Heywood/Howland fit to Peterson's chart (Pilkey, *Peterson's Stress
   Concentration Factors*, Chart 4.1 for a flat tension bar with a transverse
   hole; the same fit appears in Roark, Table 17.1). The fit is validated here by
   its d/W -> 0 limit recovering the Kirsch infinite-plate value Kt = 3.0 to
   within ~0.4% (the fit's limit is 3.004).

2. End-loaded rectangular cantilever (Euler-Bernoulli): maximum bending stress at
   the fixed end and tip deflection. Reference: Roark, Table 8.1 case 1; Gere &
   Goodno, *Mechanics of Materials*. The closed forms are validated against an
   independent recomputation (sigma_max two ways; tip deflection by numerical
   double-integration of curvature) in `tests/test_ground_truth_references.py`.
"""

from __future__ import annotations

from dataclasses import dataclass


# Heywood/Howland fit coefficients for Kt referenced to NET section stress.
# Kt_net(s) = 2 + 0.284*s - 0.600*s**2 + 1.32*s**3,  with s = 1 - d/W.
_KT_HOLE_COEFFS = (2.0, 0.284, -0.600, 1.32)


@dataclass(frozen=True)
class PlateHoleResult:
    d_over_W: float
    Kt_net: float
    Kt_gross: float
    sigma_gross_MPa: float
    sigma_net_MPa: float
    sigma_max_MPa: float


def kt_plate_with_hole_net(d_over_w: float) -> float:
    """Peterson/Heywood Kt (referenced to net-section stress) for a holed plate.

    Valid for 0 < d/W < 1 (finite-width plate, central transverse circular hole,
    uniaxial tension). As d/W -> 0 the value approaches the Kirsch infinite-plate
    factor of 3.0, which is the validation anchor for this correlation.
    """
    if not 0.0 < d_over_w < 1.0:
        raise ValueError("d/W must lie in the open interval (0, 1).")
    s = 1.0 - d_over_w
    c0, c1, c2, c3 = _KT_HOLE_COEFFS
    return c0 + c1 * s + c2 * s * s + c3 * s * s * s


def plate_with_hole(
    *,
    width_mm: float,
    hole_diameter_mm: float,
    thickness_mm: float,
    axial_force_N: float,
) -> PlateHoleResult:
    """Peak stress at the bore of a finite-width holed plate in axial tension.

    All inputs are SI-mm (force in N, lengths in mm), so stresses come out in MPa
    (1 N/mm^2 = 1 MPa). Returns net- and gross-referenced Kt, the nominal gross
    and net stresses, and the peak stress at the hole edge.
    """
    if hole_diameter_mm <= 0 or width_mm <= 0 or thickness_mm <= 0:
        raise ValueError("Geometry dimensions must be positive.")
    if hole_diameter_mm >= width_mm:
        raise ValueError("Hole diameter must be smaller than plate width.")

    d_over_w = hole_diameter_mm / width_mm
    kt_net = kt_plate_with_hole_net(d_over_w)

    area_gross = width_mm * thickness_mm
    area_net = (width_mm - hole_diameter_mm) * thickness_mm
    sigma_gross = axial_force_N / area_gross
    sigma_net = axial_force_N / area_net
    sigma_max = kt_net * sigma_net
    kt_gross = kt_net / (1.0 - d_over_w)

    return PlateHoleResult(
        d_over_W=d_over_w,
        Kt_net=kt_net,
        Kt_gross=kt_gross,
        sigma_gross_MPa=sigma_gross,
        sigma_net_MPa=sigma_net,
        sigma_max_MPa=sigma_max,
    )


@dataclass(frozen=True)
class CantileverResult:
    moment_of_inertia_mm4: float
    fixed_end_moment_Nmm: float
    sigma_max_MPa: float
    tip_deflection_mm: float


def end_loaded_cantilever(
    *,
    load_N: float,
    length_mm: float,
    width_mm: float,
    height_mm: float,
    youngs_modulus_MPa: float,
) -> CantileverResult:
    """Max bending stress and tip deflection of an end-loaded rectangular cantilever.

    Euler-Bernoulli, rectangular section (I = b h^3 / 12):

        sigma_max = M c / I = 6 P L / (b h^2)   at the fixed end
        delta_tip = P L^3 / (3 E I)

    SI-mm units throughout (N, mm, MPa); deflection in mm.
    """
    if min(load_N, length_mm, width_mm, height_mm, youngs_modulus_MPa) <= 0:
        raise ValueError("All cantilever parameters must be positive.")

    inertia = width_mm * height_mm**3 / 12.0
    c = height_mm / 2.0
    moment = load_N * length_mm
    sigma_max = moment * c / inertia
    tip_deflection = load_N * length_mm**3 / (3.0 * youngs_modulus_MPa * inertia)

    return CantileverResult(
        moment_of_inertia_mm4=inertia,
        fixed_end_moment_Nmm=moment,
        sigma_max_MPa=sigma_max,
        tip_deflection_mm=tip_deflection,
    )
