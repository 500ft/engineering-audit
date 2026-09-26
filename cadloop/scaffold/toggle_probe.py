"""Read swInputDimValOnCreate without changing it. Runs on the host."""
import json, os, sys, traceback
import swhelpers as sw

out = {"status": "error"}
app = None
try:
    app, _, _ = sw.connect()
    out["toggle_10_swInputDimValOnCreate"] = bool(app.GetUserPreferenceToggle(10))
    out["status"] = "ok"
except Exception:
    out["error"] = traceback.format_exc()
finally:
    sw.shutdown(app)
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    open(os.path.join(d, "toggle_result.json"), "w").write(json.dumps(out, indent=2))
