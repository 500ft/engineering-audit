# syn-kt-hole-0001: Stress Concentration at a Hole (analytically-validated ground truth)

**This is a synthetic, analytically/FEA-grade-validated GROUND-TRUTH control —
NOT a wild model capture.** The correct answer is computed independently in-repo
by `mechaudit.stress_concentration.plate_with_hole`, whose Kt correlation is the
Heywood/Howland fit to Peterson's chart (Pilkey, *Peterson's Stress Concentration
Factors*, Chart 4.1, flat tension bar with a transverse hole; same fit in Roark,
Table 17.1). The fit is validated by its d/W -> 0 limit recovering the Kirsch
infinite-plate value Kt = 3.0 to within ~0.4% (the fit's limit is 3.004). See
`tests/test_ground_truth_references.py`.

It is a no-failure positive control: the `llm_response` shown is an *author-written
correct solution* used to exercise false-positive behavior, with
`failure_modes: []`. The capture harness (`mechaudit capture`) and provenance
tiers are reserved for genuine model runs; this case is `provenance_tier:
synthetic` and carries no transcript.

```json
{
  "case_id": "syn-kt-hole-0001",
  "schema_version": "0.3.0",
  "source_type": "synthetic",
  "status": "complete",
  "source": {"kind": "synthetic", "description": "Analytically-validated stress-concentration ground-truth control (Peterson/Heywood Kt for a finite-width plate with a central hole). Not a model run.", "provenance_tier": "synthetic", "raw_output_available": true, "model_name": null, "model_version": null, "run_date": null, "temperature": null, "run_settings": {}},
  "prompt_id": "synthetic_stress_concentration_plate_hole",
  "problem_statement": "A flat steel plate of width W = 80 mm and thickness b = 5 mm has a central transverse circular hole of diameter d = 20 mm and carries an axial tensile force P = 18 kN. Find the peak (maximum) stress at the edge of the hole using the stress-concentration factor.",
  "llm_response": {
    "prompt": "Compute the peak stress at the hole using a stress-concentration factor. Show the net-section nominal stress and Kt.",
    "response": "Net section area A_net = (W - d) b = (80 - 20)(5) = 300 mm^2, so the net-section nominal stress is sigma_net = P / A_net = 18000 / 300 = 60.0 MPa. With d/W = 0.25, the Peterson net-section stress-concentration factor is Kt = 2.432. Therefore the peak stress at the hole edge is sigma_max = Kt * sigma_net = 2.432 * 60.0 = 145.9 MPa."
  },
  "expected_result": {"value": 145.9425, "unit": "MPa", "method": "sigma_max = Kt_net * sigma_net, with Kt_net = 2 + 0.284 s - 0.600 s^2 + 1.32 s^3 (s = 1 - d/W) per Peterson/Heywood (Pilkey Chart 4.1; Roark Table 17.1), and sigma_net = P / ((W - d) b).", "required_assumptions": ["linear-elastic, isotropic material", "central transverse circular hole", "uniaxial far-field tension", "Kt referenced to net-section nominal stress"]},
  "failure_modes": [],
  "formulas_used": [
    {"id": "eq1", "formula_id": "net_section_stress", "equation": "sigma_net = P / ((W - d) * b)", "purpose": "Compute net-section nominal stress", "variables": {"sigma_net": "net_section_stress", "P": "axial_force", "W": "plate_width", "d": "hole_diameter", "b": "thickness"}},
    {"id": "eq2", "formula_id": "stress_concentration_peak", "equation": "sigma_max = Kt_net * sigma_net", "purpose": "Apply stress-concentration factor to net-section stress", "variables": {"sigma_max": "peak_stress", "Kt_net": "stress_concentration_factor", "sigma_net": "net_section_stress"}}
  ],
  "inputs": {
    "plate_width": {"value": 80, "unit": "mm"},
    "hole_diameter": {"value": 20, "unit": "mm"},
    "thickness": {"value": 5, "unit": "mm"},
    "axial_force": {"value": 18, "unit": "kN"},
    "stress_concentration_factor_net": {"value": 2.432375, "unit": "dimensionless"}
  },
  "outputs": [
    {"name": "net_section_stress", "symbol": "sigma_net", "value": 60.0, "unit": "MPa", "source": "llm"},
    {"name": "peak_stress", "symbol": "sigma_max", "value": 145.9, "unit": "MPa", "source": "llm"},
    {"name": "net_section_stress", "symbol": "sigma_net", "value": 60.0, "unit": "MPa", "source": "expected"},
    {"name": "peak_stress", "symbol": "sigma_max", "value": 145.9425, "unit": "MPa", "source": "expected"}
  ],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md"},
  "notes": {
    "assumptions_stated": ["linear-elastic isotropic material", "central transverse circular hole", "uniaxial tension", "Kt referenced to net-section stress"],
    "limitations": ["Synthetic analytically-validated GROUND TRUTH, not a transcript-backed model run.", "Kt is the Heywood/Howland fit to Peterson's chart, valid for 0 < d/W < 1.", "The current verifier has no Kt-specific check; this case loads as a no-failure positive control validating the schema and false-positive behavior."],
    "reviewer_notes": "Reference solution computed in-repo by mechaudit.stress_concentration.plate_with_hole and asserted in tests/test_ground_truth_references.py: d/W = 0.25, Kt_net = 2.432375, sigma_net = 60.0 MPa, sigma_max = 145.9425 MPa. The fit's d/W -> 0 limit gives Kt = 3.004, recovering the Kirsch value 3.0 within ~0.4% and validating the correlation. The author can reproduce this peak stress with an FEA model of the holed plate.",
    "expected_verifier_behavior": "Load the case under schema 0.3.0 and detect no failure modes. The reported 145.9 MPa is within tolerance of the validated 145.9425 MPa. This is a positive/control case, not an elicited failure."
  }
}
```

## Reference Solution (independent, in-repo)

For a finite-width plate with a central transverse hole in axial tension, the
peak stress is `sigma_max = Kt_net * sigma_net` where `sigma_net = P / ((W-d) b)`
and `Kt_net` follows the Peterson/Heywood fit (Pilkey Chart 4.1; Roark
Table 17.1):

```text
s = 1 - d/W = 0.75
Kt_net = 2 + 0.284 s - 0.600 s^2 + 1.32 s^3 = 2.432375
sigma_net = 18000 N / ((80 - 20) mm * 5 mm) = 60.0 MPa
sigma_max = 2.432375 * 60.0 = 145.9425 MPa
```

Validation anchor: as `d/W -> 0`, `Kt_net -> 3.004`, recovering the Kirsch
infinite-plate solution (Kt = 3.0) to within ~0.4%. This and the numbers above
are asserted in `tests/test_ground_truth_references.py`.

## Expected Future Verifier Behavior

Detect no failure modes (correct control). A future Kt-aware check should
recompute `Kt_net` from `d/W`, recompute `sigma_net`, and confirm
`sigma_max = Kt_net * sigma_net` within tolerance.
