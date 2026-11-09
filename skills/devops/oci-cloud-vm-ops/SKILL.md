---
name: oci-cloud-vm-ops
description: Use when managing OCI Always Free VMs/volumes.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [oci, oracle-cloud, always-free, boot-volume, storage, resize]
---

# OCI Cloud VM Ops (Oracle Cloud Infrastructure, Always Free)

## When to use
- Managing OCI instances / boot volumes via CLI: resize, grow, clone, terminate
- Always Free budget planning (200GB block storage, 4 OCPU, 24GB RAM per tenancy)
- Data forensics on another OCI box BEFORE terminating it (clone-mount)
- User's crash-proof consolidation pattern: ek hi box, ek hi volume, saari services ek jagah, kabhi bhi bina backup terminate nahi

## Environment (this VM)
- OCI CLI venv: `/home/ubuntu/oci-venv/bin/oci` (v3.91.0); config: `/home/ubuntu/.oci/config` + `oci_api_key.pem`
- Env prefix for EVERY call:
  `export OCI_CLI_AUTH=api_key OCI_CLI_CONFIG_FILE=/home/ubuntu/.oci/config OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True`
- Tenancy OCID (compartment target, no child compartments): `grep tenancy /home/ubuntu/.oci/config | cut -d= -f2`
- AD: `xWfz:ME-JEDDAH-1-AD-1`
- Main box: `instance-20260811-0141` (instance public IP 141.147.131.108; NAT-gateway egress IP 158.101.229.133), Ubuntu, 2 OCPU / 12GB (11GB usable, `free -g`), boot volume 200GB — **this is the FULL Always Free A1 entitlement, nothing spare** (see Shape resize + Always Free posture audit below). Uptime 5 weeks as of 2026-10-08.
- Working scripts + history: `/home/ubuntu/ops/scripts/oci-*.sh`, README: `/home/ubuntu/ops/README.md`

## Always Free storage budget (critical)
- 200GB block storage TOTAL per tenancy — sab boot volumes + block volumes count
- 4 OCPU + 24GB RAM total. Boot volume grow requires FREE quota: 100G→200G needs 100GB freed from other boxes first
- At 200GB used = limit reached; free-tier growth over — only cleanup/compression helps

## Shape (OCPU/RAM) resize — PAID here, check entitlement first
⚠️ **Corrected 2026-10-08 against the current Oracle doc:** Always Free A1 = *"the first 1,500 OCPU hours and 9,000 GB hours per month ... equivalent to 2 OCPUs and 12 GB of memory"*. Our box is 2 OCPU / 12 GB → it already consumes the ENTIRE free A1 allowance (1488/1500 OCPU-h, 8928/9000 GB-h per 744 h month). **4 OCPU / 24 GB is NOT free — it is a paid shape and there is no quota for a second A1 instance either.** Never present a resize as zero-cost without re-checking the doc.
Symptom that justifies it: sustained swap (GBs of `swpd`/VmSwap), `vmstat wa` ≥ 40% with idle `us`, load 1.5–2.0 on 2 vCPU — memory-bound while the CPU idles (diagnose with `saas-performance-diagnosis` → Step 0.7).
- **Never tell the user "I have no OCI creds, this is console-only" without checking.** The CLI venv, `~/.oci/config` and `oci_api_key.pem` live on this VM and are verified working (boot-volume ops 2026-08-31). Read-only proof to run first:
  `oci compute instance list --compartment-id <tenancy-OCID> --query 'data[].{n:"display-name",s:shape,o:"shape-config".ocpus,m:"shape-config".memoryInGBs}' --output table`
