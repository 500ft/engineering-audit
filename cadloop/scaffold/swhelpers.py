"""SOLIDWORKS COM helpers with the host's known traps already handled.

Runs on the host. Every function here exists because the obvious way to write it
does not work on this host, silently. Each docstring records why. Behaviour is
catalogued in docs/solidworks_api_findings.md; this module is that catalogue as
working code, so a new part does not rediscover it.

Import from a sibling script: `import swhelpers as sw`.
"""

import os
import subprocess
import time

# Enumerations. Use numbers: gencache/makepy fails against this type library, so
# named constants are unavailable.
SW_DOC_PART = 1
SW_SOLID_BODY = 0
SW_DEFAULT_PART_TEMPLATE = 69
SW_THROUGH_ALL = 1          # swEndCondThroughAllBoth = 9 is rejected on this build
SW_START_SKETCH_PLANE = 0
MM = 0.001                  # the API works in metres; author in mm and scale

FALLBACK_PART_TEMPLATE = r"C:\ProgramData\SolidWorks\SOLIDWORKS 2024\templates\Part.prtdot"
POST_LAUNCH_SETTLE_S = 8
OPEN_RETRIES = 4
OPEN_RETRY_DELAY_S = 5


def solidworks_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"],
                         capture_output=True, text=True).stdout
    return "SLDWORKS.EXE" in out.upper()


# swUserPreferenceToggle_e. "Input dimension value" (Tools > Options > General).
# When on, every AddDimension2 raises a modal Modify box; with no operator the
# run hangs, or the blocked COM server surfaces as "The remote procedure call
# failed". Observed true on this host on 2026-09-26 and both failures reproduced.
SW_INPUT_DIM_VAL_ON_CREATE = 10
_RESTORE = {}


def begin_unattended(app):
    """Turn off prompts that need an operator. Returns a journal of what happened.

    The toggle is read back after writing rather than assumed, so a run records
    whether it actually took effect.
    """
    journal = []
    for ident, target in ((SW_INPUT_DIM_VAL_ON_CREATE, False),):
        entry = {"preference_id": ident, "target": target}
        try:
            was = bool(app.GetUserPreferenceToggle(ident))
            app.SetUserPreferenceToggle(ident, target)
            now = bool(app.GetUserPreferenceToggle(ident))
            _RESTORE[ident] = was
            entry.update(was=was, now=now, applied=(now == target))
        except Exception as error:
            entry.update(applied=False, error="%s: %s" % (type(error).__name__, error))
        journal.append(entry)
    return journal


def end_unattended(app):
    """Put the host's own settings back."""
    for ident, was in list(_RESTORE.items()):
        try:
            app.SetUserPreferenceToggle(ident, was)
        except Exception:
            pass
    _RESTORE.clear()


def connect(visible=False, unattended=True):
    """Start SOLIDWORKS and return (app, callout, warning_flag).

    Dispatch, not EnsureDispatch: gencache cannot automate makepy for this type
    library. The two VARIANTs are required arguments elsewhere and are made once
    here because constructing them wrongly is a common failure.

    `unattended` disables the operator prompts that otherwise block a headless
    run. Read `last_unattended_journal()` to record what it did.
    """
    import pythoncom
    import win32com.client

    app = win32com.client.Dispatch("SldWorks.Application")
    app.Visible = visible
    time.sleep(POST_LAUNCH_SETTLE_S)
    globals()["_JOURNAL"] = begin_unattended(app) if unattended else []

    # SelectByID2 rejects None and pythoncom.Empty for its nullable Callout.
    callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    # IFeature::GetErrorCode2 takes a by-reference boolean, not a Python bool.
    warning_flag = win32com.client.VARIANT(pythoncom.VT_BOOL | pythoncom.VT_BYREF, False)
    return app, callout, warning_flag


def long_refs():
    """Two by-reference longs, for OpenDoc6's error and warning arguments."""
    import pythoncom
    import win32com.client
    return (win32com.client.VARIANT(pythoncom.VT_I4 | pythoncom.VT_BYREF, 0),
            win32com.client.VARIANT(pythoncom.VT_I4 | pythoncom.VT_BYREF, 0))


