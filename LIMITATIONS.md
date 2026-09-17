# Limitations

This file states what engineering-audit's current evidence does and does not
support. It exists so that no summary of this project has to guess. Wherever a
claim about engineering-audit is made (README, resume line, talk slide), it
should be checkable against this list.

## 1. The real-world failures are elicited, not found in the wild

The gold captures are verbatim model outputs with hash-verified provenance —
but they were produced by **challenge-protocol prompts written by the operator
and run deliberately** (`capture_protocol: challenge`). No committed case yet
records a failure encountered during someone's real engineering workflow.

- Supported claim: *"engineering-audit detected genuine, reproducible
  calculation failures in unmodified frontier-model outputs, captured under a
  pre-registered protocol with cryptographic provenance."*
- Unsupported claim: *"engineering-audit has caught model failures in the
  wild."*

The gap matters because elicited prompts are chosen where failure is likely;
wild usage samples a different distribution.

## 2. Domain coverage is narrow

Verified failure detection currently covers thin-wall pressure-vessel hoop
stress, axial stress, and finite-width holed-plate stress concentration
(Kt-aware, FM-04). The taxonomy in `docs/failure_taxonomy.md` is much larger
than the implemented checker set. Beam bending, buckling, contact, bolted
joints, and fatigue are scoped but not implemented; claims about "mechanical
engineering calculations" in general are aspirational beyond the three
implemented families.

## 3. Ground truth is closed-form first

Expected results trace to standard closed-form solutions (with the tolerance
policy in `docs/tolerance_policy.md`) and, for stress concentration, to
Peterson/Roark Kt fits validated against the in-repo FEA work. There is no
physical-test ground truth anywhere in the benchmark. Where a problem admits
defensible variant conventions (inner-radius vs mean-radius), the rubric
accepts the variant rather than forcing one number.

## 4. Capture metadata is partly self-reported

Model identity/version in `source.json` is recorded from the serving CLI and
the model's own self-report (`metadata_source: self_report`). Raw output bytes
are hash-verified; the *identity* of the model that produced them relies on
the toolchain being honest. Temperature was not controlled (`temperature:
null`), so per-prompt failure rates are single-draw observations, not
probabilities.

## 5. Sample sizes are small

10 Haiku runs, 20 Codex runs, one prompt battery, one language (English), one
unit system (SI). Per-model comparisons ("model X fails where model Y passes")
are existence results, not statistics.

## 6. The CAD loop builds and measures; it does not yet simulate

`cadloop/` drives a parametric SOLIDWORKS template, gates the result against a
closed-form volume oracle, and exports STEP. The FEA stage is not implemented:
no committed run imports a STEP file into a solver, and no stress or
displacement number in this repository came from that loop.

- Supported claim: *"Parametric CAD builds are produced on a licensed host and
  accepted only when measured mass properties match a closed-form oracle within
  tolerance."*
- Unsupported claim: *"The loop validates designs by FEA"* — and, for now,
  *"the loop re-drives a template to new parameters"*: the oracle gate is in
  place, but no recorded run shows a second parameter set measuring its own
  expected volume. An earlier run reported success while returning the
  template's original volume, which is why the gate exists.

Coverage is one plate fixture in one configuration. The gate constrains volume
only, so a correctly sized feature in the wrong location passes it. Host open
latency is unstable and unexplained (seconds to over thirteen minutes for the
same call), so throughput claims are not supportable. Details and the full
finding list are in [`docs/cad_fea_loop.md`](docs/cad_fea_loop.md) and
[`docs/solidworks_api_findings.md`](docs/solidworks_api_findings.md).

## 7. The verifier is narrow by design

Checks are limited to what is independently recomputable. engineering-audit does
not judge modeling choices, load-case selection, or safety-factor policy — the
places where real engineering judgment lives. A calculation can pass every
engineering-audit check and still be the wrong calculation for the design.
