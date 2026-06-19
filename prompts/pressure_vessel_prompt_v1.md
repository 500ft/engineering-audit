# pressure_vessel_prompt_v1

Use this prompt unchanged when collecting the Week 1/2 real-run pressure-vessel
outputs.

```text
You are solving a mechanical engineering pressure-vessel problem.

Problem:
A closed-end cylindrical pressure vessel has internal pressure p = 1.2 MPa,
inner radius r = 50 mm, and wall thickness t = 3 mm. Calculate the hoop stress
and longitudinal stress in the vessel wall.

Instructions:
1. State any assumptions you use.
2. Write the governing formulas before substituting numbers.
3. Show the unit substitutions.
4. Compute the hoop stress and longitudinal stress.
5. Give the final answers with units.
6. Do not skip intermediate arithmetic.
```

## Prompt v2 Hardening Notes

The first real-run batch was clean on this standard SI problem. Future
failure-eliciting prompts should add difficulty deliberately rather than
changing domains too early:

- mixed or imperial units, such as psi and inches;
- borderline thin-wall ratios around `r / t = 8` to `12`;
- implicit or missing data that forces the model to state assumptions;
- multi-step chains that require a safety decision after recomputation;
- explicit decision language such as "is this safe for material X?".

Do not replace the v1 prompt for comparable GPT/Claude/Gemini capture slots.
Use a new prompt ID for hardened variants.
