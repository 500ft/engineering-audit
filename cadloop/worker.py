"""CAD build worker. Runs on the SOLIDWORKS host, one job per invocation.

Reads `job.json` from the job directory, drives SOLIDWORKS through its COM API,
and writes `result.json` atomically. Standard output is not used for results:
processes launched into an interactive Windows session do not reliably return
stdout to the caller.

Invoked as: python worker.py <job_dir>
"""

import json
import os
import shutil
import subprocess
import sys
import time
import traceback

import volume

SW_DOC_PART = 1
SW_SOLID_BODY = 0
DENSITY_KG_M3 = 1000.0
OPEN_RETRIES = 4
OPEN_RETRY_DELAY_S = 5
POST_LAUNCH_SETTLE_S = 8


def load_job(job_dir):
    with open(os.path.join(job_dir, "job.json")) as handle:
        return json.load(handle)


def write_result(job_dir, result):
    tmp = os.path.join(job_dir, "result.json.tmp")
    with open(tmp, "w") as handle:
        json.dump(result, handle, indent=2)
    os.replace(tmp, os.path.join(job_dir, "result.json"))


def log(job_dir, message):
    with open(os.path.join(job_dir, "build.log"), "a") as handle:
        handle.write("%s %s\n" % (time.strftime("%H:%M:%S"), message))
        handle.flush()


def solidworks_running():
    out = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"],
        capture_output=True, text=True,
    ).stdout
    return "SLDWORKS.EXE" in out.upper()


def read_global_variables(equation_mgr):
    """Map global-variable name to equation index.

    Global variables are the equations whose text begins with a quoted name.
    Dimension-driving equations are left untouched: they are the template's
    contract, not job input.
    """
    names = {}
    for index in range(equation_mgr.GetCount):
        text = equation_mgr.Equation(index) or ""
        stripped = text.strip()
        if stripped.startswith('"'):
            names[stripped.split('"')[1]] = index
    return names


def failing_features(document, warning_flag):
    """Return every feature reporting a nonzero error code after a rebuild."""
    failures = []
    feature = document.FirstFeature
    while feature is not None:
        code = feature.GetErrorCode2(warning_flag)
        code = code[0] if isinstance(code, tuple) else code
        if code:
            failures.append({"feature": feature.Name, "error_code": code})
        feature = feature.GetNextFeature
    return failures


def open_template_copy(sw, path, long_ref_a, long_ref_b):
    """Open a part, retrying because host open latency is highly variable.

    See docs/solidworks_api_findings.md: a single OpenDoc6 call on this host has
    been observed to take from seconds to over thirteen minutes, and to fail
    with an RPC error that a later identical call does not reproduce.
    """
    last_error = None
    for _ in range(OPEN_RETRIES):
        try:
            return sw.OpenDoc6(path, SW_DOC_PART, 0, "", long_ref_a, long_ref_b)
        except Exception as error:  # COM errors are not a stable subclass
            last_error = error
            time.sleep(OPEN_RETRY_DELAY_S)
    if last_error is not None:
        raise last_error
    return None


