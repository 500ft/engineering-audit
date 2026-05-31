# Real-World Benchmark Case Template

Use this template only for transcript-backed cases from actual engineering work.
Do not claim a case is real-world unless the prompt, LLM response, and trusted
correction are available.

## Metadata

- Case ID:
- Schema version: `0.2.0`
- Source type: `real_world`
- Status: `pending_capture` or `complete`
- Course or project context:
- Date of LLM interaction:
- Model name:
- Model version:
- Prompt ID:
- Temperature:
- Anonymization notes:

```json
{
  "case_id": "",
  "schema_version": "0.2.0",
  "source_type": "real_world",
  "status": "pending_capture",
  "source": {
    "kind": "manual_model_run",
    "description": "",
    "raw_output_available": false
  },
  "model_name": null,
  "model_version": null,
  "run_date": null,
  "prompt_id": "pressure_vessel_prompt_v1",
  "temperature": null,
  "run_settings": {},
  "problem_statement": "",
  "llm_response": {
    "prompt": "prompts/pressure_vessel_prompt_v1.md",
    "response": ""
  },
  "expected_result": {
    "value": null,
    "unit": null,
    "method": "",
    "required_assumptions": []
  },
  "failure_modes": [],
  "formulas_used": [],
  "inputs": [],
  "outputs": [],
  "units": {
    "system": "SI",
    "canonical_outputs": {}
  },
  "tolerance": {
    "relative": 0.005,
    "absolute": null,
    "policy": "docs/tolerance_policy.md"
  },
  "notes": {
    "assumptions_stated": [],
    "limitations": ["Pending raw model output."],
    "reviewer_notes": "",
    "expected_verifier_behavior": "Pending classification after raw output is captured."
  }
}
```

## Original Engineering Problem

```text
Paste the original problem statement here.
```

## LLM Prompt

```text
Paste the exact prompt sent to the LLM here.
```

## LLM Response

```text
Paste the exact LLM response here.
```

## Trusted Expected Result

```text
Show the trusted solution, reference answer, or manually verified result here.
```

## Classified Failure Modes

- `FM-XX`:

## Expected Future Verifier Behavior

Describe what the verifier should flag, what it should ignore, and what report
message would make the issue clear to a human reviewer.

## Inputs

| Name | Symbol | Value | Unit |
|---|---:|---:|---|
|  |  |  |  |

## Outputs

| Name | Symbol | Value | Unit | Source |
|---|---:|---:|---|---|
|  |  |  |  |  |

## Notes

- Assumptions stated by LLM:
- Assumptions required by trusted method:
- Limitations:
- Reviewer notes:
