# rw-pressure-vessel-claude-0001: Claude Pressure-Vessel Capture

```json
{
  "case_id": "rw-pressure-vessel-claude-0001",
  "schema_version": "0.3.0",
  "source_type": "reference_correct",
  "status": "complete",
  "source": {
    "kind": "reviewer_synthesis",
    "description": "Reviewer-synthesized description of a Claude plain pressure-vessel run. Not a verbatim capture.",
    "provenance_tier": "deprecated",
    "raw_output_available": false,
    "model_name": "Claude",
    "model_version": "claude-opus-4-8",
    "run_date": "2026-06-05",
    "temperature": null,
    "reasoning_effort": "High",
    "run_settings": {"reasoning_effort": "High"},
    "metadata_source": "self_report"
  },
  "prompt_id": "pressure_vessel_prompt_v1",
  "problem_statement": "See prompts/pressure_vessel_prompt_v1.md.",
  "llm_response": {
    "prompt": "prompts/pressure_vessel_prompt_v1.md",
    "response": "Reviewer-provided capture synthesis: Claude Opus 4.8 High solved the canonical pressure-vessel prompt cleanly. It reported hoop stress = 1.2 * 50 / 3 = 20.0 MPa and longitudinal stress = 1.2 * 50 / (2 * 3) = 10.0 MPa. It also reported a mean-radius refinement using r_m = 51.5 mm: hoop = 20.6 MPa and longitudinal = 10.3 MPa, noting the refinement changes the result by about 3%. Reviewer recomputation found no unit, formula, arithmetic, assumption, or reasoning failure."
  },
  "expected_result": {
    "value": null,
    "unit": null,
    "method": "Closed-end thin-walled cylinder with accepted inner-radius and mean-radius convention values.",
    "required_assumptions": ["thin-walled cylinder", "closed-end vessel", "internal pressure", "inner radius convention", "mean radius refinement"]
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
    {"name": "hoop_stress_mean_refinement", "symbol": "sigma_h", "value": 20.6, "unit": "MPa", "source": "llm", "convention": "mean_radius"},
    {"name": "longitudinal_stress_mean_refinement", "symbol": "sigma_l", "value": 10.3, "unit": "MPa", "source": "llm", "convention": "mean_radius"},
    {"name": "hoop_stress", "symbol": "sigma_h", "value": 20.0, "unit": "MPa", "source": "expected", "convention": "inner_radius"},
    {"name": "longitudinal_stress", "symbol": "sigma_l", "value": 10.0, "unit": "MPa", "source": "expected", "convention": "inner_radius"}
  ],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md", "accepted_conventions": ["inner_radius", "mean_radius"]},
  "notes": {
    "assumptions_stated": ["thin-walled cylinder", "closed-end vessel", "internal pressure", "mean-radius refinement"],
    "limitations": ["Raw transcript is not present in the repository; this fixture is populated from reviewer-provided capture synthesis.", "No-failure real capture used as a false-positive control.", "Model version, run date, and reasoning effort are recorded from self-reported or UI-level context rather than provider API metadata."],
    "reviewer_notes": "Reviewer independently recomputed inner-radius hoop = 20.0 MPa, inner-radius longitudinal = 10.0 MPa, mean-radius hoop = 20.6 MPa, and mean-radius longitudinal = 10.3 MPa. Claude reported run date 2026-06-05; reviewer notes actual/session date 2026-06-08. No failures were observed.",
    "expected_verifier_behavior": "Detect no failure modes. The mean-radius refinement must not trigger FM-03 because this case explicitly accepts both inner_radius and mean_radius conventions."
  }
}
```

## Classification

This is a reviewer-synthesized control (`provenance_tier: deprecated`), not a
verbatim capture. It is retained as a no-failure false-positive control and
preserves the 20.0 MPa versus 20.6 MPa convention trap.