def main():
    job_dir = sys.argv[1]
    job = load_job(job_dir)
    result = {
        "job_id": job["job_id"],
        "status": "error",
        "stage": "init",
        "message": "",
        "warnings": [],
        "resolved_parameters": {},
        "artifacts": {},
    }

    if solidworks_running():
        result["stage"] = "preflight"
        result["message"] = (
            "SLDWORKS.exe is already running; refusing to attach to a session this "
            "job does not own, because the worker exits the application when done"
        )
        write_result(job_dir, result)
        return

    import pythoncom
    import win32com.client

    warning_flag = win32com.client.VARIANT(pythoncom.VT_BOOL | pythoncom.VT_BYREF, False)
    long_ref_a = win32com.client.VARIANT(pythoncom.VT_I4 | pythoncom.VT_BYREF, 0)
    long_ref_b = win32com.client.VARIANT(pythoncom.VT_I4 | pythoncom.VT_BYREF, 0)

    sw = None
    document = None
    try:
        template = job["template_part"]
        working_copy = os.path.join(job_dir, os.path.basename(template))
        shutil.copyfile(template, working_copy)
        log(job_dir, "copied template to %s" % working_copy)

        result["stage"] = "open"
        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = False
        time.sleep(POST_LAUNCH_SETTLE_S)

        document = open_template_copy(sw, working_copy, long_ref_a, long_ref_b)
        if document is None:
            result["message"] = "OpenDoc6 returned no document for %s" % working_copy
            write_result(job_dir, result)
            return
        log(job_dir, "opened working copy")

        result["stage"] = "validate"
        equation_mgr = document.GetEquationMgr
        global_variables = read_global_variables(equation_mgr)
        requested = job["parameters"]

        unknown = sorted(name for name in requested if name not in global_variables)
        if unknown:
            result["message"] = "template declares no global variable named: %s (declared: %s)" % (
                ", ".join(unknown), ", ".join(sorted(global_variables)),
            )
            write_result(job_dir, result)
            return

        for name, value in requested.items():
            try:
                volume.parse_mm(value)
            except volume.DimensionError as error:
                result["message"] = "parameter %s: %s" % (name, error)
                write_result(job_dir, result)
                return

        result["stage"] = "apply"
        applied = []
        for name, value in requested.items():
            index = global_variables[name]
            equation_mgr.Equation(index, '"%s"= %s' % (name, value))
            applied.append({"name": name, "index": index, "readback": equation_mgr.Equation(index)})
        result["resolved_parameters"] = dict(requested)
        result["applied_equations"] = applied
        log(job_dir, "applied %d parameters" % len(applied))

        result["stage"] = "evaluate"
        equation_mgr.EvaluateAll

        result["stage"] = "rebuild"
        rebuilt = document.ForceRebuild3(False)
        failures = failing_features(document, warning_flag)
        if not rebuilt or failures:
            result["message"] = "rebuild reported errors"
            result["warnings"] = failures
            write_result(job_dir, result)
            return
        log(job_dir, "rebuild clean")

        result["stage"] = "geometry"
        bodies = document.GetBodies2(SW_SOLID_BODY, True)
        body_count = len(bodies) if bodies else 0
        measured_mm3 = 0.0
        if bodies:
            measured_mm3 = bodies[0].GetMassProperties(DENSITY_KG_M3)[3] * 1e9

        acceptance = job.get("acceptance", {})
        check = volume.check_volume(
            acceptance.get("oracle"),
            requested,
            measured_mm3,
            acceptance.get("tolerance_pct", 0.5),
        )
        result["body_count"] = body_count
        result["volume_check"] = check

        if body_count != 1:
            result["message"] = "expected exactly one solid body, measured %d" % body_count
            write_result(job_dir, result)
            return
        if check["accepted"] is False:
            result["message"] = (
                "geometry does not match the requested parameters: expected %.3f mm3, "
                "measured %.3f mm3 (%.3f%% off, tolerance %.3f%%)"
                % (check["expected_mm3"], check["measured_mm3"],
                   check["error_pct"], check["tolerance_pct"])
            )
            write_result(job_dir, result)
            return
        log(job_dir, "geometry accepted: %s" % check)

        result["stage"] = "export_step"
        document.ClearSelection2(True)
        step_path = os.path.join(job_dir, job["output_name"] + ".step")
        step_status = document.SaveAs3(step_path, 0, 0)
        if not os.path.exists(step_path) or os.path.getsize(step_path) == 0:
            result["message"] = "STEP export produced no file (SaveAs3 returned %s)" % (step_status,)
            write_result(job_dir, result)
            return
        result["artifacts"]["step"] = os.path.basename(step_path)
        log(job_dir, "exported %s" % step_path)

        result["stage"] = "preview"
        document.ShowNamedView2("*Isometric", 7)
        document.ViewZoomtofit2()
        document.GraphicsRedraw2()
        preview_path = os.path.join(job_dir, job["output_name"] + ".bmp")
        if not document.SaveBMP(preview_path, 800, 600) or not os.path.exists(preview_path):
            result["message"] = "preview image was not written"
            write_result(job_dir, result)
            return
        result["artifacts"]["preview"] = os.path.basename(preview_path)
        log(job_dir, "wrote preview %s" % preview_path)

        result["status"] = "ok"
        result["stage"] = "done"
        result["message"] = "build accepted"

    except Exception:
        result["message"] = "unhandled exception:\n" + traceback.format_exc()
        log(job_dir, result["message"])
    finally:
        try:
            if document is not None:
                sw.CloseDoc(document.GetTitle)
        except Exception:
            pass
        try:
            if sw is not None:
                sw.ExitApp()
        except Exception:
            pass
        write_result(job_dir, result)


if __name__ == "__main__":
    main()
