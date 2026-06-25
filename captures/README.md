# Captures

Immutable, hash-verified raw model captures. This tree is the rail for genuine
`gold`/`silver` captures; nothing here is fabricated or synthetic.

Layout (pre-registered by `mechaudit.capture`):

- `prompts/` — verbatim prompt text, one file per `prompt_id`. Re-registering a
  prompt id with different text is refused.
- `models/`  — one record per model id seen.
- `runs/`    — one directory per captured run, named
  `<model>__<prompt>__<output-hash12>`, holding the verbatim `output.txt`
  (or `output.json`) and a `source.json` provenance record with the SHA-256 of
  the captured bytes.

A captured run is promoted into a `complete` `real_world` benchmark case by
copying its output artifact into `benchmark/real_world/raw/` and referencing the
recorded hash from the case `source.artifacts[]`. See `docs/capture_provenance.md`.

The actual model API call that produces `output.txt` is performed by the
operator with their own credentials; `mechaudit capture` only records the bytes
it is handed (from a file or stdin) and never performs network access.
