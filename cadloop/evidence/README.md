# CAD loop evidence

Unedited outputs from the host runs that produced the current template and the
findings in [`../../docs/solidworks_api_findings.md`](../../docs/solidworks_api_findings.md).
Recorded 2026-09-17 on the reference host (SOLIDWORKS 2024 build 34.2.1,
Python 3.12.10, `pywin32` 312).

These files were produced by the session scripts that `cadloop/` was refactored
from, so their key names and step names do not always match the current modules.
They are kept as recorded rather than rewritten to match. The recorded runs also
used the earlier host path `C:\SWBuilder\`, which the current modules replace
with `C:\CADLoop\`; authoring must be re-run before a job can resolve the
template path the job specifications declare.

| File | What it shows | What it does not show |
| --- | --- | --- |
| `template-authoring-2026-09-17.json` | The authoring run that produced the current template: all four global-variable declarations and all four dimension links accepted with indices 0-7, a clean rebuild with no failing features, one solid body, and 29 748.672 587 712 812 mm³ measured against a 29 748.673 mm³ oracle. | Any parametric re-drive. This is the template at its authored defaults. `origin_coincident_constraint: false` is the open under-defined-sketch gap. |
| `template-preview-2026-09-17.png` | Isometric view of the authored plate written by `SaveBMP` and converted to PNG: rectangular plate, one through hole near centre. | Dimensional verification. A preview cannot confirm size; the oracle comparison does that. |
| `equation-readback-pre-fix-2026-09-17.json` | The failure mode that motivated the quoting finding: a template that read back three global variables and zero dimension links, after an authoring run that reported its equations written. `Thickness` is absent because its declaration was rejected. | The current template, which has eight equations. This is the pre-fix state, kept deliberately. |
| `open-latency-2026-09-17.json` | One `OpenDoc6` call returning successfully 797.96 s (13 min 18 s) after the last liveness sample, with `SLDWORKS.exe` alive across all six samples beforehand. | A cause. The call succeeded; other runs failed in about 20 s with an RPC error. Unresolved. |
| `parametric-redrive-2026-09-18.json` | `result.json` from `orchestrator.py cadloop/jobs/plate-150x80x6.json` against the template re-authored at `C:\CADLoop\templates\plate.sldprt`: all four parameters applied with read-backs, one solid body, 71 528.761 101 961 53 mm³ measured against a 71 528.761 101 961 54 mm³ oracle (2e-14% error), STEP and preview both retrieved. This is the loop's first recorded parametric re-drive. | Position of the hole. The oracle constrains volume only. |
| `parametric-redrive-preview-2026-09-18.png` | Isometric preview of the 150x80x6mm plate with a 10mm hole, visibly larger and thicker than the 100x60x5mm authored default. | Dimensional verification; see the oracle comparison in the JSON alongside it. |

## Recorded on 2026-09-18

The same session that produced `parametric-redrive-2026-09-18.json` also found
that `author_template.py`'s `GetUserPreferenceStringValue(swDefaultTemplatePart)`
call returned an empty string on a fresh authoring run — not the not-yet-run
condition the earlier evidence covers, but an intermittent one, since the
2026-09-17 authoring run resolved a template path from the same call. The fix
(a hard-coded fallback path, checked into `author_template.py`) is what let
this session's authoring run and the parametric re-drive above complete. See
`docs/solidworks_api_findings.md` for both this and a second finding from the
same session: a host network outage left the interactive session unable to
complete `OpenDoc6`/`AddDimension2` calls across multiple consecutive attempts,
recovered by killing stray SOLIDWORKS processes and retrying rather than by
rebooting the host.
