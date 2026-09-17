"""Measure how long the host takes to open a part, and whether it stays alive.

Open latency on the reference host is unstable: the same call has completed in
seconds and in over thirteen minutes, and has failed with an RPC error that the
next identical call did not reproduce. This script separates the two candidate
explanations — a dead application versus a slow call — by sampling the process
list while the call is outstanding.

Invoked on the host as: python measure_open_latency.py <output_dir> [template_path]
"""

import json
import os
import subprocess
import sys
import time
import traceback

SW_DOC_PART = 1
DEFAULT_TEMPLATE = r"C:\CADLoop\templates\plate.sldprt"
SAMPLES = 6
SAMPLE_INTERVAL_S = 3


def solidworks_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"],
                         capture_output=True, text=True).stdout
    return "SLDWORKS.EXE" in out.upper()


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    template = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TEMPLATE
    report = {"template": template, "events": [], "open_seconds": None, "opened": None}
    started = time.time()

    def event(message):
        report["events"].append({"t_s": round(time.time() - started, 2), "event": message})

    sw = None
    try:
        import pythoncom
        import win32com.client

        long_ref_a = win32com.client.VARIANT(pythoncom.VT_I4 | pythoncom.VT_BYREF, 0)
        long_ref_b = win32com.client.VARIANT(pythoncom.VT_I4 | pythoncom.VT_BYREF, 0)

        sw = win32com.client.Dispatch("SldWorks.Application")
        event("dispatched")
        sw.Visible = False

        for _ in range(SAMPLES):
            event("alive=%s" % solidworks_running())
            time.sleep(SAMPLE_INTERVAL_S)

        open_started = time.time()
        try:
            document = sw.OpenDoc6(template, SW_DOC_PART, 0, "", long_ref_a, long_ref_b)
            report["open_seconds"] = round(time.time() - open_started, 2)
            report["opened"] = document is not None
            event("open returned after %ss" % report["open_seconds"])
        except Exception as error:
            report["open_seconds"] = round(time.time() - open_started, 2)
            report["opened"] = False
            event("open failed after %ss: %s" % (report["open_seconds"], error))
            event("alive after failure=%s" % solidworks_running())

    except Exception:
        event("unhandled exception:\n" + traceback.format_exc())
    finally:
        try:
            if sw is not None:
                sw.ExitApp()
        except Exception:
            pass
        with open(os.path.join(out_dir, "open_latency.json"), "w") as handle:
            json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
