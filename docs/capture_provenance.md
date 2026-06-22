# Capture Provenance

This document defines how MechAudit records where a benchmark case's model output
came from, and how strongly that origin is evidenced. Provenance is enforced by
the loader as of schema version `0.3.0`; it is not an honor-system annotation.

The goal is narrow and deliberate: a reader must be able to tell, mechanically,
whether a "real" case is backed by a verbatim model artifact or is a reviewer's
reconstruction. Reviewer reconstructions are useful as controls but must never be
presented as real captures.

## Provenance tiers

Every case carries `source.provenance_tier`, one of:

| Tier | Meaning | Raw artifact | Metadata source |
|---|---|---|---|
| `gold` | Verbatim provider API response captured programmatically. | Required: `api_response` (and/or `raw_response`). | `api` — model/version/date/settings from the provider response. |
| `silver` | Verbatim transcript copied from a model UI. | Required: `raw_response` plus a timestamped `screenshot`. | `self_report` — model/version/date from the UI, not the API. |
| `deprecated` | Reviewer synthesis: text written by a reviewer to describe what a model did. Retained only as a reference control. | None. | Not applicable; this is not a capture. |
| `synthetic` | Hand-authored case for isolated single-mode testing. Not a model run. | None. | Not applicable. |

`gold` and `silver` are the only tiers that count as genuine model evidence for
v1. `deprecated` and `synthetic` cases are valid benchmark members but are never
counted as real-world captures in reporting.

## Artifacts

Raw outputs are stored as files and referenced from `source.artifacts`, a typed
list. Each artifact records:

| Field | Type | Description |
|---|---|---|
| `kind` | string | One of `raw_response`, `api_response`, `screenshot`, `prompt`. |
| `path` | string | Repository-relative path to the stored file. |
| `sha256` | string | Lowercase hex SHA-256 of the file's bytes. |
| `media_type` | string or null | Optional MIME type, e.g. `text/plain`, `image/png`. |

Raw transcripts live under `benchmark/real_world/raw/`. The loader recomputes the
SHA-256 of each referenced file and fails with `P-01` if a file is missing or its
hash does not match. This makes "the transcript is present and unmodified" a
checked property rather than a claim.

## Enforcement rules

The loader enforces, for `0.3.0`:

- `schema_version` must be exactly `0.3.0`. Any other value is `P-01`.
- A `complete` case with `source_type: real_world` must:
  - use tier `gold` or `silver`,
  - set `source.raw_output_available: true`,
  - reference at least one `raw_response` or `api_response` artifact,
  - and every referenced artifact file must exist and match its recorded hash.
- A `pending_capture` case may omit artifacts and set
  `raw_output_available: false`.
- A `deprecated` case must use `source.kind: reviewer_synthesis` and
  `source_type: reference_correct`. It is never `real_world`.
- A `synthetic` case must use `source_type: synthetic` and have
  `source.model_name: null`.

## Why reviewer synthesis is quarantined

The first MechAudit "real" fixtures were reviewer-written descriptions of model
runs, with `raw_output_available: false`. They are honest as controls — they
exercise the verifier's false-positive behavior — but they are not evidence that
any model produced any specific output. Tier `deprecated` exists to keep these
cases usable while making it impossible for them to masquerade as captures, in
the schema or in reporting.
