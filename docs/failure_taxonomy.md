# Failure Taxonomy

This document defines the first failure modes MechAudit should detect in
LLM-generated mechanical engineering calculations. The taxonomy is benchmark-led:
case files define expected future verifier behavior before verifier code exists.

## Failure Mode Format

Each failure mode includes a definition, detection method, required schema
fields, tolerance behavior, examples, and known limitations.

## FM-01: Unit Conversion or Dimensional Inconsistency

### Definition

The LLM combines incompatible units, converts units incorrectly, or reports an
output whose dimensions do not match the requested engineering quantity.

### Detection Method

1. Parse input and output values with units.
2. Parse the stated formula and variable mapping.
3. Check dimensional compatibility.
4. Convert compatible units to the case canonical unit system.
5. Recompute the stated output.
6. Flag `FM-01` when dimensions are incompatible or unit conversion changes the
   result beyond the case tolerance.

### Required Schema Fields

- `inputs[].value`
- `inputs[].unit`
- `outputs[].value`
- `outputs[].unit`
- `formulas_used[].equation`
- `units.system`
- `tolerance`

### Tolerance

Numerical unit-conversion checks use the tolerance policy in
`docs/tolerance_policy.md`. Dimensional incompatibility always fails and has no
tolerance.

### Positive Example

`F = 10 kN`, `A = 50 mm^2`, and `sigma = F / A`. If the LLM reports
`sigma = 0.2 MPa`, the verifier should recompute `200 MPa` and flag `FM-01`.

### Negative Example

With the same inputs, `sigma = 200 MPa` is unit-consistent and should not flag
`FM-01`.

### Known Limitations

- Requires explicit units.
- V1 should not infer omitted units from prose.
- Gauge versus absolute pressure should be treated as an assumption issue unless
  the response explicitly states the basis.

## FM-02A: Wrong Governing Formula

### Definition

The LLM uses a formula that does not govern the requested quantity or physical
case. The arithmetic may be internally consistent, but the selected engineering
model is wrong.

### Detection Method

1. Parse the requested quantity and problem class from the benchmark case.
2. Parse the formula purpose and equation from `formulas_used`.
3. Compare the formula family against `expected_result.method`.
4. Flag `FM-02A` when the formula computes the wrong quantity or applies the
   wrong governing relation.

### Required Schema Fields

- `problem_statement`
- `expected_result.method`
- `expected_result.required_assumptions`
- `formulas_used[].equation`
- `formulas_used[].purpose`
- `failure_modes`

### Tolerance

Formula selection is categorical. Numeric tolerance does not apply.

### Positive Example

For hoop stress in a thin-walled cylindrical pressure vessel, using
`sigma = p r / (2 t)` should flag `FM-02A` because that is the longitudinal
stress relation, not the hoop stress relation.

### Negative Example

For longitudinal stress in a closed-end thin-walled cylindrical pressure vessel,
`sigma = p r / (2 t)` should not flag `FM-02A`.

### Known Limitations

- Requires the benchmark case to declare the expected method.
- V1 checks against the expected formula for the benchmark, not universal
  formula correctness.

## FM-02B: Missing or Invalid Assumption

### Definition

The LLM relies on a formula or simplification without stating the assumptions
needed for that method, or states an assumption that is invalid for the problem
conditions.

### Detection Method

1. Parse required assumptions from `expected_result.required_assumptions`.
2. Parse assumptions stated by the LLM from `notes.assumptions_stated`.
3. Compare stated assumptions against required assumptions.
4. Flag `FM-02B` when required assumptions are missing, contradicted, or invalid
   for the stated inputs.

### Required Schema Fields

- `problem_statement`
- `expected_result.required_assumptions`
- `notes.assumptions_stated`
- `inputs`
- `formulas_used[].purpose`

### Tolerance

Assumption validity is categorical. Numeric tolerance does not apply, except
when an assumption is tied to a numerical threshold such as thin-wall ratio.

