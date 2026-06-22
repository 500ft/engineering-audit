# syn-arith-0001: Arithmetic Substitution Error

```json
{
  "case_id": "syn-arith-0001",
  "schema_version": "0.3.0",
  "source_type": "synthetic",
  "status": "complete",
  "source": {"kind": "synthetic", "description": "Synthetic arithmetic error case.", "provenance_tier": "synthetic", "raw_output_available": true, "model_name": null, "model_version": null, "run_date": null, "temperature": null, "run_settings": {}},
  "prompt_id": "synthetic_pressure_vessel_arithmetic",
  "problem_statement": "Find hoop stress in a thin-walled cylindrical pressure vessel with p = 1.2 MPa, r = 50 mm, t = 3 mm, and yield strength S_y = 120 MPa.",
  "llm_response": {
    "prompt": "Find hoop stress and show arithmetic.",
    "response": "sigma_h = p r / t = 1.2 * 50 / 3 = 25 MPa. The hoop stress is 25 MPa."
  },
  "expected_result": {"value": 20, "unit": "MPa", "method": "sigma_h = p r / t = 1.2 * 50 / 3 = 20 MPa.", "required_assumptions": ["thin-walled cylinder", "internal pressure", "hoop stress requested"]},
  "failure_modes": ["FM-03"],
  "formulas_used": [{"id": "eq1", "formula_id": "hoop_stress_thin_wall", "equation": "sigma_h = p * r / t", "purpose": "Compute hoop stress", "variables": {"sigma_h": "hoop_stress", "p": "pressure", "r": "radius", "t": "thickness"}}],
  "inputs": {
    "pressure": {"value": 1.2, "unit": "MPa"},
    "radius": {"value": 50, "unit": "mm"},
    "thickness": {"value": 3, "unit": "mm"},
    "yield_strength": {"value": 120, "unit": "MPa"}
  },
  "outputs": [
    {"name": "hoop_stress", "symbol": "sigma_h", "value": 25, "unit": "MPa", "source": "llm"},
    {"name": "hoop_stress", "symbol": "sigma_h", "value": 20, "unit": "MPa", "source": "expected"}
  ],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md"},
  "notes": {
    "assumptions_stated": ["thin-walled cylinder"],
    "limitations": ["Synthetic case."],
    "reviewer_notes": "Formula choice is correct, but substitution arithmetic is wrong.",
    "expected_verifier_behavior": "Flag FM-03 because the correct formula recomputes to 20 MPa, not the reported final 25 MPa."
  }
}
```

## Expected Future Verifier Behavior

Recompute the formula and flag `FM-03` for the arithmetic mismatch.
