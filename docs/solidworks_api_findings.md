# SOLIDWORKS API findings

Behaviour observed while building `cadloop` against SOLIDWORKS 2024 with
Python 3.12 and `pywin32` 312, driven over COM from a script launched into a
logged-in Windows session. Each entry is recorded because the failure it
describes is silent, misleading, or costly to rediscover.

Reference host: Windows 11 Home, SOLIDWORKS 2024 (build 34.2.1), Python 3.12.10,
`pywin32` 312, launched with PsExec into session 1.

## Dispatch and binding

| Finding | Consequence |
| --- | --- |
| `win32com.client.gencache.EnsureDispatch` fails with `TypeError: This COM object can not automate the makepy process`. | Early binding is unavailable, so named enumeration constants are unavailable. Use `Dispatch` and numeric enum values. |
| Members named `GetX` are frequently properties, not methods. | `GetEquationMgr()`, `GetCount()`, `EvaluateAll()`, `FirstFeature()`, `GetNextFeature()`, and `GetTitle()` all fail when called. Access them without parentheses. VBA hides this distinction; Python does not. |
| A nullable interface argument rejects `None` and `pythoncom.Empty`. | `SelectByID2` raises `Type mismatch` until the `Callout` argument is `win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)`. |
| A by-reference scalar argument rejects a plain Python value. | `OpenDoc6`'s error and warning arguments need `VARIANT(VT_I4 \| VT_BYREF, 0)`; `IFeature::GetErrorCode2`'s warning flag needs `VARIANT(VT_BOOL \| VT_BYREF, False)`. |
| A property on an object returned from another call may not expose a setter. | `IDimension::SystemValue` raises `Property ... can not be set`. Invoke the property-put directly through `_oleobj_.Invoke(dispatch_id, 0, DISPATCH_PROPERTYPUT, 0, value)`. |

## Object model

| Finding | Consequence |
| --- | --- |
| `IModelDoc2::AddDimension2` returns a `DisplayDimension`, not a `Dimension`. | `SystemValue` and `FullName` are one hop away, through `GetDimension2(0)`. |
| `IDimension::FullName` returns three parts, such as `D1@Sketch1@Part1.Part`. | Equations inside the same part need the two-part form `D1@Sketch1`. The document-qualified form is accepted by `Add2` and then discarded. |
| `IModelDocExtension::CreateMassProperty` is not resolvable on this build. | Take mass properties from the body: `IBody2::GetMassProperties(density)`, where index 3 is volume in cubic metres. |
| `IModelDocExtension::SaveAs3` requires an `AdvancedSaveAsOptions` object. | The three-argument `IModelDoc2::SaveAs3(path, 0, 0)` form is sufficient for both native saves and STEP export, and the target format follows the path's extension. |
| `SaveAs3` returns a status code, not a boolean, and the observed values are inconsistent. | Saves that produced a valid, correctly sized file returned both `0` and `1` on this host. The return value therefore cannot be truth-tested in either direction; check that the file exists and is non-empty. |

## Equations

| Finding | Consequence |
| --- | --- |
| `Thickness` cannot be declared as a global variable. | `Add2` returns `-1` and the declaration is discarded. The name appears to be reserved. `PlateThickness` works. |
| One rejected equation invalidates the rest of the batch. | Every `Add2` call after the rejected one also returns `-1`, so a single bad name silently costs every subsequent equation. Check each return index. |
| A dimension-driving equation needs both sides quoted. | `"D1@Sketch1"= "Length"` is stored; `D1@Sketch1= "Length"` returns `-1` and is discarded, leaving the global variable declared but driving nothing. |
| `Add2` with `Solve=False` defers evaluation. | `EvaluateAll` must run before the equations appear in the feature tree or affect a rebuild. |

The combination of the last three is worth stating directly: a template can
contain correctly declared global variables, have every link equation silently
rejected, rebuild cleanly, and measure exactly the expected volume — because
the authored dimensions already carry those values. The template looks
parametric and is not. Reading the equation table back, which
`inspect_template.py` does, is the check that catches it.

## Sketch dimensions and what actually drives geometry

All of this was measured on the host by `cadloop/scaffold/probe_rectangle.py`
and `probe_sketch_dims.py`.

