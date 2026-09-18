"""Author the parametric plate fixture used by the CAD loop.

Creates a rectangular plate with one through hole whose four driving dimensions
are linked to named global variables, then verifies the result against the
closed-form oracle before saving. Run once per host; `worker.py` drives the
saved template thereafter.

Invoked as: python author_template.py <output_dir> [save_path]
"""

import json
import os
import sys
import traceback

import volume

SW_DEFAULT_PART_TEMPLATE = 69
SW_DOC_PART = 1
SW_SOLID_BODY = 0
SW_END_COND_THROUGH_ALL = 1
SW_START_SKETCH_PLANE = 0
DENSITY_KG_M3 = 1000.0
DEFAULT_SAVE_PATH = r"C:\CADLoop\templates\plate.sldprt"
FALLBACK_PART_TEMPLATE = r"C:\ProgramData\SolidWorks\SOLIDWORKS 2024\templates\Part.prtdot"

# Authored defaults, in metres for the API and millimetres for the equations.
LENGTH_M, WIDTH_M, THICKNESS_M, HOLE_DIAMETER_M = 0.100, 0.060, 0.005, 0.008
DEFAULTS_MM = {
    "Length": "100mm",
    "Width": "60mm",
    "PlateThickness": "5mm",
    "HoleDiameter": "8mm",
}

RESULT = {"status": "error", "steps": [], "message": "", "declared_defaults": DEFAULTS_MM}


def step(name, ok, detail=None):
    RESULT["steps"].append({"step": name, "ok": bool(ok), "detail": detail})
    return bool(ok)


def set_property(com_object, name, value):
    """Assign a COM property that dynamic dispatch exposes as read-only.

    Objects returned from another COM call do not always advertise a property
    setter, so the property-put is invoked directly. See
    docs/solidworks_api_findings.md.
    """
    import pythoncom
    dispatch_id = com_object._oleobj_.GetIDsOfNames(name)
    com_object._oleobj_.Invoke(dispatch_id, 0, pythoncom.DISPATCH_PROPERTYPUT, 0, value)


def short_dimension_name(dimension):
    """Return `D1@Sketch1` from a full name like `D1@Sketch1@Part1.Part`.

    Equations inside a part reference the two-part form; the document-qualified
    form is silently rejected by the equation parser.
    """
    return "@".join(dimension.FullName.split("@")[:2])