def part_template(app):
    """The default part template, with a fallback.

    GetUserPreferenceStringValue has returned an empty string on a host where the
    previous day's call returned a valid path, so the result is checked.
    """
    path = app.GetUserPreferenceStringValue(SW_DEFAULT_PART_TEMPLATE)
    if path and os.path.exists(path):
        return path
    return FALLBACK_PART_TEMPLATE


def new_part(app):
    return app.NewDocument(part_template(app), 0, 0, 0)


def open_part(app, path):
    """Open a part, retrying. Open latency on this host is unstable: the same call
    has returned in seconds and in over thirteen minutes, and has failed with an
    RPC error that an identical later call did not reproduce."""
    last = None
    for _ in range(OPEN_RETRIES):
        try:
            doc = app.OpenDoc6(path, SW_DOC_PART, 0, "", *long_refs())
            if doc is not None:
                return doc
        except Exception as error:      # COM errors are not a stable subclass
            last = error
            time.sleep(OPEN_RETRY_DELAY_S)
    if last is not None:
        raise last
    return None


def set_property(com_object, name, value):
    """Assign a property that dynamic dispatch exposes as read-only.

    Objects returned from another COM call do not always advertise a setter, so
    IDimension::SystemValue raises "Property can not be set" on assignment. The
    property-put is invoked directly instead.
    """
    import pythoncom
    dispatch_id = com_object._oleobj_.GetIDsOfNames(name)
    com_object._oleobj_.Invoke(dispatch_id, 0, pythoncom.DISPATCH_PROPERTYPUT, 0, value)


def short_name(dimension):
    """`D1@Sketch1` from `D1@Sketch1@Part1.Part`.

    Equations inside a part need the two-part form. The document-qualified form
    is accepted by Add2 and then silently discarded, leaving a variable that
    drives nothing.
    """
    return "@".join(dimension.FullName.split("@")[:2])


def select_plane(part, name, callout):
    """Select a named datum plane: "Front Plane", "Top Plane", "Right Plane".

    Prefer this to picking a face by coordinate when the face lies on a plane
    through the origin; SelectByID2 for a FACE at exactly x=0 has returned false
    where selecting the coincident named plane worked.
    """
    part.ClearSelection2(True)
    return part.Extension.SelectByID2(name, "PLANE", 0.0, 0.0, 0.0, False, 0, callout, 0)


def select_face(part, point_mm, callout):
    """Select the face containing a point, given in millimetres."""
    part.ClearSelection2(True)
    x, y, z = (v * MM for v in point_mm)
    return part.Extension.SelectByID2("", "FACE", x, y, z, False, 0, callout, 0)


def extrude(part, depth_mm):
    """Boss-extrude the open sketch.

    The sketch must hold exactly one closed contour. Two concentric circles in
    one sketch are rejected: build a cylinder and cut its bore as two features.
    """
    return part.FeatureManager.FeatureExtrusion3(
        True, False, False, 0, 0, depth_mm * MM, 0.0, False, False, False, False,
        0, 0, False, False, False, False, True, True, True, 0, 0, False)


def cut_through_all(part, dir_opposite=False):
    """Cut the open sketch through all material.

    `dir_opposite` reverses the cut. A sketch on a FACE cuts into the body with
    the default; a sketch on a DATUM PLANE generally needs dir_opposite=True,
    because a cut and a boss do not run the same way off a datum plane. Use
    cut_through_all_either when unsure.
    """
    return part.FeatureManager.FeatureCut4(
        True, False, dir_opposite, SW_THROUGH_ALL, 0, 0.01, 0.01,
        False, False, False, False, 1, 1, False, False, False, False, False,
        True, True, True, True, False, SW_START_SKETCH_PLANE, 0, False, False)


def cut_through_all_either(part, density=1000.0):
    """Try both cut directions, keeping whichever removed material.

    Returns (feature, dir_opposite, removed_mm3) or (None, None, 0.0). The caller
    must re-create the sketch before each attempt; see the scaffold for the shape.
    """
    before = volume_mm3(part, density)
    for dir_opposite in (False, True):
        feature = cut_through_all(part, dir_opposite)
        after = volume_mm3(part, density)
        if feature is not None and after < before:
            return feature, dir_opposite, before - after
    return None, None, 0.0


