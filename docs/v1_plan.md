# MechAudit v1 Credibility Plan

Date: 2026-06-21
Schedule: 2026-06-22 through 2026-07-31
Assumption: one primary engineer

## Objective

Ship a defensible v1 of MechAudit that demonstrates transparent, reproducible
failure detection on genuine model outputs within its stated scope: thin-wall
pressure-vessel and axial-stress calculations.

The current verifier has a working CLI, CI, 24 tests, convention-aware
pressure-vessel calculations, five synthetic failure cases, and three
reviewer-synthesized correct controls. The main remaining risk is evidence
quality: the repository does not yet contain verbatim real-model transcripts or
an example of the verifier detecting a genuine model failure.

## Credibility risks to retire

1. The existing completed "real" fixtures are reviewer synthesis rather than
   raw model output.
2. The verifier has not yet demonstrated detection of a genuine model failure.
3. Broad percentage claims would be misleading for the current small,
   correlated benchmark.

## Week 1: Provenance and schema enforcement

**Dates:** June 22-26

- Spend no more than two days reconfirming the baseline: install test
  dependencies, run all tests, verify the CLI, and confirm CI.
- Add `docs/capture_provenance.md` with these provenance tiers:
  - **Gold:** verbatim API response plus provider model/version/date and run
    settings.
  - **Silver:** verbatim UI transcript plus timestamped screenshot and
    self-reported model metadata.
  - **Deprecated:** reviewer synthesis retained only as a reference control.
- Model provenance as validated data rather than unvalidated extra metadata.
  Add a `SourceRecord` containing:
  - capture kind and protocol (`standard`, `challenge`, or `organic`);
  - `raw_output_available`;
  - `provenance_tier`;
  - `raw_artifact_path` and `raw_artifact_sha256`;
  - provider, model/version, date, and run settings.
- Keep benchmark lifecycle status separate from provenance. Reclassify the
  three reviewer-synthesized controls as:
  - `status: complete`;
  - `source_type: reference_correct`;
  - `provenance_tier: deprecated`;
  - `source.kind: reviewer_synthesis`.
- Require a complete `real_world` case to use Gold or Silver provenance, point
  to an existing raw artifact, and match its recorded hash. A pending capture
  may omit the artifact.
- Rewrite README wording so reviewer synthesis is not presented as a real
  capture.
- Start real-model capture work while the schema changes are being completed.

**Exit tests**

- The test suite and CLI pass locally and in CI.
- A complete `real_world` case without a valid raw artifact fails with `P-01`.
- The three synthesized controls remain executable but are no longer counted as
  real-world evidence.

**Risk retired:** synthesized evidence can no longer silently masquerade as a
real capture.

## Week 2: Genuine captures, including failures

**Dates:** June 29-July 3

- Pre-register the exact prompts, model identifiers, settings, run counts, and
  classification procedure before capture.
- Capture the two pending GPT runs with verbatim raw artifacts.
- Re-run Claude and Gemini to replace or supplement synthesized fixtures with
  genuine transcripts.
- Retain every registered run, including correct answers, to avoid selecting
  only outputs that support the project claim.
- Run separately identified challenge prompts designed to expose:
  - mixed-unit errors;
  - thin-wall applicability errors;
  - formula-selection traps;
  - inconsistent substitution and final answers.
- Preserve the distinction between organic, standard, and deliberately
  elicited challenge failures in all reporting.
- Do not add thick-wall or open-end numeric claims until the verifier implements
  the required governing physics. Applicability-only cases may be used if
  labeled accordingly.
- Allow genuine captures to carry multiple failure modes.

**Exit tests**

- At least five Gold or Silver captures have immutable raw artifacts in the
  repository.
- At least two captures contain genuine model failures detected by MechAudit.
- `tests/test_real_world_cases.py` asserts the reviewed expected modes.
- If the fixed protocol produces no failures, publish that result as controls
  rather than modifying prompts after seeing the output.

**Risks retired:** the benchmark contains genuine model evidence and the
verifier has demonstrated detection outside author-created synthetic failures.

## Week 3: Mode-structured benchmark expansion

**Dates:** July 6-10

- Build at least four positive benchmark instances for each implemented mode:
  `FM-01`, `FM-02A`, `FM-02B`, `FM-03`, and `FM-07`.
- Add at least eight correct controls, including:
  - inner-radius versus mean-radius convention handling;
  - valid mixed-unit calculations;
  - assumption and boundary controls supported by the implemented physics.
- Target at least 28 complete cases overall.
- Use synthetic cases for isolated single-mode tests. Do not force genuine
  multi-error responses into single-label fixtures.
- Require every expected result to be independently recomputable from its
  inputs. Record the derivation or review evidence separately from the verifier
  implementation.
- Add cases before changing detection logic.

**Exit tests**

- At least 28 complete cases load successfully.
- Each synthetic positive has a reviewed intended mode.
- Genuine cases retain all applicable labels.
- Every control has an empty expected failure-mode set.

**Risk retired:** evaluation has explicit, countable denominators instead of an
unsupported percentage claim.

## Week 4: Close verifier gaps

