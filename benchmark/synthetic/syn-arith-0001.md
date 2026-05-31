# syn-arith-0001: Arithmetic Substitution Error

```json
{
  "case_id": "syn-arith-0001",
  "schema_version": "0.2.0",
  "source_type": "synthetic",
  "status": "complete",
  "source": {"kind": "synthetic", "description": "Synthetic arithmetic error case.", "raw_output_available": true},
  "model_name": null,
  "model_version": null,
  "run_date": null,
  "prompt_id": "synthetic_pressure_vessel_arithmetic",
  "temperature": null,
  "run_settings": {},
  "problem_statement": "Find hoop stress for a thin-walled cylindrical pressure vessel with p = 1.2 MPa, r = 50 mm, and t = 3 mm.",
  "llm_response": {
    "prompt": "Find hoop stress and show arithmetic.",
    "response": "sigma_h = p r / t = 1.2 * 50 / 3 = 25 MPa. The hoop stress is 25 MPa."
  },
  "expected_result": {"value": 20, "unit": "MPa", "method": "sigma_h = p r / t = 1.2 * 50 / 3 = 20 MPa.", "required_assumptions": ["thin-walled cylinder", "internal pressure", "hoop stress requested"]},
  "failure_modes": ["FM-07"],
  "formulas_used": [{"id": "eq1", "equation": "sigma_h = p * r / t", "purpose": "Compute hoop stress", "variables": {"sigma_h": "hoop_stress", "p": "pressure", "r": "radius", "t": "wall_thickness"}}],
  "inputs": [
    {"name": "pressure", "symbol": "p", "value": 1.2, "unit": "MPa"},
    {"name": "radius", "symbol": "r", "value": 50, "unit": "mm"},
    {"name": "wall_thickness", "symbol": "t", "value": 3, "unit": "mm"}
  ],
  "outputs": [
    {"name": "hoop_stress", "symbol": "sigma_h", "value": 25, "unit": "MPa", "source": "llm"},
    {"name": "hoop_stress", "symbol": "sigma_h", "value": 20, "unit": "MPa", "source": "expected"}
  ],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md"},
  "notes": {
    "assumptions_stated": ["thin-walled cylinder"],
    "limitations": ["Synthetic case.", "Arithmetic errors may deserve a future FM-03 label; for this milestone they are grouped under reasoning/recomputation behavior."],
    "reviewer_notes": "Formula choice is correct, but substitution arithmetic is wrong.",
    "expected_verifier_behavior": "Flag the numeric recomputation mismatch; this is currently classified under FM-07-style reasoning consistency until a dedicated arithmetic label exists."
  }
}
```

## Expected Future Verifier Behavior

Recompute the formula and flag the arithmetic mismatch. This file explicitly
notes that a future `FM-03` may be useful for pure arithmetic errors.
