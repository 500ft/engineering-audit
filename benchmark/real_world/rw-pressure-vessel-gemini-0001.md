# rw-pressure-vessel-gemini-0001: Gemini Pressure-Vessel Capture

```json
{
  "case_id": "rw-pressure-vessel-gemini-0001",
  "schema_version": "0.2.0",
  "source_type": "real_world",
  "status": "complete",
  "source": {
    "kind": "manual_model_run",
    "description": "Completed Gemini pressure-vessel run classified from reviewer-provided capture synthesis.",
    "raw_output_available": false
  },
  "model_name": "Gemini",
  "model_version": "gemini-3.5-thinking",
  "run_date": "2026-06-05",
  "metadata_source": "self_report",
  "capture_source": "reviewer_synthesis",
  "temperature": null,
  "run_settings": {},
  "prompt_id": "pressure_vessel_prompt_v1",
  "problem_statement": "See prompts/pressure_vessel_prompt_v1.md.",
  "llm_response": {
    "prompt": "prompts/pressure_vessel_prompt_v1.md",
    "response": "Reviewer-provided capture synthesis: Gemini 3.5 Thinking solved the canonical pressure-vessel prompt cleanly. It reported hoop stress = 1.2 * 50 / 3 = 20.0 MPa, longitudinal stress = 1.2 * 50 / (2 * 3) = 10.0 MPa, and r/t = 16.67. Reviewer recomputation found no unit, formula, arithmetic, assumption, or reasoning failure."
  },
  "expected_result": {
    "value": null,
    "unit": null,
    "method": "Closed-end thin-walled cylinder with inner-radius convention: sigma_h = p r / t and sigma_l = p r / (2 t).",
    "required_assumptions": ["thin-walled cylinder", "closed-end vessel", "internal pressure", "inner radius convention"]
  },
  "failure_modes": [],
  "formulas_used": [
    {"id": "eq1", "formula_id": "hoop_stress_thin_wall", "equation": "sigma_h = p * r / t", "purpose": "Compute hoop stress", "variables": {"sigma_h": "hoop_stress", "p": "pressure", "r": "radius", "t": "thickness"}},
    {"id": "eq2", "formula_id": "longitudinal_stress_thin_wall", "equation": "sigma_l = p * r / (2 * t)", "purpose": "Compute longitudinal stress", "variables": {"sigma_l": "longitudinal_stress", "p": "pressure", "r": "radius", "t": "thickness"}}
  ],
  "inputs": {
    "pressure": {"value": 1.2, "unit": "MPa"},
    "radius": {"value": 50, "unit": "mm"},
    "thickness": {"value": 3, "unit": "mm"}
  },
  "outputs": [
    {"name": "hoop_stress", "symbol": "sigma_h", "value": 20.0, "unit": "MPa", "source": "llm", "convention": "inner_radius"},
    {"name": "longitudinal_stress", "symbol": "sigma_l", "value": 10.0, "unit": "MPa", "source": "llm", "convention": "inner_radius"},
    {"name": "hoop_stress", "symbol": "sigma_h", "value": 20.0, "unit": "MPa", "source": "expected", "convention": "inner_radius"},
    {"name": "longitudinal_stress", "symbol": "sigma_l", "value": 10.0, "unit": "MPa", "source": "expected", "convention": "inner_radius"}
  ],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md", "accepted_conventions": ["inner_radius"]},
  "notes": {
    "assumptions_stated": ["thin-walled cylinder", "closed-end vessel", "internal pressure"],
    "limitations": ["Raw transcript is not present in the repository; this fixture is populated from reviewer-provided capture synthesis.", "No-failure real capture used as a false-positive control."],
    "reviewer_notes": "Reviewer independently recomputed hoop = 20.0 MPa, longitudinal = 10.0 MPa, and r/t = 16.67. No failures were observed.",
    "expected_verifier_behavior": "Detect no failure modes and treat the case as a real no-failure control."
  }
}
```

## Classification

This completed real capture is a no-failure control. It exists to prove that the
verifier does not produce false positives on a correct standard SI
pressure-vessel solve.