def sketch_dimensions(part, sketch_name):
    """Every dimension on a sketch, as {name, value_mm, driven_state}.

    DrivenState is only meaningful once the sketch has been solved. Read inside
    an open sketch it reports 2 (driven) for dimensions that report 1 (driving)
    after the sketch closes, so do not gate on it mid-sketch.
    """
    out = []
    feature = part.FeatureByName(sketch_name)
    if feature is None:
        return out
    display = feature.GetFirstDisplayDimension
    while display is not None:
        dimension = display.GetDimension2(0)
        out.append({"name": short_name(dimension),
                    "value_mm": dimension.SystemValue / MM,
                    "driven_state": dimension.DrivenState})
        display = feature.GetNextDisplayDimension(display)
    return out


def clear_sketch_dimensions(part, sketch_name, callout):
    """Delete the dimensions a sketch tool created, so ours are the only ones.

    CreateCornerRectangle dimensions its own rectangle on a host where the
    rectangle tool has automatic dimensions enabled. That is sticky host state and
    it varies: the same call did not auto-dimension autonomous-racing-systems'
    root_clamp, authored earlier on this host. So this runs unconditionally rather
    than trying to detect which way the host is set -- with the option off there is
    nothing to remove. Adding ours on top leaves
    four dimensions on two edges: ours report driving, the tool's already fix the
    geometry, and driving ours moves nothing. The measured volume still matches
    the oracle, because the rectangle was drawn at the intended size -- only a
    parameter change exposes it. GetConstrainedStatus does not distinguish this
    from a fully defined sketch, so it cannot be used as the check.

    `sketch_name` is the feature name in the tree. Call with the sketch open,
    after drawing and before dimensioning. Returns what was removed.
    """
    removed = []
    for existing in sketch_dimensions(part, sketch_name):
        part.ClearSelection2(True)
        picked = part.Extension.SelectByID2(existing["name"], "DIMENSION",
                                           0, 0, 0, False, 0, callout, 0)
        if picked:
            # EditDelete returns False here even when the dimension is gone, so
            # the outcome is confirmed by re-reading the list, not by this call.
            part.EditDelete()
        removed.append(existing["name"])
    return {"removed": removed, "remaining": sketch_dimensions(part, sketch_name)}


def dimension_segment(part, callout, pick_mm, place_mm, value_mm):
    """Dimension the sketch segment under `pick_mm`; return its two-part name.

    Must be called while the sketch is still open. Draw the segment at its final
    size and dimension it to that same value, so applying the dimension does not
    move under-defined geometry.

    AddDimension2 returns a DisplayDimension, not a Dimension; the value and the
    name are one hop away through GetDimension2(0).
    """
    part.ClearSelection2(True)
    px, py, pz = (v * MM for v in pick_mm)
    if not part.Extension.SelectByID2("", "SKETCHSEGMENT", px, py, pz, False, 0, callout, 0):
        return None
    ax, ay, az = (v * MM for v in place_mm)
    display = part.AddDimension2(ax, ay, az)
    if display is None:
        return None
    dimension = display.GetDimension2(0)
    set_property(dimension, "SystemValue", value_mm * MM)
    return short_name(dimension)


def feature_depth_name(feature):
    """The depth dimension of an extrude, through IFeature::Parameter."""
    if feature is None:
        return None
    dimension = feature.Parameter("D1")
    return short_name(dimension) if dimension is not None else None


def write_equations(part, declarations, links):
    """Declare global variables then drive dimensions from them.

    `declarations` are strings like '"PlateLength"= 80mm'. `links` are
    (dimension_name, expression) pairs, where expression may reference variables:
    ("D1@Sketch1", '"PlateLength"') or ("D2@Sketch1", '"PlateLength" / 2').

    Both sides of a link are quoted by this function. An unquoted dimension name
    is accepted and then discarded. One rejected equation invalidates every later
    one in the batch, so each returned index is reported.

    "Thickness" cannot be declared; the name is reserved. Use "PlateThickness".
    """
    manager = part.GetEquationMgr            # a property, not a method
    written = []
    for text in declarations:
        written.append({"equation": text, "index": manager.Add2(-1, text, False)})
    for dimension_name, expression in links:
        if not dimension_name:
            written.append({"equation": None, "index": -1, "note": "no dimension name"})
            continue
        text = '"%s"= %s' % (dimension_name, expression)
        written.append({"equation": text, "index": manager.Add2(-1, text, False)})
    manager.EvaluateAll                      # also a property
    accepted = all(w["index"] is not None and w["index"] >= 0 for w in written)
    return accepted, written


