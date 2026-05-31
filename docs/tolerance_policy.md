# Tolerance Policy

This document defines default numeric comparison rules for benchmark cases and
future verifier checks.

## Defaults

- Relative tolerance: `0.005` (`0.5%`)
- Absolute tolerance: case-specific and required when the expected value is near
  zero
- Unit or dimensional incompatibility: always fail, no tolerance
- Formula selection checks: categorical, no numeric tolerance
- Assumption checks: categorical, no numeric tolerance unless the assumption is
  tied to an explicit numerical threshold

## Relative Tolerance

Use relative tolerance when the expected value is safely away from zero:

```text
abs(actual - expected) / abs(expected) <= relative_tolerance
```

The default relative tolerance is intended to absorb normal rounding in
hand-calculation style LLM responses, not incorrect arithmetic.

## Absolute Tolerance

Use absolute tolerance when the expected value is zero or close enough to zero
that relative comparison becomes unstable:

```text
abs(actual - expected) <= absolute_tolerance
```

Benchmark cases must specify the absolute tolerance and unit when they rely on
this comparison.

## Combined Numeric Check

When both tolerances are present, a value passes if either comparison passes:

```text
abs(actual - expected) <= absolute_tolerance
or
abs(actual - expected) / abs(expected) <= relative_tolerance
```

## Unit and Dimension Checks

Dimensional incompatibility is not a rounding problem. A result with incompatible
dimensions should fail even if its number happens to be close to the expected
number.

## Formula and Assumption Checks

`FM-02A` and `FM-02B` are categorical checks. A wrong formula or invalid
assumption should be flagged even when the final number accidentally matches the
expected result.
