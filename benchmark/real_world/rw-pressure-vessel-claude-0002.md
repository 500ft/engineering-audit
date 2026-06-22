# rw-pressure-vessel-claude-0002: Claude Design-Review Pressure-Vessel Capture

```json
{
  "case_id": "rw-pressure-vessel-claude-0002",
  "schema_version": "0.3.0",
  "source_type": "reference_correct",
  "status": "complete",
  "source": {
    "kind": "reviewer_synthesis",
    "description": "Reviewer-synthesized description of a Claude design-review pressure-vessel run. Not a verbatim capture.",
    "provenance_tier": "deprecated",
    "raw_output_available": false,
    "model_name": "Claude",
    "model_version": "claude-opus-4-8",
    "run_date": "2026-06-05",
    "temperature": null,
    "reasoning_effort": "High",
    "run_settings": {"reasoning_effort": "High", "prompt_condition": "design_review_persona"},
    "metadata_source": "self_report"
  },
  "prompt_id": "pressure_vessel_review_v1",
  "problem_statement": "Canonical pressure-vessel problem with design-review persona added to the prompt condition.",
  "llm_response": {
    "prompt": "prompts/pressure_vessel_prompt_v1.md plus design-review persona instruction.",
    "response": "Reviewer-provided capture synthesis: Claude Opus 4.8 High solved the pressure-vessel prompt cleanly under a design-review persona. It reported hoop stress = 20.0 MPa, longitudinal stress = 10.0 MPa, and the same mean-radius refinement as the plain Claude run: hoop = 20.6 MPa and longitudinal = 10.3 MPa. It additionally produced a self-review that included von Mises stress sqrt(20^2 - 20*10 + 10^2) = 17.3 MPa, a safety factor near 14 using a model-selected 250 MPa yield strength, radial-to-hoop stress ratio 1.2/20 = 6%, ASME-oriented notes, and a self-score of 88/100. Reviewer recomputation found the pressure-vessel solve correct and found no unit, formula, arithmetic, assumption, or reasoning failure. The model self-review is stored as capture evidence only, not verifier ground truth."
  },
  "expected_result": {
    "value": null,
    "unit": null,
    "method": "Closed-end thin-walled cylinder with accepted inner-radius and mean-radius convention values. Design-review self-assessment is not used as expected result ground truth.",
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
    "limitations": ["Raw transcript is not present in the repository; this fixture is populated from reviewer-provided capture synthesis.", "No-failure real capture used as a false-positive control.", "Model self-review is stored only as evidence and is not accepted as verifier ground truth.", "Von Mises and safety-factor checks are intentionally deferred because they require a separate detection rule and material-yield-source policy."],
    "reviewer_notes": "Reviewer independently recomputed inner-radius hoop = 20.0 MPa, inner-radius longitudinal = 10.0 MPa, mean-radius hoop = 20.6 MPa, mean-radius longitudinal = 10.3 MPa, von Mises = 17.3 MPa, SF near 14 given model-selected S_y = 250 MPa, and sigma_r/sigma_h = 6%. Claude reported run date 2026-06-05; reviewer notes actual/session date 2026-06-08. No failures were observed.",
    "expected_verifier_behavior": "Detect no failure modes. Do not ingest the model's self-score or design-review critique as ground truth."
  }
}
```

## Classification

This is a reviewer-synthesized control (`provenance_tier: deprecated`), not a
verbatim capture. It is a no-failure control for the design-review prompt
condition. The self-review narrative is preserved in `llm_response.response` as
evidence only; MechAudit does not use model self-grading as an expected result.
