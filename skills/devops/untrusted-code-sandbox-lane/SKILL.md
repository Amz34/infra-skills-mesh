---
name: untrusted-code-sandbox-lane
description: Use when sandboxing untrusted code or walling lane egress.
version: 1.0.0
author: Aamir's Hermes agent
license: MIT
metadata:
  hermes:
    tags: [devops, security, sandbox, nftables, secrets]
    related_skills: [attack-surface-self-audit, infra-hardening-crashproof, secrets-vault-ops]
---

# Untrusted-code sandbox + per-lane egress wall

## When to Use

- Code we did not write must execute: scraped snippets, model-generated scripts, third-party repo tests.
- A lane's egress must be limited to a domain allowlist (or its keys must never sit in its env).
- A sandbox "wall" appears not to work — check pitfalls 1 and 2 first.

Use when code we did not write must run (scraped snippets, model-generated scripts, third-party
repo tests) or when a systemd lane should only reach a domain allowlist. Reference build:
`~/ops/sandbox/` (safe_run.sh, egress_broker.py :8899, lane_egress.sh, README.md, qa_*.sh).
Read `~/ops/sandbox/README.md` first — it carries the measured QA table.

## 1. Running the code (container, host-agent path)

```bash
~/ops/sandbox/safe_run.sh --quota 64m --timeout 30 -- python3 script.py
~/ops/sandbox/safe_run.sh --dir ~/repo -- npm test      # bind mount, default
```
Flags that matter and why:
- `--user "$(id -u):$(id -g)"` — without it `--cap-drop ALL` makes container root
  capability-less: writes to a normal 775 dir fail, and world-writable dirs leave
  **root-owned files** on the host. Single most common sandbox bug.
- `--pids-limit 128` (fork-bomb fuse; verify with `cat /sys/fs/cgroup/pids.max` inside),
  `--ulimit nofile`, `--security-opt no-new-privileges`, `--cap-drop ALL`, `--read-only`
  + `--tmpfs /tmp`, `--network none` (default), `timeout -k 3 N`.
- `--quota 64m` → sparse ext4 image + `mount -o loop`, so a disk-filling runaway hits ENOSPC
  inside; cleanup in a trap (`docker rm -f`, umount, losetup -d). Needs passwordless sudo.

## 2. Egress wall for a lane

`egress_broker.py` = 127.0.0.1:8899: domain allowlist + secret injection, SIGHUP reload.
`lane_egress.sh apply <unit>` writes an **nftables** rule keyed on the unit's cgroup plus a
systemd drop-in exporting http_proxy/https_proxy/ALL_PROXY (upper+lower) and the broker CA.

```bash
~/ops/sandbox/lane_egress.sh selftest         # how the wall must be implemented HERE
~/ops/sandbox/lane_egress.sh apply my-lane.service
~/ops/sandbox/lane_egress.sh rollback my-lane.service
```
nft rule shape (root; path relative to cgroup root, level = component count):

    socket cgroupv2 level 5 "user.slice/user-1001.slice/user@1001.service/app.slice/lane.service" ip daddr != 127.0.0.0/8 drop

nft rules die on reboot → keep them in `/etc/agent-egress/rules.nft` and load them from a
root `oneshot` unit (`agent-egress-wall.service`, `RemainAfterExit=yes`, `Before=network-pre.target`).

## 3. Secrets never enter the lane

`secrets_rules.json` maps host → `{header, env}`; values live in `secrets.env` (0600). Plain HTTP
injects directly; HTTPS uses a leaf cert minted on demand and signed by `certs/ca.pem`, which the
lane trusts via `SSL_CERT_FILE`/`CURL_CA_BUNDLE`. Proof pattern: caller with the key **absent**
from env → direct request `403`, via broker `200`.

## Pitfalls (all hit in practice)

1. **systemd `IPAddressDeny=` is silently NOT enforced in user units** — the user manager has no
   CAP_BPF: the property is accepted, `BPFProgram` stays empty, packets flow. Always `selftest`
   before trusting it; use the nftables backend for `systemd --user` lanes. (Root units do enforce.)
2. **curl ignores UPPERCASE `HTTP_PROXY`** (browser-hijack legacy). Use lowercase `http_proxy`,
   `-x`, or `ALL_PROXY`. A "broken wall" is often just this.
3. `socket cgroupv2` needs the `nft_socket` module: `Could not process rule: No such file or
   directory` → `sudo modprobe nft_socket`.
4. `set -e` + `VAR="$( cmd && cmd )"`: an assignment whose command substitution returns non-zero
   kills the script silently. Use `if` blocks, never `$(cmd && cmd)` in an assignment.
5. Confirm the cgroup path at run time (`systemctl show -p ControlGroup --value`) — transient
   `systemd-run` units land in `app.slice` at the same depth as real ones.
6. Test a walled lane with a two-phase probe: the unit waits for a marker file, you apply the
   wall, then touch the marker. Reading output before its `done` sentinel = truncated evidence.
7. Loop-mounted quota needs `mkdir -p` on the **per-run** mount dir before `mount -o loop`
   (and after rollback: mounts=0, images=0).

## Honest limits

Root-owned wall vs. passwordless-sudo agent: it constrains lane *code*, not the agent itself —
governance gates still carry that. MITM CA key is its own secret. Containers share the host
kernel; gVisor/Firecracker is the next rung.
