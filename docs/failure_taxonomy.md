# Failure Taxonomy

This document defines the first failure modes MechAudit should detect in
LLM-generated mechanical engineering calculations. The taxonomy is written before
verifier code so benchmark cases can define the expected behavior.

## Failure Mode Format

Each failure mode includes:

- Definition: what counts as the failure.
- Detection method: how a verifier could identify it from structured output.
- Required schema fields: data needed to make the check possible.
- Tolerance: numerical threshold for flagging when relevant.
- Positive example: should be flagged.
- Negative example: should pass.
- Known limitations: cases the first verifier should not claim to solve.

## FM-01: Unit Conversion or Dimensional Inconsistency

### Definition

The LLM combines values with incompatible units, converts units incorrectly, or
reports an output whose dimensions do not match the quantity being calculated.
This includes using millimeters as meters, mixing gauge and absolute pressure
without stating the basis, or producing stress in units that are dimensionally
incompatible with force per area.

### Detection Method

1. Parse each stated input value and unit from `inputs`.
2. Parse the stated formula from `formulas_used`.
3. Check that substituted units reduce to the declared output dimension.
4. Convert all compatible units to the canonical unit system for the case.
5. Recompute the output and compare it with the stated output.
6. Flag `FM-01` when unit dimensions are incompatible or when a unit conversion
   changes the result beyond tolerance.

### Required Schema Fields

- `inputs[].name`
- `inputs[].value`
- `inputs[].unit`
- `formulas_used[].equation`
- `outputs[].name`
- `outputs[].value`
- `outputs[].unit`
- `units.system`

### Tolerance

Use a default relative tolerance of `0.5%` for unit-converted recomputation.
Dimensional incompatibility has no tolerance and should always flag.

### Positive Example

Stated formula:

```text
sigma = F / A
```

Stated inputs:

```text
F = 10 kN
A = 50 mm^2
```

Stated output:

```text
sigma = 0.2 MPa
```

Recomputed result:

```text
10 kN / 50 mm^2 = 200 MPa
```

The stated output is off by a factor of 1000, so the verifier should flag
`FM-01`.

### Negative Example

Stated inputs:

```text
F = 10 kN
A = 50 mm^2
```

Stated output:

```text
sigma = 200 MPa
```

The units and value are consistent, so the verifier should not flag `FM-01`.

### Known Limitations

- Requires explicit units for inputs and outputs.
- Does not infer missing units from surrounding prose in V1.
- Does not decide whether an engineering assumption, such as gauge versus
  absolute pressure, is appropriate unless that basis is stated.

## FM-02: Incorrect Formula Selection or Missing Assumption

### Definition

The LLM uses a formula that does not apply to the problem conditions, omits a
necessary assumption, or applies a simplified relation outside its valid range.
The arithmetic may be internally consistent, but the engineering model is wrong
or under-specified.

### Detection Method

1. Parse the problem type and stated assumptions from the case metadata.
2. Parse each formula in `formulas_used`.
3. Compare the formula against the expected formula family for the benchmark
   case.
4. Check whether required assumptions are present, such as thin-wall criteria,
   static loading, linear elasticity, or small deflection.
5. Flag `FM-02` when the formula family is incompatible with the case or when a
   required assumption is missing from the LLM response.

### Required Schema Fields

- `problem_statement`
- `expected_result.method`
- `expected_result.required_assumptions`
- `formulas_used[].equation`
- `formulas_used[].purpose`
- `notes.assumptions_stated`

### Tolerance

Formula selection is categorical. Numerical tolerance does not apply unless the
wrong formula also produces a recomputation mismatch covered by another failure
mode.

### Positive Example

Problem:

```text
Find hoop stress in a thin-walled cylindrical pressure vessel.
```

LLM formula:

```text
sigma = p r / (2 t)
```

Expected formula:

```text
sigma_hoop = p r / t
```

The LLM used the longitudinal stress formula for hoop stress. The verifier should
flag `FM-02`.

### Negative Example

Problem:

```text
Find longitudinal stress in a closed-end thin-walled cylindrical pressure vessel.
```

LLM formula:

```text
sigma_longitudinal = p r / (2 t)
```

The formula matches the requested quantity, so the verifier should not flag
`FM-02`.

### Known Limitations

- Requires benchmark cases to declare the expected formula family.
- Does not prove that a formula is universally correct; it checks against the
  expected method for the case.
- Ambiguous problem statements should be marked as benchmark quality issues
  rather than verifier failures.

## FM-07: Correct Answer, Incorrect Reasoning

### Definition

The LLM produces a final answer that is numerically correct within tolerance, but
the stated chain of reasoning contains formulas, substitutions, or intermediate
calculations that would produce a different result if executed faithfully.

This is a high-priority failure mode because it can make an answer look reliable
even when the reasoning is not reproducible.

### Detection Method

1. Parse stated formulas from `formulas_used`.
2. Parse stated input values and units from `inputs`.
3. Substitute the stated inputs into each relevant equation.
4. Recompute intermediate and final outputs.
5. Compare recomputed values against the LLM-stated values in `outputs`.
6. Separately compare the final answer against `expected_result`.
7. Flag `FM-07` when the final answer is correct but the recomputed reasoning
   does not match the stated intermediate or final values.

### Required Schema Fields

- `formulas_used[].equation`
- `formulas_used[].variables`
- `inputs[].name`
- `inputs[].value`
- `inputs[].unit`
- `outputs[].name`
- `outputs[].value`
- `outputs[].unit`
- `expected_result.value`
- `expected_result.unit`

### Tolerance

Use a default relative tolerance of `0.5%` for recomputation. The tolerance
should eventually be configurable per case because some engineering problems
depend on rounded tabular values.

### Positive Example

Stated formula:

```text
sigma_h = p r / t
```

Stated inputs:

```text
p = 1.2 MPa
r = 50 mm
t = 3 mm
```

Stated output:

```text
sigma_h = 25 MPa
```

Expected final answer:

```text
25 MPa
```

Recomputed from stated reasoning:

```text
1.2 * 50 / 3 = 20 MPa
```

The final answer matches the expected result, but it does not follow from the
stated formula and inputs. The verifier should flag `FM-07`.

### Negative Example

Stated formula:

```text
sigma_h = p r / t
```

Stated inputs:

```text
p = 1.2 MPa
r = 50 mm
t = 3 mm
```

Stated output:

```text
sigma_h = 20 MPa
```

Expected final answer:

```text
20 MPa
```

The reasoning and final answer agree, so the verifier should not flag `FM-07`.

### Known Limitations

- Requires the LLM to state formulas explicitly.
- Requires parseable equations and named variables.
- Does not detect hidden reasoning that is not represented in the structured
  output.
- V1 should focus on algebraic expressions and basic engineering formulas before
  supporting piecewise, iterative, or table-based methods.

## P-01: Schema Noncompliance

### Definition

The LLM response cannot be parsed into the required benchmark or verifier schema.
This is a parsing-layer failure, not an engineering failure mode.

### Detection Method

1. Attempt to parse the structured response.
2. Validate required top-level fields.
3. Validate required nested fields and primitive types.
4. Reject hallucinated schema extensions unless the schema version explicitly
   allows them.
5. Report missing, malformed, or unparseable fields as `P-01`.

### Expected Behavior

V1 should fail gracefully with a diagnostic report instead of attempting an
engineering audit on malformed data.

### Known Limitations

- A schema-compliant response can still contain incorrect engineering.
- A schema-noncompliant response may contain useful prose, but V1 should not rely
  on ad hoc prose extraction.
