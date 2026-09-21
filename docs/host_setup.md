# CAD host setup

How to bring a Windows SOLIDWORKS host from nothing to a state where
`cadloop/orchestrator.py` can drive it. `cadloop/README.md` lists what the host
must provide; this file is how to make it provide that.

Written from the bring-up of the reference host (Windows 11 **Home**, SOLIDWORKS
2024 build 34.2.1, Python 3.12.10, `pywin32` 312). Steps that cost real time to
work out are marked **trap**.

## What you need before starting

- A Windows machine with SOLIDWORKS licensed and installed, reachable on the same
  LAN as the workstation. Wired or wireless does not matter; same subnet does.
- An account on that machine that can run SOLIDWORKS interactively.
- Its password. Not a Windows Hello PIN — see the trap in step 2.

## 1. Enable OpenSSH Server

In an **administrator** PowerShell on the host:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
New-NetFirewallRule -Name sshd -DisplayName "OpenSSH Server" -Enabled True `
  -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
ipconfig
```

Note the IPv4 address. Confirm from the workstation:

```bash
nc -zv -w3 <host-ip> 22
```

## 2. Key authentication

Generate a key on the workstation:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_pc -N "" -C "workstation-to-cad-host"
cat ~/.ssh/id_ed25519_pc.pub
```

**Trap — an administrator account does not read `~/.ssh/authorized_keys`.**
Windows OpenSSH sends members of the local Administrators group to a different
file, and silently ignores the usual one. On the host, in an admin PowerShell:

```powershell
Add-Content -Path "$env:ProgramData\ssh\administrators_authorized_keys" -Value "<paste the public key>"
icacls "$env:ProgramData\ssh\administrators_authorized_keys" /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
Restart-Service sshd
```

**Trap — the ACL is load-bearing.** If that file grants access to anything other
than `SYSTEM` and `Administrators`, sshd ignores it without logging a reason and
authentication fails as though the key were wrong. Verify:

```powershell
icacls "$env:ProgramData\ssh\administrators_authorized_keys"
```

It must show exactly `NT AUTHORITY\SYSTEM:(F)` and `BUILTIN\Administrators:(F)`.

Confirm `sshd_config` routes admins to that file — it is the default, but check:

```powershell
Get-Content "$env:ProgramData\ssh\sshd_config" | Select-String "Match Group","AuthorizedKeysFile"
```

There must be an uncommented `Match Group administrators` block pointing at
`__PROGRAMDATA__/ssh/administrators_authorized_keys`.

**Trap — a Windows Hello PIN is not the password.** A PIN is device-bound and
cannot authenticate a network logon, which is what PsExec performs later. If the
account signs in with a PIN, you need the underlying account password (the
Microsoft account password, if it is an MSA).

## 3. Get the username right

**Trap — this one is easy to lose an hour to.** On the host:

```powershell
whoami
```

It prints `HOSTNAME\username`. The part *before* the backslash is the computer
name, not the account. On the reference host `whoami` returned
`methamphetamine\admin`: the machine is `methamphetamine`, the account is
`admin`. Authenticating as the hostname produces
`Invalid user ... does not exist` in the sshd log while looking like a key
problem.

Verify from the workstation:

```bash
ssh -i ~/.ssh/id_ed25519_pc <account>@<host-ip> "whoami && hostname"
```

### If key auth still fails

Run sshd in the foreground and watch one connection attempt. On the host:

```powershell
Stop-Service sshd
& "C:\Windows\System32\OpenSSH\sshd.exe" -d -p 22
```

It prints the real rejection reason. It serves exactly one connection and exits,
so restart it for each attempt, and `Start-Service sshd` when finished. The `&`
call operator is required; without it PowerShell parses the quoted path as a
string and the `-d` flag as a syntax error.

## 4. Find the interactive session id

SOLIDWORKS' COM server will not start from a plain SSH session, so the worker is
launched into a logged-in session by id. Find it:

```bash
ssh -i ~/.ssh/id_ed25519_pc <account>@<host-ip> 'tasklist /V /FI "IMAGENAME eq explorer.exe"'
```

The `Session#` column is the id, normally `1`. It must be a real logged-in
desktop session; if nobody is signed in, there is nothing to launch into.

