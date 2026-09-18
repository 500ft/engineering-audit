"""Job driver. Runs on the workstation, owns timeout and cleanup.

Uploads a job into its own directory on the SOLIDWORKS host, launches the
worker inside the host's interactive session, waits for `result.json`, and
retrieves the declared artifacts. The worker owns CAD correctness; this module
owns the transport, the deadline, and the guarantee that a reported success has
artifacts on local disk.

Invoked as: python orchestrator.py <job_spec.json>
"""

import json
import os
import subprocess
import sys
import time

CONFIG_PATH = os.environ.get(
    "CADLOOP_HOST_CONFIG", os.path.expanduser("~/.config/sw_pc_credentials.json")
)
JOBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs")
RUNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")
REMOTE_BASE = r"C:\CADLoop\jobs"
UPLOADS = ("worker.py", "volume.py")
POLL_INTERVAL_S = 3
LAUNCH_TIMEOUT_S = 20
DEFAULT_TIMEOUT_S = 1200


def load_config():
    with open(CONFIG_PATH) as handle:
        return json.load(handle)


def ssh_base(config):
    return ["ssh", "-i", config["ssh_key"],
            "%s@%s" % (config["ssh_user"], config["ssh_host"])]


def scp_base(config):
    return ["scp", "-i", config["ssh_key"]]


def remote(config, command, timeout=60):
    return subprocess.run(ssh_base(config) + [command],
                          capture_output=True, text=True, timeout=timeout)


def solidworks_running(config):
    probe = remote(config, 'tasklist /FI "IMAGENAME eq SLDWORKS.exe"')
    return "SLDWORKS.EXE" in probe.stdout.upper()


def clear_solidworks(config):
    """Remove any SOLIDWORKS process the run may have left behind.

    The worker exits the application itself; this is the backstop for a worker
    that died before its `finally` block ran.
    """
    remote(config, "taskkill /F /IM SLDWORKS.exe", timeout=30)
    remote(config, "taskkill /F /IM sldworks_fs.exe", timeout=30)


def upload(config, local_path, remote_dir_posix, name):
    """Copy one file to the host.

    Remote paths use forward slashes: scp treats a backslash as an escape
    character, so a Windows-style path silently resolves to the wrong name.
    """
    target = "%s@%s:%s/%s" % (config["ssh_user"], config["ssh_host"], remote_dir_posix, name)
    return subprocess.run(scp_base(config) + [local_path, target],
                          capture_output=True, text=True)


def download(config, remote_dir_posix, name, local_path):
    source = "%s@%s:%s/%s" % (config["ssh_user"], config["ssh_host"], remote_dir_posix, name)
    return subprocess.run(scp_base(config) + [source, local_path],
                          capture_output=True, text=True)


def fail(job_id, stage, message):
    return {"job_id": job_id, "status": "error", "stage": stage, "message": message}


def run_job(job_spec):
    config = load_config()
    job_id = job_spec["job_id"]
    timeout_s = job_spec.get("timeout_seconds", DEFAULT_TIMEOUT_S)

    local_dir = os.path.join(RUNS_DIR, job_id)
    os.makedirs(local_dir, exist_ok=True)
    job_path = os.path.join(local_dir, "job.json")
    with open(job_path, "w") as handle:
        json.dump(job_spec, handle, indent=2)

    if solidworks_running(config):
        return fail(job_id, "preflight",
                    "SLDWORKS.exe is already running on the host; close it before running a job")

    remote_dir = "%s\\%s" % (REMOTE_BASE, job_id)
    remote_dir_posix = remote_dir.replace("\\", "/")
    remote(config, "mkdir %s" % remote_dir)

    here = os.path.dirname(os.path.abspath(__file__))
    for name in UPLOADS:
        transfer = upload(config, os.path.join(here, name), remote_dir_posix, name)
        if transfer.returncode != 0:
            return fail(job_id, "upload", "could not upload %s: %s" % (name, transfer.stderr.strip()))
    transfer = upload(config, job_path, remote_dir_posix, "job.json")
    if transfer.returncode != 0:
        return fail(job_id, "upload", "could not upload job.json: %s" % transfer.stderr.strip())

    # A rerun with the same job_id must not read back a previous run's result:
    # the worker writes result.json atomically but never deletes a stale one,
    # and it is only ever created, not guaranteed absent, before a fresh launch.
    remote(config, 'del /Q "%s\\result.json"' % remote_dir)

    launch = (
        r'%s -accepteula -i %d -u %s -p %s "%s" %s\worker.py %s'
        % (config["psexec_path"], config["session_id"], config["windows_user"],
           config["windows_password"], config["python_path"], remote_dir, remote_dir)
    )
    try:
        subprocess.run(ssh_base(config) + [launch], capture_output=True, text=True,
                       timeout=LAUNCH_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        # PsExec does not reliably return when the process it started into an
        # interactive session finishes, so completion is detected by polling.
        pass

    deadline = time.time() + timeout_s
    produced = False
    while time.time() < deadline:
        probe = remote(config, 'if exist "%s\\result.json" echo READY' % remote_dir, timeout=15)
        if "READY" in probe.stdout:
            produced = True
            break
        time.sleep(POLL_INTERVAL_S)

    clear_solidworks(config)

    result_path = os.path.join(local_dir, "result.json")
    download(config, remote_dir_posix, "result.json", result_path)
    download(config, remote_dir_posix, "build.log", os.path.join(local_dir, "build.log"))

    if not os.path.exists(result_path):
        return fail(job_id, "orchestrator",
                    "no result.json after %ds" % timeout_s if not produced
                    else "result.json exists on the host but could not be retrieved")

    with open(result_path) as handle:
        result = json.load(handle)

    if result.get("job_id") != job_id:
        return fail(job_id, "orchestrator",
                    "result.json reports job_id %r; refusing to accept a stale artifact"
                    % result.get("job_id"))

    for name in result.get("artifacts", {}).values():
        download(config, remote_dir_posix, name, os.path.join(local_dir, name))

    if result.get("status") == "ok":
        missing = [name for name in result.get("artifacts", {}).values()
                   if not os.path.exists(os.path.join(local_dir, name))]
        if missing:
            result["status"] = "error"
            result["stage"] = "retrieve"
            result["message"] = "host reported success but these artifacts did not arrive: %s" % (
                ", ".join(missing))

    result["local_dir"] = local_dir
    return result


def main():
    spec_arg = sys.argv[1]
    if not os.path.exists(spec_arg):
        spec_arg = os.path.join(JOBS_DIR, spec_arg)
    with open(spec_arg) as handle:
        job_spec = json.load(handle)
    result = run_job(job_spec)
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