- Authoritative current shape-config comes from `/nproc` + `free -g` on the guest, or IMDS (`curl -s -H 'Authorization: Bearer Oracle' http://169.254.169.254/opc/v2/instance/`) — not from a service's `ps` output.
- Shape-config change (`oci compute instance update --instance-id <OCID> --shape-config '{"ocpus":4,"memoryInGBs":24}'`): **NOT yet verified from this box** — confirm with `--help`/console whether OCI requires a STOP/START for A1 shape changes before promising the user anything. Do not present it as zero-downtime the way boot-volume resize is.
- **A shape change can restart the box = our own gateway (and this conversation) goes down.** Explicit user approval + maintenance window first; then verify the guest sees it (`nproc`, `free -g`) and that swap/`wa` improved.
- Cheaper lever first if the user hesitates: stop un-used residents (open-webui, n8n, rsshub, demo containers) — ask which, never silently kill client services.

## Live boot volume resize (ZERO downtime — verified 2026-08-31)
OCI accepts `boot-volume update --size-in-gbs N` on a RUNNING instance — no stop needed.
1. Free storage quota first (terminate other boxes + delete their boot volumes)
2. `oci bv boot-volume update --boot-volume-id <BV> --size-in-gbs 200` → PROVISIONING → AVAILABLE
3. Guest rescan: `echo 1 | sudo tee /sys/block/sda/device/rescan` → `lsblk` shows new size
4. `sudo growpart /dev/sda 1` (online, partition grow)
5. `sudo resize2fs /dev/sda1` (online, mounted, no unmount)
6. Verify: `df -h /` shows grown size; uptime unchanged (no reboot happened)
Reusable: scripts/oci-grow-filesystem.sh does steps 3–5.

## Clone-mount forensics (data audit when SSH fails or read-only look needed)
SSH to Oracle Linux boxes often fails (publickey-only, no matching key) → clone route:
1. Create clone from source boot volume (source must be STOPPED; known-good scripts: ~/ops/scripts/oci-final-sweep-prep.sh + oci-final-sweep-archive.sh)
2. Attach to main Ubuntu box, then:
   `sudo vgchange -ay ocivolume` (Oracle Linux VG name; safe on Ubuntu host)
   `sudo mount -o ro /dev/mapper/ocivolume-root /mnt/oracle-root`
3. Audit, then DETACH + DELETE the clone (never leave clones attached)

## Pre-terminate crash-proof archive (user's HARD requirement)
Before ANY terminate: clone-mount the box → tar important paths → checksum → store on main box:
- Paths: /etc (incl. .ssh, shadow, passwd, hosts), /home, /root, /opt, /srv, /var/www
- `sudo tar --warning=no-file-changed -czf <name>.tar.gz <paths>`, then `sha256sum *.tar.gz > SHA256SUMS.txt`
- Store under `/home/ubuntu/oracle-server-archive/` (pattern from 2026-08-31)
- ONLY after archive verified → terminate instance + delete boot volume. Kabhi ulta nahi.

## Terminate + volume delete
- Use the phase scripts (oci-phaseB-cleanup.sh pattern) — exact flags live there; use preserve-boot-volume=false semantics so storage is freed
- Verify storage freed: boot-volume list shows only the main volume

## Pitfalls
- **OCID typos**: hand-copied OCIDs fail silently (NotAuthorizedOrNotFound / 404). ALWAYS fetch OCIDs programmatically (`--query`/`jq`) in the same script — never paste from memory. One-char typo = wasted cycle.
- **Inline multi-line shell commands fail** in the terminal tool (quoting/heredoc blocks, exit -1) → always write `oci-*.sh` script files and run those.
- **Guest disk size lags API**: after API resize, guest shows old size until `/sys/block/sda/device/rescan`.
- **LVM VG conflict**: Oracle Linux clones use VG `ocivolume`. Fine on Ubuntu host; WOULD collide with running root on an Oracle Linux target — mount clones only on the Ubuntu box.
- **XFS `noload` mount option is invalid** — plain `mount -o ro` works.
- **Free ARM ceiling is 2 OCPU / 12 GB** (current doc), not 4/24 — a box showing 2 OCPU/12GB is **already maxed**. Check `nproc` + `free -g` (or IMDS shape-config) before any spend recommendation, and never quote the old 4 OCPU/24GB figure.
- **`lsblk` can mislead** — use `df -h` on the actual mount point for real usage.