**Trap — Windows Home has no session tools.** `query user` and `qwinsta` do not
exist on Home editions, and there is no RDP host either, so `explorer.exe` is the
reliable way to read the session id and confirm someone is signed in.

## 5. Python and pywin32 on the host

```powershell
python --version      # 3.12.x, 64-bit to match SOLIDWORKS
pip install pywin32
where python           # note the full path for the config file
```

## 6. PsExec

```powershell
Invoke-WebRequest -Uri https://live.sysinternals.com/psexec.exe -OutFile C:\CADLoop\bin\psexec.exe
```

It needs `-accepteula` on every invocation, which `cadloop` already passes.

## 7. Host directories

```powershell
mkdir C:\CADLoop\bin, C:\CADLoop\jobs, C:\CADLoop\templates
```

## 8. Workstation configuration

Copy `cadloop/config.example.json` to `~/.config/sw_pc_credentials.json` (or
anywhere, and point `CADLOOP_HOST_CONFIG` at it) and fill it in:

```json
{
  "ssh_host": "192.168.1.10",
  "ssh_user": "admin",
  "ssh_key": "/Users/you/.ssh/id_ed25519_pc",
  "windows_user": "HOSTNAME\\admin",
  "windows_password": "...",
  "session_id": 1,
  "psexec_path": "C:\\CADLoop\\bin\\psexec.exe",
  "python_path": "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"
}
```

`chmod 600` it. It holds a plaintext password, so it stays outside version
control. Note that PsExec passes that password as a process argument on the host,
where anything that can read the process list can see it; that is a property of
the launch mechanism, not of where the file is stored.

## 9. Verify the chain

```bash
python cadloop/remote_run.py cadloop/author_template.py template_build_result.json
python cadloop/remote_run.py cadloop/inspect_template.py template_contract.json
python cadloop/orchestrator.py cadloop/jobs/plate-150x80x6.json
```

The last should exit zero with `"accepted": true` and land artifacts in
`cadloop/runs/plate-150x80x6/`. If it does, the chain is working end to end.

## MAPDL, for the FEA stage

MAPDL is a console application and does **not** need PsExec or an interactive
session. Launch it over plain SSH:

```bash
ssh -i <key> <user>@<host> \
  'cd /d C:\CADLoop\fea_run && "<ansys_exe>" -grpc -smp -np 2 -port 50052 -j feajob'
```

**Trap — `-smp` is required.** Without it the same executable starts in its
default distributed-memory mode, leaves a wrapper process sitting at a few
kilobytes of memory, and never binds the port. With `-smp` a real solver process
appears and the socket opens.

**Trap — the gRPC server binds `127.0.0.1` only.** No firewall rule will make it
reachable from the workstation. Tunnel it, and keep the tunnel open:

```bash
ssh -i <key> -L 50052:127.0.0.1:50052 -N <user>@<host>
```

Then `pip install -e ".[fea]"` on the workstation and connect to
`127.0.0.1:50052`. See `cadloop/fea/README.md`.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `Permission denied (publickey)` | admin account needs `administrators_authorized_keys`, with SYSTEM+Administrators-only ACL |
| `Invalid user <name>` in sshd log | authenticating as the hostname instead of the account; run `whoami` |
| `The user name or password is incorrect` from PsExec | a Windows Hello PIN is not the account password |
| `Server execution failed` (`CO_E_SERVER_EXEC_FAILURE`) on `Dispatch` | launched outside an interactive session; PsExec `-i <session>` with `-u`/`-p` |
| Job launches but no `result.json` | PsExec does not reliably return when an interactive-session process ends; poll for the file, which `orchestrator.py` does |
| `scp` reports a missing remote file that exists | backslashes in a remote path are escape characters; use forward slashes |
| COM calls fail repeatedly after the host slept or dropped off the network | the session's COM state is broken; kill stray `SLDWORKS.exe`/`sldworks_fs.exe` and retry, which recovered it without a reboot |
| MAPDL port never opens | missing `-smp`, or you are checking the LAN address instead of tunnelling `127.0.0.1` |
