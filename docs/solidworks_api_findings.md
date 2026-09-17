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

## Session and process behaviour

| Finding | Consequence |
| --- | --- |
| SOLIDWORKS' COM server will not start from a non-interactive SSH session. | `Dispatch` fails with `Server execution failed` (`CO_E_SERVER_EXEC_FAILURE`). The process must be launched into a logged-in session; PsExec's `-i <session>` does this. |
| Running as `SYSTEM` in the target session is not sufficient. | The launch must also impersonate the account that owns the session, so PsExec needs `-u` and `-p`. |
| PsExec does not reliably return when a process it started in an interactive session finishes. | Completion cannot be inferred from the launch call. Poll for a result file. |
| Standard output from a process in another session does not reach the caller. | Host-side scripts write their results to a file; nothing depends on stdout. |
| `scp` treats a backslash in a remote path as an escape character. | `C:\CADLoop\jobs\x\result.json` resolves to a mangled name and the transfer fails while the local caller sees only a missing file. Use forward slashes for remote paths. |
| `OpenDoc6` latency is unstable, and a failure is not reproducible. | One measured call returned after 13 minutes 18 seconds; others failed in about 20 seconds with `The remote procedure call failed` while the process stayed alive throughout. Cause unresolved. The worker retries the open and the orchestrator polls on a long deadline. |

## Uninstall behaviour

The Ansys Student uninstaller reported `Uninstallation Complete` while leaving
most of the installation in place — roughly 65 GB across `ansys`, `fluent`,
`meshing`, and sibling directories — and scheduled a self-delete script that
covered only its own uninstaller. Verify the install directory after any
uninstall rather than trusting the log.