## Always Free posture audit & guard (verified 2026-10-08 — free trial ended)
Trigger: Oracle mails *"Your Oracle Cloud Free Trial promotion has ended"* → the tenancy drops to Always Free-only, non-Always-Free resources get reclaimed, and with no PAYG upgrade there is **no billing relationship at all → charges are impossible**; the real risks are (a) losing resources and (b) the idle-reclaim rule.
Baseline of this tenancy: 1 × A1.Flex 2 OCPU/12 GB RUNNING, 1 × 200 GB boot volume (exactly the cap), 0 block volumes, 1 × 200 GB boot-volume backup (5 free slots, count-based), egress ~21 GB/day / peak 45 GB (~630 GB/mo of 10 TB), 1 region (me-jeddah-1). Unused but usable-in-theory: 2 × E2.1.Micro — **blocked**, their 47 GB boot volumes must come out of the same already-full 200 GB pool (boot volumes can't shrink).
Idle-reclaim rule (the only way Oracle takes the box): during a 7-day period ALL THREE of CPU P95 <20%, network utilisation <20%, memory <20% (memory test applies to A1 only). Ours: CPU P95 89%, memory 70% → cannot be deemed idle. If it ever genuinely idles, keep a light workload or upgrade to PAYG (official mitigation; still $0 while usage stays inside Always Free).
Tools (all read-only): `ops/scripts/oci-free-guard.sh` (cron `40 5 * * *`, silent unless disk ≥85%, egress >300 GB/24 h, idle pair cpu_p95<25 AND mem<25, state ≠ RUNNING, or 0 backups; alerts Telegram 8843884232), `ops/scripts/free_tier_accounting.py --line` (egress/day + CPU P95 from sysstat; also usable as the yardstick for any "is the box idle?" question), `ops/scripts/oci-make-dr-backup.sh` (one Always Free boot backup). KB write-up: `ops/kb/oci-always-free-baseline.md`.
Audit pitfalls (learned the hard way):
- `sar -n DEV` on this build prints the **metric names in the header row and IFACE as the LAST column** — matching `$2 == enp0s6` yields *zero* samples and bogus egress numbers. Match the header token instead (see `free_tier_accounting.py`).
- `/var/log/sysstat/saNN` sorts lexicographically, so `sa30` (Sep 30) lands *after* `sa08` (Oct 8). Sort by mtime before slicing a "last 24 h" window; retention here is only ~9 days.
- `oci bv volume list` prints nothing at all for an empty list (not an error), and `oci limits resource-availability get` needs `--availability-domain` or it returns InvalidParameter.
- Tenancy IPs: 158.101.229.133 = NAT-gateway egress (what external allowlists see), 141.147.131.108 = instance public IP (SSH, ephemeral → changes after stop/start).
- Console-only check: the instance and boot volume carry the green **Always Free-eligible** label; no API exposes that flag. Disk sits at 77% of the fixed 200 GB (46 GB free) → cleanup is the only lever (`resource-guard.sh` already auto-reacts; docker had ~14 GB reclaimable).

## Related
- **RAM-starved box + a data-platform ask?** `local-lakehouse-ops` covers the MinIO/Iceberg/DuckDB/dbt/Spark lane on this VM; the free shape resize above is its gating decision — but **measure the lane first**: the light lane (MinIO + Iceberg + dbt + DuckDB) was measured at ~0.3 GB peak (2026-09-18), so it does NOT need a resize. Offload Spark/Airflow learning to free notebooks instead; resize only for a paid workload.
- ~/ops/scripts: oci-inventory.sh, oci-ids.sh, oci-phaseA.sh, oci-reattach.sh, oci-clone-cleanup.sh, oci-clone-delete.sh, oci-final-sweep-prep.sh, oci-final-sweep-archive.sh, oci-phaseB-cleanup.sh, post-resize-verify.sh