def dimension_for_selection(part, place_x, place_y, callout):
    """Dimension the current selection and return the underlying dimension."""
    display = part.AddDimension2(place_x, place_y, 0.0)
    if display is None:
        return None
    return display.GetDimension2(0)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    save_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SAVE_PATH
    result_path = os.path.join(out_dir, "template_build_result.json")

    part = None
    sw = None
    try:
        import pythoncom
        import win32com.client

        callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        warning_flag = win32com.client.VARIANT(pythoncom.VT_BOOL | pythoncom.VT_BYREF, False)

        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = False

        part_template = sw.GetUserPreferenceStringValue(SW_DEFAULT_PART_TEMPLATE)
        if not part_template or not os.path.exists(part_template):
            # GetUserPreferenceStringValue(swDefaultTemplatePart) has been observed
            # to return an empty string on this host. See
            # docs/solidworks_api_findings.md.
            part_template = FALLBACK_PART_TEMPLATE
        step("resolve_part_template", part_template and os.path.exists(part_template), part_template)

        part = sw.NewDocument(part_template, 0, 0, 0)
        if not step("new_document", part is not None):
            RESULT["message"] = "NewDocument returned nothing for %s" % part_template
            return

        step("select_front_plane",
             part.Extension.SelectByID2("Front Plane", "PLANE", 0.0, 0.0, 0.0, False, 0, callout, 0))

        sketch_mgr = part.SketchManager
        sketch_mgr.InsertSketch(True)
        step("open_profile_sketch", True)
        step("draw_rectangle",
             sketch_mgr.CreateCornerRectangle(0.0, 0.0, 0.0, LENGTH_M, WIDTH_M, 0.0) is not None)

        part.ClearSelection2(True)
        selected = part.Extension.SelectByID2(
            "", "SKETCHSEGMENT", LENGTH_M / 2, 0.0, 0.0, False, 0, callout, 0)
        length_dim = dimension_for_selection(part, LENGTH_M / 2, -0.01, callout) if selected else None
        length_name = None
        if step("dimension_length", length_dim is not None):
            set_property(length_dim, "SystemValue", LENGTH_M)
            length_name = short_dimension_name(length_dim)

        part.ClearSelection2(True)
        selected = part.Extension.SelectByID2(
            "", "SKETCHSEGMENT", 0.0, WIDTH_M / 2, 0.0, False, 0, callout, 0)
        width_dim = dimension_for_selection(part, -0.01, WIDTH_M / 2, callout) if selected else None
        width_name = None
        if step("dimension_width", width_dim is not None):
            set_property(width_dim, "SystemValue", WIDTH_M)
            width_name = short_dimension_name(width_dim)

        part.ClearSelection2(True)
        part.Extension.SelectByID2("", "SKETCHPOINT", 0.0, 0.0, 0.0, False, 0, callout, 0)
        part.Extension.SelectByID2("Origin", "ORIGIN", 0.0, 0.0, 0.0, True, 0, callout, 0)
        step("anchor_sketch_to_origin", part.SketchAddConstraints("sgCOINCIDENT"))

        sketch_mgr.InsertSketch(True)
        step("close_profile_sketch", True)

        extrusion = part.FeatureManager.FeatureExtrusion3(
            True, False, False, 0, 0, THICKNESS_M, 0.0, False, False, False, False,
            0, 0, False, False, False, False, True, True, True, 0, 0, False)
        step("extrude_plate", extrusion is not None)

        thickness_name = None
        if extrusion is not None:
            depth_dim = extrusion.Parameter("D1")
            if depth_dim is not None:
                thickness_name = short_dimension_name(depth_dim)
        step("capture_thickness_dimension", thickness_name is not None, thickness_name)

        step("select_top_face",
             part.Extension.SelectByID2("", "FACE", LENGTH_M / 2, WIDTH_M / 2, THICKNESS_M,
                                        False, 0, callout, 0))
        sketch_mgr.InsertSketch(True)
        step("open_hole_sketch", True)
        step("draw_hole_circle",
             sketch_mgr.CreateCircleByRadius(LENGTH_M / 2, WIDTH_M / 2, 0.0,
                                             HOLE_DIAMETER_M / 2) is not None)

        part.ClearSelection2(True)
        selected = part.Extension.SelectByID2(
            "", "SKETCHSEGMENT", LENGTH_M / 2 + HOLE_DIAMETER_M / 2, WIDTH_M / 2, 0.0,
            False, 0, callout, 0)
        hole_dim = dimension_for_selection(part, 0.07, 0.04, callout) if selected else None
        hole_name = None
        if step("dimension_hole_diameter", hole_dim is not None):
            set_property(hole_dim, "SystemValue", HOLE_DIAMETER_M)
            hole_name = short_dimension_name(hole_dim)

        sketch_mgr.InsertSketch(True)
        step("close_hole_sketch", True)

        cut = part.FeatureManager.FeatureCut4(
            True, False, False, SW_END_COND_THROUGH_ALL, 0, 0.01, 0.01,
            False, False, False, False, 1, 1, False, False, False, False, False,
            True, True, True, True, False, SW_START_SKETCH_PLANE, 0, False, False)
        step("cut_hole", cut is not None)

        equation_mgr = part.GetEquationMgr
        additions = []
        declarations = ['"%s"= %s' % (name, value) for name, value in DEFAULTS_MM.items()]
        links = [
            (length_name, "Length"),
            (width_name, "Width"),
            (hole_name, "HoleDiameter"),
            (thickness_name, "PlateThickness"),
        ]
        for text in declarations:
            additions.append({"equation": text, "index": equation_mgr.Add2(-1, text, False)})
        for dimension_name, variable in links:
            if dimension_name:
                # Both sides are quoted: an unquoted dimension name is accepted
                # by Add2 and then discarded.
                text = '"%s"= "%s"' % (dimension_name, variable)
                additions.append({"equation": text, "index": equation_mgr.Add2(-1, text, False)})
        accepted = all(item["index"] is not None and item["index"] >= 0 for item in additions)
        step("write_equations", accepted, additions)
        if not accepted:
            RESULT["message"] = "the equation manager rejected at least one equation"
            return

        equation_mgr.EvaluateAll

        rebuilt = part.ForceRebuild3(False)
        failures = []
        feature = part.FirstFeature
        while feature is not None:
            code = feature.GetErrorCode2(warning_flag)
            code = code[0] if isinstance(code, tuple) else code
            if code:
                failures.append({"feature": feature.Name, "error_code": code})
            feature = feature.GetNextFeature
        step("rebuild", rebuilt and not failures, failures)

        bodies = part.GetBodies2(SW_SOLID_BODY, True)
        body_count = len(bodies) if bodies else 0
        measured_mm3 = bodies[0].GetMassProperties(DENSITY_KG_M3)[3] * 1e9 if bodies else 0.0
        check = volume.check_volume("plate_with_center_hole", DEFAULTS_MM, measured_mm3, 0.5)
        RESULT["volume_check"] = check
        RESULT["body_count"] = body_count
        if not step("verify_against_oracle", body_count == 1 and check["accepted"], check):
            RESULT["message"] = "authored geometry does not match the closed-form oracle"
            return

        # SaveAs3's status code has been observed as both 0 and 1 for saves that
        # produced a valid file. File existence is the check that cannot be misread.
        save_status = part.SaveAs3(save_path, 0, 0)
        step("save_template", os.path.exists(save_path),
             {"path": save_path, "save_status": repr(save_status)})

        preview_path = os.path.join(out_dir, "template_preview.bmp")
        part.ShowNamedView2("*Isometric", 7)
        part.ViewZoomtofit2()
        part.GraphicsRedraw2()
        step("write_preview", part.SaveBMP(preview_path, 800, 600), preview_path)

        RESULT["status"] = "ok" if all(item["ok"] for item in RESULT["steps"]) else "partial"
        RESULT["message"] = "template authored"

    except Exception:
        RESULT["message"] = "unhandled exception:\n" + traceback.format_exc()
    finally:
        try:
            if part is not None:
                sw.CloseDoc(part.GetTitle)
        except Exception:
            pass
        try:
            if sw is not None:
                sw.ExitApp()
        except Exception:
            pass
        with open(result_path, "w") as handle:
            json.dump(RESULT, handle, indent=2)


if __name__ == "__main__":
    main()
