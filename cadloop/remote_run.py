"""Run one host-side script inside the SOLIDWORKS host's interactive session.

Used for the scripts that are not jobs: authoring a template, reading a
template's equation contract, and measuring open latency. Jobs go through
`orchestrator.py`, which additionally enforces the job contract.

Invoked as: python remote_run.py <local_script.py> <result_filename> [timeout_s]
"""

import json
import os
import subprocess
import sys
import time

import orchestrator

REMOTE_DIR = r"C:\CADLoop\bin"
REMOTE_DIR_POSIX = REMOTE_DIR.replace("\\", "/")
SUPPORT_FILES = ("volume.py",)


def run(local_script, result_filename, timeout_s=1200):
    config = orchestrator.load_config()
    here = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(local_script)

    orchestrator.remote(config, "mkdir %s" % REMOTE_DIR)
    orchestrator.clear_solidworks(config)

    for name in SUPPORT_FILES + (script_name,):
        source = local_script if name == script_name else os.path.join(here, name)
        transfer = orchestrator.upload(config, source, REMOTE_DIR_POSIX, name)
        if transfer.returncode != 0:
            return {"status": "error", "message": "could not upload %s: %s"
                    % (name, transfer.stderr.strip())}

    remote_result = "%s\\%s" % (REMOTE_DIR, result_filename)
    orchestrator.remote(config, 'del /Q "%s"' % remote_result)

    launch = (
        r'%s -accepteula -i %d -u %s -p %s "%s" %s\%s %s'
        % (config["psexec_path"], config["session_id"], config["windows_user"],
           config["windows_password"], config["python_path"], REMOTE_DIR, script_name, REMOTE_DIR)
    )
    try:
        subprocess.run(orchestrator.ssh_base(config) + [launch],
                       capture_output=True, text=True, timeout=orchestrator.LAUNCH_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        pass

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        probe = orchestrator.remote(config, 'if exist "%s" echo READY' % remote_result, timeout=15)
        if "READY" in probe.stdout:
            break
        time.sleep(orchestrator.POLL_INTERVAL_S)
    else:
        orchestrator.clear_solidworks(config)
        return {"status": "error", "message": "%s was not produced within %ds"
                % (result_filename, timeout_s)}

    orchestrator.clear_solidworks(config)
    local_result = os.path.join(orchestrator.RUNS_DIR, result_filename)
    os.makedirs(orchestrator.RUNS_DIR, exist_ok=True)
    orchestrator.download(config, REMOTE_DIR_POSIX, result_filename, local_result)
    if not os.path.exists(local_result):
        return {"status": "error", "message": "%s could not be retrieved" % result_filename}

    with open(local_result) as handle:
        return json.load(handle)


def main():
    script = sys.argv[1]
    result_filename = sys.argv[2]
    timeout_s = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
    print(json.dumps(run(script, result_filename, timeout_s), indent=2))


if __name__ == "__main__":
    main()
