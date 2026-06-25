# syn-cantilever-0001: End-Loaded Cantilever Bending (analytically-validated ground truth)

**This is a synthetic, analytically/FEA-grade-validated GROUND-TRUTH control —
NOT a wild model capture.** The correct answer is computed independently in-repo
by `mechaudit.stress_concentration.end_loaded_cantilever` (Euler-Bernoulli;
Roark Table 8.1 case 1; Gere & Goodno). The tip deflection is additionally
cross-checked by numerical double-integration of the curvature in
`tests/test_ground_truth_references.py` (relative error ~1e-12).

It is a no-failure positive control: the `llm_response` is an *author-written
correct solution* with `failure_modes: []`, used to exercise false-positive
behavior. It is `provenance_tier: synthetic` and carries no transcript; the
capture harness and gold/silver tiers are reserved for genuine model runs.

```json
{
  "case_id": "syn-cantilever-0001",
  "schema_version": "0.3.0",
  "source_type": "synthetic",
  "status": "complete",
  "source": {"kind": "synthetic", "description": "Analytically-validated cantilever-bending ground-truth control (Euler-Bernoulli end-loaded rectangular cantilever). Not a model run.", "provenance_tier": "synthetic", "raw_output_available": true, "model_name": null, "model_version": null, "run_date": null, "temperature": null, "run_settings": {}},
  "prompt_id": "synthetic_cantilever_end_load",
  "problem_statement": "A rectangular steel cantilever (width b = 20 mm, height h = 10 mm, length L = 300 mm, E = 200 GPa) carries a transverse point load P = 500 N at its free end. Find the maximum bending stress at the fixed end and the tip deflection.",
  "llm_response": {
    "prompt": "Find the maximum bending stress and tip deflection of the end-loaded cantilever. Show I, the fixed-end moment, and the formulas.",
    "response": "Second moment of area I = b h^3 / 12 = 20 * 10^3 / 12 = 1666.67 mm^4. The bending moment is maximum at the fixed end: M = P L = 500 * 300 = 150000 N*mm. Maximum bending stress sigma_max = M c / I = 150000 * 5 / 1666.67 = 450 MPa (equivalently 6 P L / (b h^2)). Tip deflection delta = P L^3 / (3 E I) = 500 * 300^3 / (3 * 200000 * 1666.67) = 13.5 mm."
  },
  "expected_result": {"value": 450.0, "unit": "MPa", "method": "sigma_max = M c / I = 6 P L / (b h^2) at the fixed end; tip deflection delta = P L^3 / (3 E I), I = b h^3 / 12 (Euler-Bernoulli; Roark Table 8.1 case 1).", "required_assumptions": ["linear-elastic isotropic material", "small deflections (Euler-Bernoulli)", "prismatic rectangular section", "load applied transversely at the free end"]},
  "failure_modes": [],
  "formulas_used": [
    {"id": "eq1", "formula_id": "rectangular_second_moment", "equation": "I = b * h^3 / 12", "purpose": "Second moment of area of a rectangular section", "variables": {"I": "moment_of_inertia", "b": "width", "h": "height"}},
    {"id": "eq2", "formula_id": "cantilever_bending_stress", "equation": "sigma_max = 6 * P * L / (b * h^2)", "purpose": "Maximum bending stress at the fixed end", "variables": {"sigma_max": "bending_stress", "P": "load", "L": "length", "b": "width", "h": "height"}},
    {"id": "eq3", "formula_id": "cantilever_tip_deflection", "equation": "delta = P * L^3 / (3 * E * I)", "purpose": "Tip deflection of an end-loaded cantilever", "variables": {"delta": "tip_deflection", "P": "load", "L": "length", "E": "youngs_modulus", "I": "moment_of_inertia"}}
  ],
  "inputs": {
    "load": {"value": 500, "unit": "N"},
    "length": {"value": 300, "unit": "mm"},
    "width": {"value": 20, "unit": "mm"},
    "height": {"value": 10, "unit": "mm"},
    "youngs_modulus": {"value": 200, "unit": "GPa"}
  },
  "outputs": [
    {"name": "bending_stress", "symbol": "sigma_max", "value": 450.0, "unit": "MPa", "source": "llm"},
    {"name": "tip_deflection", "symbol": "delta", "value": 13.5, "unit": "mm", "source": "llm"},
    {"name": "bending_stress", "symbol": "sigma_max", "value": 450.0, "unit": "MPa", "source": "expected"},
    {"name": "tip_deflection", "symbol": "delta", "value": 13.5, "unit": "mm", "source": "expected"}
  ],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa", "deflection": "mm"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md"},
  "notes": {
    "assumptions_stated": ["linear-elastic isotropic material", "small deflections", "prismatic rectangular section", "end load"],
    "limitations": ["Synthetic analytically-validated GROUND TRUTH, not a transcript-backed model run.", "Euler-Bernoulli theory; shear deformation neglected (L/h = 30, so shear contribution is negligible).", "The current verifier has no cantilever-bending check; this case loads as a no-failure positive control."],
    "reviewer_notes": "Reference solution computed in-repo by mechaudit.stress_concentration.end_loaded_cantilever and asserted in tests/test_ground_truth_references.py: I = 1666.667 mm^4, M_fixed = 150000 N*mm, sigma_max = 450.0 MPa, delta_tip = 13.5 mm. Tip deflection is independently cross-checked by numerical double-integration of curvature (rel err ~6e-12). The author can reproduce both quantities with an FEA beam/solid model.",
    "expected_verifier_behavior": "Load the case under schema 0.3.0 and detect no failure modes. Reported sigma_max = 450 MPa and delta = 13.5 mm both match the validated reference within tolerance. This is a positive/control case, not an elicited failure."
  }
}
```

## Reference Solution (independent, in-repo)

```text
I = b h^3 / 12 = 20 * 10^3 / 12 = 1666.667 mm^4
M_fixed = P L = 500 * 300 = 150000 N*mm
sigma_max = M c / I = 150000 * 5 / 1666.667 = 450.0 MPa  (= 6 P L / (b h^2))
delta_tip = P L^3 / (3 E I) = 500 * 300^3 / (3 * 200000 * 1666.667) = 13.5 mm
```

The tip deflection is cross-checked by numerically integrating the curvature
`v'' = M(x) / (E I)` twice from the fixed end, recovering 13.5 mm to ~1e-12
relative error. All values are asserted in
`tests/test_ground_truth_references.py`.

## Expected Future Verifier Behavior

Detect no failure modes (correct control). A future bending-aware check should
recompute `I`, `sigma_max`, and `delta` from the inputs and confirm the reported
values within tolerance.