### Positive Example

For a pressure vessel with radius `r = 50 mm` and wall thickness `t = 20 mm`, an
LLM that applies thin-wall formulas and states "thin-walled because t is small"
should flag `FM-02B`, because `r / t = 2.5` is outside the typical thin-wall
range.

### Negative Example

For `r = 50 mm` and `t = 3 mm`, stating the thin-wall assumption is acceptable
for this benchmark and should not flag `FM-02B`.

### Known Limitations

- V1 should use benchmark-declared assumptions rather than trying to infer all
  valid engineering models.
- Ambiguous problem statements should be marked as benchmark-quality issues.

## FM-07: Correct Answer, Incorrect Reasoning

### Definition

The LLM produces a final answer that is numerically correct within tolerance, but
the stated formulas, substitutions, or intermediate calculations would produce a
different value if executed faithfully.

### Detection Method

1. Parse formulas from `formulas_used`.
2. Parse input values and units from `inputs`.
3. Recompute intermediate and final outputs.
4. Compare recomputed values against LLM-stated outputs.
5. Separately compare the final answer against `expected_result`.
6. Flag `FM-07` when the final answer is correct but the stated reasoning is not
   reproducible.

### Required Schema Fields

- `formulas_used[].equation`
- `formulas_used[].variables`
- `inputs`
- `outputs`
- `expected_result`
- `tolerance`

### Tolerance

Use the numeric tolerance policy in `docs/tolerance_policy.md`. The default
relative tolerance is `0.5%`.

### Positive Example

If an LLM states `sigma_h = p r / t`, gives `p = 1.2 MPa`, `r = 50 mm`,
`t = 3 mm`, writes an intermediate value of `25 MPa`, but concludes with the
correct final answer `20 MPa`, the verifier should flag `FM-07`.

### Negative Example

If the same formula and inputs produce stated intermediate and final values of
`20 MPa`, the verifier should not flag `FM-07`.

### Known Limitations

- Requires explicit, parseable formulas.
- Does not inspect hidden reasoning absent from the structured case data.
- V1 should focus on algebraic expressions before table-based or iterative
  methods.

## FM-03: Arithmetic or Substitution Error

### Definition

The LLM selects the correct governing formula and states the relevant inputs, but
performs arithmetic or substitution incorrectly. Unlike `FM-07`, the incorrect
arithmetic propagates to the final reported answer.

### Detection Method

1. Identify the canonical `formula_id` for the stated calculation.
2. Recompute the quantity from the stated inputs.
3. Compare the recomputed value with the LLM-reported final output.
4. Flag `FM-03` when the formula is appropriate but the reported final value
   differs beyond tolerance.

### Required Schema Fields

- `formulas_used[].formula_id`
- `inputs`
- `outputs`
- `expected_result`
- `tolerance`

### Tolerance

Use the numeric tolerance policy in `docs/tolerance_policy.md`. The default
relative tolerance is `0.5%`.

### Positive Example

For `sigma_h = p r / t`, `p = 1.2 MPa`, `r = 50 mm`, and `t = 3 mm`, reporting
`25 MPa` should flag `FM-03` because the recomputed value is `20 MPa`.

### Negative Example

Reporting `20 MPa` for the same formula and inputs should not flag `FM-03`.

## P-01: Schema Noncompliance

### Definition

The response or benchmark case cannot be parsed into the required schema. This
is a parsing-layer failure, not an engineering failure mode.

### Detection Method

1. Parse the embedded metadata block or model output schema.
2. Validate required fields and primitive types.
3. Validate required nested structures.
4. Report missing or malformed fields as `P-01`.

### Expected Behavior

The future verifier should fail gracefully with a diagnostic report and skip
engineering checks when schema data is invalid.

## Compatibility Note

The legacy label `FM-02` has been split into `FM-02A` for wrong governing formula
and `FM-02B` for missing or invalid assumption. New benchmark cases should not
use unsuffixed `FM-02`.
