# Raw capture artifacts

This directory holds verbatim model outputs referenced by `complete`
`real_world` benchmark cases.

- One file per artifact (raw transcript `.txt`, API response `.json`, or
  UI screenshot `.png`).
- Each file is referenced from a case's `source.artifacts[]` with its
  SHA-256. The loader recomputes the hash and fails with `P-01` on any
  missing or modified file.
- Do not edit a stored artifact after capture. To correct a capture, store a
  new file and update the case.

See `docs/capture_provenance.md` for the provenance tiers and rules.
