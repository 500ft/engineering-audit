# Real-Case Classification Rubric

Use this lightweight rubric when converting pending real LLM pressure-vessel
captures into completed benchmark cases. Store the raw model response; do not
summarize it as a substitute for the original output.

## Labels

- `FM-01`: Unit conversion or dimensional inconsistency. Use when the response
  mixes incompatible units or reports a value that does not follow after unit
  conversion.
- `FM-02A`: Wrong governing formula. Use when the response applies the
  longitudinal stress equation to hoop stress, uses a formula for the wrong
  requested quantity, or otherwise selects the wrong governing relation.
- `FM-02B`: Missing or invalid assumption. Use when the response relies on a
  thin-wall assumption without stating it, contradicts the stated geometry, or
  applies thin-wall equations when the benchmark geometry is outside
  applicability.
- `FM-03`: Arithmetic or substitution error. Use when the formula choice is
  appropriate but the final reported number does not follow from the stated
  inputs.
- `FM-07`: Correct answer, incorrect reasoning. Use when the final answer is
  correct but an intermediate formula, substitution, or stated calculation is not
  reproducible.
- No detected failure: Use when the response states valid assumptions, uses the
  correct formulas, performs arithmetic within tolerance, and reports clear
  units.

## `P-01` Boundary

Natural-language LLM output is not `P-01` by itself. Use `P-01` only when
MechAudit benchmark metadata is malformed, required structured extraction fails,
or the verifier cannot parse required case data.

## Manual Review Notes

For each completed real case, record the model name, model version if visible,
run date, temperature/settings if known, raw prompt, raw response, assigned
failure modes, and expected verifier behavior.