**Dates:** July 13-17

Do not expand the case quota this week. Fix only gaps exposed by the frozen
Week-3 benchmark.

Priority gaps already visible in the current implementation:

- Convert reported output units before comparing values; current comparisons
  treat output magnitudes as MPa regardless of `output.unit`.
- Detect a required but omitted assumption, not only an explicitly stated
  invalid thin-wall assumption.
- Strengthen `FM-02A` beyond narrowly authored formula identifiers where the
  structured schema provides enough evidence.
- Improve `P-01` diagnostics and cross-field schema validation.
- Keep thick-wall Lamé stress and open-end vessel calculations out of the
  supported set unless their governing models and tests are implemented.

**Exit tests**

- Report detection counts per mode, for example `FM-03: 4/4`.
- Detect every frozen positive benchmark instance.
- Produce zero false positives across the frozen control set.
- Mutation tests continue to demonstrate that results are computed rather than
  copied from expected labels.

**Risk retired:** the verifier demonstrates repeatable behavior across the
supported family rather than only the original examples.

## Week 5: Productize benchmark evaluation

**Dates:** July 20-24

- Add a batch command:

  ```text
  mechaudit eval benchmark/ --report out/
  ```

- Emit aggregate Markdown and JSON reports containing:
  - per-mode detected/annotated counts;
  - control false-positive counts;
  - results grouped by provenance tier and capture protocol;
  - skipped and malformed-case counts;
  - the benchmark commit hash.
- Return a nonzero exit code when a positive is missed, a control is falsely
  flagged, or a case violates the schema.
- Emit a diagnostic report for `P-01` cases rather than only printing a CLI
  error.
- Run the batch evaluation in CI.

**Exit test:** one command evaluates the complete benchmark, creates both report
formats, and gates CI on regressions.

## Week 6: Independent review and release

**Dates:** July 27-31

- Have someone who did not author the detector or annotations independently
  recompute at least one case per failure mode and two correct controls.
- Record review outcomes and resolve disagreements without changing tolerance
  or accepted conventions merely to avoid a failure.
- Add `LIMITATIONS.md` stating that v1:
  - covers a narrow pressure-vessel and axial-stress family;
  - reports benchmark detection counts, not general model accuracy;
  - does not inspect hidden chain-of-thought;
  - does not provide engineering certification;
  - does not yet perform broad code or standards compliance.
- Update the package version to `1.0.0`.
- Reproduce the batch evaluation in CI and tag `v1.0.0`.

**Exit test:** the tagged release contains traceable evidence, count-based
metrics, explicit limitations, and a reproducible CI evaluation.

## Definition of done

- At least five Gold or Silver raw captures are stored with verified hashes.
- At least two genuine model failures are detected and preserved with raw
  output.
- At least 28 complete benchmark cases exist: at least four positives for each
  of five modes and at least eight controls.
- Results are reported as detected/annotated counts per mode, not bare
  percentages.
- The frozen control set has zero false positives.
- `mechaudit eval benchmark/` is reproducible and CI-gated.
- `LIMITATIONS.md` scopes all claims to the implemented engineering family.
- No reviewer-synthesized fixture is labeled as real-world evidence.

## Defensibility matrix

| Reviewer objection | v1 evidence |
|---|---|
| "The real data is fabricated." | Verbatim raw artifacts, validated provenance, hashes, and synthesis reclassified as reference controls. |
| "It has never caught a real failure." | At least two genuine failure captures with raw output and verifier findings. |
| "What is the denominator?" | Per-mode detected/annotated counts and explicit control counts. |
| "It only handles one formula family." | `LIMITATIONS.md` scopes claims to supported pressure-vessel and axial-stress calculations. |
| "How can the recomputation be trusted?" | Independent review plus mutation tests showing detection is computed rather than label-driven. |

## Post-v1 queue

1. Raw-response-to-schema extraction with mandatory human review.
2. Automated provider capture using a pre-registered run protocol.
3. A second engineering domain selected from observed demand.
4. Historical benchmark comparisons and richer regression reporting.
5. Packaging and installation improvements.
6. FEA-class verifier coverage (no closed-form oracle): mesh-independence
   sanity, boundary-condition plausibility, and load-path/unit consistency,
   backed by author-built CAD/FEA ground-truth cases. See ROADMAP.md,
   "CAD/FEA-validated ground truth".

## Trigger-gated work

- **Second engineering domain:** consider only after all positives are detected
  across at least four reviewed cases per mode with zero control false
  positives.
- **Web UI:** consider when at least five nontechnical evaluators are blocked by
  the CLI.
- **Provider API automation:** consider when manual capture consumes more than
  two hours per evaluation cycle.
- **Engineering-code compliance:** consider only when a specific standard,
  licensed source material, and a traceable rule model are available.
- **Persistent database:** consider when the corpus exceeds roughly 500 cases
  or concurrent editing becomes a measurable problem.

## Explicitly out of scope

- Validation of hidden chain-of-thought.
- Claims of general mechanical-engineering accuracy from this benchmark.
- Replacement of professional engineering review or certification.
- Expansion into unsupported physics solely to increase benchmark size.
