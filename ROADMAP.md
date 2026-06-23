# Roadmap — MechAudit

_Last updated: 2026-06-23 · Horizon: 8 weeks (through ~2026-08-23)_

## Role in the portfolio

**Industry / shipping anchor.** A differentiated AI x mechanical-engineering tool
that proves software discipline (CLI, CI, tests, mutation testing) and an unusual
niche. This is the "I ship real software/AI tooling" proof for the part-time
industry track.

## Where it is now

Working verifier that detects errors in LLM-generated engineering calculations
(thin-wall pressure vessel + axial stress): CLI, CI, 24 tests, convention-aware
calculations, synthetic failure cases + reviewer-synthesized controls, mutation
tests proving detection is computed (not label-matched).

## The make-or-break gap

The benchmark is still **synthetic** — the verifier has not yet caught a
**genuine** model failure in the wild with verbatim, provenance-tracked raw
output. Retiring that single credibility risk is the whole game this summer.

## Plan

The detailed week-by-week schedule already lives in
[`docs/v1_plan.md`](docs/v1_plan.md) (June 22 -> July 31) and is the source of
truth. This file is the portfolio-facing summary. Execute v1_plan verbatim. Key
gated outcomes:

- [ ] **Wk 1:** schema 0.3.0 provenance enforcement (Gold/Silver/Deprecated
      tiers; `SourceRecord` with hashes). *Done — merged.*
- [ ] **Wk 2:** >=5 Gold/Silver real captures with immutable hashed artifacts;
      **>=2 genuine detected model failures.** Pre-register prompts/models/runs;
      keep every run including passes.
- [ ] **Wk 3:** mode-structured benchmark — >=28 complete cases (>=4 positives x
      5 modes + >=8 controls); count-based denominators, not bare percentages.
- [ ] **Wk 4:** close verifier gaps exposed by the frozen benchmark (unit
      conversion before comparison; omitted-assumption detection; `P-01`
      diagnostics).
- [ ] **Wk 5:** `mechaudit eval benchmark/ --report out/` batch command, CI-gated
      on regressions.
- [ ] **Wk 6:** independent recompute review + `LIMITATIONS.md`; tag **v1.0.0**.

## CAD/FEA-validated ground truth (additive)

This does **not** change the make-or-break priority — capturing >=2 genuine wild
model failures with provenance-tracked, hashed raw artifacts is still the whole
game. It only strengthens the ground truth those failures are judged against.
The author can do CAD and FEA, which is used to:

- **Harden the Wk-3 mode-structured benchmark.** Author harder ground-truth
  cases whose correct answer is confirmed by an FEA model — stress
  concentration, beam/plate bending, buckling, contact — beyond the closed-form
  thin-wall/axial family. Lets the benchmark claim that positives and controls
  are validated against FEA, not only hand analytics.
- **Seed a future verifier-coverage expansion.** Scope checks for FEA-class
  problems where no closed-form oracle exists: mesh-independence sanity,
  boundary-condition plausibility, and load-path/unit consistency. Tracked as a
  later coverage item, gated behind the core capture work above.

## Portfolio statement

> Built a reproducible, CI-gated verifier that detects errors in LLM-generated
> engineering calculations, with provenance-tracked real-model failure captures
> (hashed raw artifacts) and mutation-tested detection logic; released v1.0.0
> with explicit scope limitations.