def set_global(part, name, value_mm):
    """Change a declared global variable. Returns the read-back text, or None.

    Only the declaration is rewritten, never a link: a link's right side contains
    a quoted variable name, a declaration's does not.
    """
    manager = part.GetEquationMgr
    for index in range(manager.GetCount):    # GetCount is a property
        text = manager.Equation(index) or ""
        stripped = text.strip()
        if stripped.startswith('"%s"' % name) and "=" in stripped:
            if '"' not in stripped.split("=", 1)[1]:
                manager.Equation(index, '"%s"= %gmm' % (name, value_mm))
                return manager.Equation(index)
    return None


def rebuild(part, warning_flag):
    """Force a full rebuild; return (ok, {"failures": [...], "warnings": [...]}).

    Do not trust this in the session that authored the equations. Once equations
    are added, the Equations folder reports error_code 1 with the warning flag
    clear for the rest of that session, however many rebuilds are forced, even
    though every equation evaluates to the right value and the geometry is exact.
    Saving and reopening clears it. So rebuild state is verified on the reopened
    file -- which also checks the artifact on disk rather than the live session.

    ForceRebuild3 returning true and every feature reporting code zero together
    prove SOLIDWORKS raised no error. They do not prove the requested geometry
    exists. Always follow this with a measurement against an oracle.
    """
    rebuilt = bool(part.ForceRebuild3(False))
    failures, warnings = [], []
    feature = part.FirstFeature                 # property
    while feature is not None:
        code = feature.GetErrorCode2(warning_flag)
        code = code[0] if isinstance(code, tuple) else code
        if code:
            # The by-reference flag says whether a non-zero code is a warning.
            # Reading it separates real failures from noise.
            is_warning = bool(getattr(warning_flag, "value", False))
            entry = {"feature": feature.Name, "error_code": code, "warning": is_warning}
            (warnings if is_warning else failures).append(entry)
        feature = feature.GetNextFeature        # property
    return rebuilt and not failures, {"failures": failures, "warnings": warnings}


def volume_mm3(part, density=1000.0):
    """Solid volume in mm^3.

    IModelDocExtension::CreateMassProperty is not resolvable on this build; take
    mass properties from the body, where index 3 is volume in cubic metres.
    """
    try:
        bodies = part.GetBodies2(SW_SOLID_BODY, True)
        return bodies[0].GetMassProperties(density)[3] * 1e9 if bodies else 0.0
    except Exception:
        return 0.0


def body_count(part):
    bodies = part.GetBodies2(SW_SOLID_BODY, True)
    return len(bodies) if bodies else 0


def save_as(part, path):
    """Save or export by extension; return True if a non-empty file resulted.

    SaveAs3's status code has been observed as both 0 and 1 for saves that
    produced valid files, so it cannot be truth-tested in either direction. File
    existence is the check. The target format follows the path's extension, so
    the same call writes .sldprt, .step and .igs.
    """
    part.ClearSelection2(True)
    part.SaveAs3(path, 0, 0)
    return os.path.exists(path) and os.path.getsize(path) > 0


def preview(part, path, width=1000, height=750):
    part.ShowNamedView2("*Isometric", 7)
    part.ViewZoomtofit2()
    part.GraphicsRedraw2()
    part.SaveBMP(path, width, height)
    return os.path.exists(path)


def close(app, part):
    """Close a document without saving. CloseDoc takes the title; GetTitle is a
    property, so calling it raises 'str object is not callable'."""
    try:
        app.CloseDoc(part.GetTitle)
    except Exception:
        pass


def last_unattended_journal():
    """What begin_unattended() did, for the result file."""
    return globals().get("_JOURNAL", [])


def shutdown(app):
    """Restore the host's settings, then close SOLIDWORKS."""
    if app is not None:
        end_unattended(app)
    try:
        if app is not None:
            app.ExitApp()
    except Exception:
        pass
