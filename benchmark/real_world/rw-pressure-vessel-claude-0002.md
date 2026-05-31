# rw-pressure-vessel-claude-0002: Claude Pressure-Vessel Capture Slot

```json
{
  "case_id": "rw-pressure-vessel-claude-0002",
  "schema_version": "0.2.0",
  "source_type": "real_world",
  "status": "pending_capture",
  "source": {"kind": "manual_model_run", "description": "Second pending Claude run using pressure_vessel_prompt_v1.", "raw_output_available": false},
  "model_name": "Claude",
  "model_version": null,
  "run_date": null,
  "prompt_id": "pressure_vessel_prompt_v1",
  "temperature": null,
  "run_settings": {},
  "problem_statement": "See prompts/pressure_vessel_prompt_v1.md.",
  "llm_response": {"prompt": "prompts/pressure_vessel_prompt_v1.md", "response": ""},
  "expected_result": {"value": null, "unit": null, "method": "Manual classification after raw output capture.", "required_assumptions": ["thin-walled cylinder", "closed-end vessel", "internal pressure"]},
  "failure_modes": [],
  "formulas_used": [],
  "inputs": [
    {"name": "pressure", "symbol": "p", "value": 1.2, "unit": "MPa"},
    {"name": "radius", "symbol": "r", "value": 50, "unit": "mm"},
    {"name": "wall_thickness", "symbol": "t", "value": 3, "unit": "mm"}
  ],
  "outputs": [],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md"},
  "notes": {"assumptions_stated": [], "limitations": ["Pending raw model output."], "reviewer_notes": "", "expected_verifier_behavior": "Pending classification after Claude output is captured."}
}
```

## Run Instructions

Run the canonical prompt in a separate Claude session from
`rw-pressure-vessel-claude-0001` and paste the raw response here.
