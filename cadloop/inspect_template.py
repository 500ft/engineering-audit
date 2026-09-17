"""Read a template's equation table and report its parameter contract.

The equations a template actually contains are the contract `worker.py` drives.
Reading them back is the only way to confirm that an authored template declares
the global variables a job will ask for, and that each one is linked to a
driving dimension rather than left orphaned.

Invoked on the host as: python inspect_template.py <output_dir> [template_path]
"""

import json
import os
import sys
import traceback

SW_DOC_PART = 1
DEFAULT_TEMPLATE = r"C:\CADLoop\templates\plate.sldprt"


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    template = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TEMPLATE
    report = {"status": "error", "template": template, "equations": [],
              "global_variables": [], "linked_dimensions": [], "message": ""}

    sw = None
    try:
        import pythoncom
        import win32com.client

        long_ref_a = win32com.client.VARIANT(pythoncom.VT_I4 | pythoncom.VT_BYREF, 0)
        long_ref_b = win32com.client.VARIANT(pythoncom.VT_I4 | pythoncom.VT_BYREF, 0)

        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = False
        document = sw.OpenDoc6(template, SW_DOC_PART, 0, "", long_ref_a, long_ref_b)
        if document is None:
            report["message"] = "could not open %s" % template
            return

        equation_mgr = document.GetEquationMgr
        for index in range(equation_mgr.GetCount):
            text = equation_mgr.Equation(index) or ""
            report["equations"].append({"index": index, "text": text})
            stripped = text.strip()
            if not stripped.startswith('"'):
                continue
            name = stripped.split('"')[1]
            # A declaration assigns a literal; a link assigns a quoted variable.
            if '= "' in stripped:
                report["linked_dimensions"].append(name)
            else:
                report["global_variables"].append(name)

        report["status"] = "ok"
        sw.CloseDoc(document.GetTitle)

    except Exception:
        report["message"] = "unhandled exception:\n" + traceback.format_exc()
    finally:
        try:
            if sw is not None:
                sw.ExitApp()
        except Exception:
            pass
        with open(os.path.join(out_dir, "template_contract.json"), "w") as handle:
            json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