| Finding | Consequence |
| --- | --- |
| `CreateCornerRectangle` **sometimes** dimensions its own rectangle. In the scaffold run the sketch already held two dimensions (`D1`, `D2`) immediately after the call, before `AddDimension2` was used at all. | Dimensions added afterwards are then a *second* pair on the same two edges. Ours report driving and the tool's already fix the geometry, so driving ours moves nothing. Delete what the tool created before adding your own; `swhelpers.clear_sketch_dimensions` does this. |
| It is not a property of the API call. The same call on the same host produced **no** dimensions when `root_clamp` was authored in `autonomous-racing-systems`: that sketch holds exactly the two dimensions the script added, in the order it added them, and all three clamp variables re-drive correctly. The scaffold, authored later, got two. | The rectangle tool's automatic-dimension option is sticky host state that changes between sessions, so neither outcome can be assumed. Do not write code that depends on the tool dimensioning, or on it not dimensioning. Clearing first makes the result the same either way — with the option off there is simply nothing to remove, which is what the circle sketches show (`removed: []`). |
| The over-defined sketch still measures correctly. | The rectangle was drawn at the intended size, so the oracle agrees to 1e-16 and the part looks finished. It is not parametric. Only a parameter change exposes it — this is exactly the failure the re-drive test exists for, and it was caught that way. |
| `EditDelete` returns `False` for a dimension it successfully deleted. | Do not test the return value. Confirm by re-reading the sketch's dimension list; after the "failed" deletes the list was empty and the sketch had dropped back to under-defined. |
| `IDimension::DrivenState` is not meaningful inside an open sketch. | Dimensions that report `2` (driven) while the sketch is open report `1` (driving) once it closes and solves. Gating on it mid-sketch reads every new dimension as driven. |
| `GetConstrainedStatus` returned `3` for both a correctly fully-defined sketch and the over-defined four-dimension sketch. | It does not distinguish them, so it cannot be used as the parametricity check. The empty sketch returned `2`. |
| The `Equations` folder reports `GetErrorCode2` = 1, with the by-reference warning flag *clear*, for the remainder of the session that added the equations — surviving any number of `ForceRebuild3` calls. Saving and reopening clears it. | Two consequences. First, rebuild state must be verified on the reopened file, not in the authoring session; that also checks the artifact on disk rather than the live session. Second, the code was not noise: here it was a true signal pointing at the over-defined sketch, and it went away when the cause was fixed. |
| `GetErrorCode2` takes a by-reference flag saying whether a non-zero code is a warning. | Read it. Treating every non-zero code as a failure rejects parts whose geometry is correct; ignoring the code entirely accepts parts whose features are in error. |

## Session and process behaviour

| Finding | Consequence |
| --- | --- |
| SOLIDWORKS' COM server will not start from a non-interactive SSH session. | `Dispatch` fails with `Server execution failed` (`CO_E_SERVER_EXEC_FAILURE`). The process must be launched into a logged-in session; PsExec's `-i <session>` does this. |
| Running as `SYSTEM` in the target session is not sufficient. | The launch must also impersonate the account that owns the session, so PsExec needs `-u` and `-p`. |
| PsExec does not reliably return when a process it started in an interactive session finishes. | Completion cannot be inferred from the launch call. Poll for a result file. |
| Standard output from a process in another session does not reach the caller. | Host-side scripts write their results to a file; nothing depends on stdout. |
| `scp` treats a backslash in a remote path as an escape character. | `C:\CADLoop\jobs\x\result.json` resolves to a mangled name and the transfer fails while the local caller sees only a missing file. Use forward slashes for remote paths. |
| `OpenDoc6` latency is unstable, and a failure is not reproducible. | One measured call returned after 13 minutes 18 seconds; others failed in about 20 seconds with `The remote procedure call failed` while the process stayed alive throughout. Cause unresolved. The worker retries the open and the orchestrator polls on a long deadline. |
| `GetUserPreferenceStringValue(swDefaultTemplatePart)` has returned an empty string on an authoring run where the previous day's run on the same host returned a valid path. | Not a one-time first-run condition; intermittent. `author_template.py` falls back to the literal templates path (`C:\ProgramData\SolidWorks\SOLIDWORKS 2024\templates\Part.prtdot`) when the preference lookup is empty or does not resolve to a file that exists. |
| A host network outage left the interactive session unable to complete COM calls across multiple consecutive attempts — `OpenDoc6` and, separately, `AddDimension2` both failed with `The remote procedure call failed` or `The RPC server is unavailable` on back-to-back fresh-process attempts after the host's network dropped and reconnected. | Not the same failure mode as the unstable-latency finding above: the process was confirmed absent before each attempt, so this was not a zombie COM server, and every attempt failed at a different call rather than reliably at the same one. Recovered without rebooting the host: kill any SOLIDWORKS process, wait, and retry the whole script from `Dispatch` onward. Two retries were needed before a clean run; a working session does not appear to need this. |

## Uninstall behaviour

The Ansys Student uninstaller reported `Uninstallation Complete` while leaving
most of the installation in place — roughly 65 GB across `ansys`, `fluent`,
`meshing`, and sibling directories — and scheduled a self-delete script that
covered only its own uninstaller. Verify the install directory after any
uninstall rather than trusting the log.
