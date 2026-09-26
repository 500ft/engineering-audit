#!/usr/bin/env python3
"""Run a scaffold script inside the host's interactive SOLIDWORKS session.

Workstation side. Uploads the script and its inputs, launches it through PsExec
into the logged-in session, polls for the result file, and retrieves it.

SOLIDWORKS' COM server will not start from a plain SSH session, which is why
PsExec is involved. PsExec does not reliably return when a process it started in
an interactive session finishes, which is why completion is detected by polling
rather than by the launch call returning.

usage: python run_host.py <script.py> <result.json> [timeout_s]
"""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("CADLOOP_HOST_CONFIG",
                                  os.path.expanduser("~/.config/sw_pc_credentials.json")))
HERE = Path(__file__).resolve().parent
REMOTE_DIR = r"C:\CADLoop\scaffold"
REMOTE_DIR_POSIX = REMOTE_DIR.replace("\\", "/")
UPLOADS = ("swhelpers.py", "redrive.py", "geometry.json", "oracle.json", "redrive.json")
POLL_S = 3
LAUNCH_TIMEOUT_S = 20


def config():
    if not CONFIG_PATH.is_file():
        raise SystemExit(
            "host config not found at %s.\n"
            "Copy cadloop/config.example.json there and fill it in, or point\n"
            "CADLOOP_HOST_CONFIG at it. It holds a password, so it lives outside\n"
            "version control and never arrives by cloning. See docs/host_setup.md."
            % CONFIG_PATH)
    return json.loads(CONFIG_PATH.read_text())


def ssh_base(c):
    return ["ssh", "-i", c["ssh_key"], "%s@%s" % (c["ssh_user"], c["ssh_host"])]


def remote(c, command, timeout=60):
    return subprocess.run(ssh_base(c) + [command], capture_output=True, text=True,
                          timeout=timeout)


def put(c, local: Path, name: str):
    # Remote paths use forward slashes: scp treats a backslash as an escape
    # character and the transfer fails against a mangled name.
    target = "%s@%s:%s/%s" % (c["ssh_user"], c["ssh_host"], REMOTE_DIR_POSIX, name)
    return subprocess.run(["scp", "-i", c["ssh_key"], str(local), target],
                          capture_output=True, text=True)


def get(c, name: str, local: Path):
    source = "%s@%s:%s/%s" % (c["ssh_user"], c["ssh_host"], REMOTE_DIR_POSIX, name)
    return subprocess.run(["scp", "-i", c["ssh_key"], source, str(local)],
                          capture_output=True, text=True)


def clear_solidworks(c):
    remote(c, "taskkill /F /IM SLDWORKS.exe", timeout=30)
    remote(c, "taskkill /F /IM sldworks_fs.exe", timeout=30)


def run(script: Path, result_name: str, timeout_s: int = 900):
    c = config()
    remote(c, "mkdir %s" % REMOTE_DIR)
    clear_solidworks(c)

    for name in UPLOADS:
        local = HERE / name
        if local.is_file():
            t = put(c, local, name)
            if t.returncode != 0:
                return {"status": "error", "message": "upload %s: %s" % (name, t.stderr.strip())}
    t = put(c, script, script.name)
    if t.returncode != 0:
        return {"status": "error", "message": "upload %s: %s" % (script.name, t.stderr.strip())}

    # A stale result from a previous run must not be read back as this one's.
    remote(c, 'del /Q "%s\\%s"' % (REMOTE_DIR, result_name))

    launch = ('%s -accepteula -i %d -u %s -p %s "%s" %s\\%s %s'
              % (c["psexec_path"], c["session_id"], c["windows_user"],
                 c["windows_password"], c["python_path"], REMOTE_DIR, script.name,
                 REMOTE_DIR))
    try:
        subprocess.run(ssh_base(c) + [launch], capture_output=True, text=True,
                       timeout=LAUNCH_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        pass

    deadline = time.time() + timeout_s
    produced = False
    while time.time() < deadline:
        probe = remote(c, 'if exist "%s\\%s" echo READY' % (REMOTE_DIR, result_name),
                       timeout=15)
        if "READY" in probe.stdout:
            produced = True
            break
        time.sleep(POLL_S)

    clear_solidworks(c)
    if not produced:
        return {"status": "error", "message": "%s not produced within %ds" % (result_name, timeout_s)}

    local = HERE / result_name
    get(c, result_name, local)
    if not local.is_file():
        return {"status": "error", "message": "%s could not be retrieved" % result_name}
    return json.loads(local.read_text())


def fetch(name: str):
    """Retrieve one artifact the host produced, such as a .sldprt or .step."""
    return get(config(), name, HERE / name)


def main():
    script = Path(sys.argv[1]).resolve()
    result_name = sys.argv[2]
    timeout_s = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    out = run(script, result_name, timeout_s)
    print(json.dumps(out, indent=2))
    return 0 if out.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
