#!/usr/bin/env python3
"""Infra capability audit - read-only gap scorecard for the Hermes VM.

Compares what this box actually HAS against the capability layers a cloud
data-engineering / agentic-AI reference stack describes (compute, object
storage, lakehouse formats, distributed compute, warehouse, queue, IaC,
orchestration, DR, secrets, ops surface).

Read-only: it probes, imports, stats and greps. It never writes, installs,
starts or mutates anything, and it never prints secret VALUES - only the
existence and shape of credential files and env var NAMES.

Usage:
    python3 infra_capability_audit.py                 # text report
    python3 infra_capability_audit.py --json          # machine-readable
    python3 infra_capability_audit.py --severity gap  # only gap rows
    python3 infra_capability_audit.py --fail-on-critical   # exit 1 if any
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
OK, PARTIAL, GAP = "ok", "partial", "gap"


def sh(cmd, timeout=20):
    """Run a shell command, return (rc, stdout). Never raises."""
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as exc:  # timeout, missing binary, anything
        return 127, str(exc)


# --- instrument calibration -------------------------------------------------
# A PATH-only probe reports false gaps on this box: every tool of interest is installed in a
# per-project venv (~/.venvs/<name>/bin) or a user-local bin dir, and not one of them is on
# the login PATH. The first run of this audit scored "lakehouse/columnar libs: gap",
# "cloud CLI + creds: partial(clis=none)" and "object storage: s3_clients=none" purely
# because of that blindness. So resolve binaries and modules the way this box actually
# installs them: PATH first, then known bin dirs, then every venv interpreter.
def _bin_dirs():
    d = [Path(p) for p in os.environ.get("PATH", "").split(":") if p]
    d += [p.parent for p in sorted(HOME.glob(".venvs/*/bin/python"))]
    d += [HOME / ".local/bin", HOME / ".hermes/node/bin"]
    return [p for p in d if p.is_dir()]


BIN_DIRS = _bin_dirs()
INTERPRETERS = [sys.executable] + [str(p) for p in sorted(HOME.glob(".venvs/*/bin/python"))]


def which_any(name):
    for d in BIN_DIRS:
        c = d / name
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)
    return shutil.which(name)


def has(*names):
    return [n for n in names if which_any(n)]


_SPEC_CODE = (
    "import importlib.util as u, sys\n"
    "for m in sys.argv[1:]:\n"
    "    try:\n"
    "        if u.find_spec(m): print(m)\n"
    "    except Exception: pass\n")


def py_imports(mods):
    """Modules installed in ANY interpreter here, not just the one running this script."""
    found = set()
    for py in INTERPRETERS:
        if not os.path.exists(py):
            continue
        try:
            p = subprocess.run([py, "-c", _SPEC_CODE] + list(mods),
                               capture_output=True, text=True, timeout=45)
            found.update(x for x in p.stdout.split() if x)
        except Exception:
            continue
        if len(found) >= len(mods):
            break
    return [m for m in mods if m in found]


def human_bytes(n):
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024:
            return "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f PiB" % n


def newest(path_glob, files_only=True):
    try:
        items = [p for p in HOME.glob(path_glob) if (p.is_file() or not files_only)]
        if not items:
            return None
        return max(items, key=lambda p: p.stat().st_mtime)
    except Exception:
        return None


def age_days(path):
    try:
        return (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 86400.0
    except Exception:
        return None


# --------------------------------------------------------------------------
# checks: each returns (status, evidence_string)
# --------------------------------------------------------------------------

def c_host_capacity():
    cores = os.cpu_count() or 0
    mebib = 0.0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                mebib = int(line.split()[1]) / 1024.0
    except Exception:
        pass
    free = shutil.disk_usage(str(HOME)).free if HOME.exists() else 0
    ev = "cores=%d ram=%.1fGiB free_disk=%s" % (cores, mebib / 1024.0, human_bytes(free))
    if cores >= 4 and mebib / 1024.0 >= 8:
        return OK, ev
    if cores >= 2:
        return PARTIAL, ev + " (small VM class)"
    return GAP, ev


def c_orchestrator():
    found = has("docker", "podman", "nerdctl", "k3s", "kubectl")
    if not found:
        return GAP, "no container runtime on PATH"
    rc, out = sh("docker ps --format '{{.Names}}' 2>/dev/null")
    running = [l for l in out.split() if l and not l.startswith("permission")]
    return OK, "bins=%s running_containers=%d" % (",".join(found), len(running))


def c_cluster_nodes():
    bins = has("oci", "aws", "gcloud", "az")
    if not bins:
        return GAP, "no cloud CLI on PATH (single self-managed host)"
    oci_bin = which_any("oci")
    if oci_bin:
        rc, out = sh("oci compute instances list --query 'data[].displayName' 2>&1",
                     timeout=45)
        if rc == 0 and "[" in out:
            n = out.count('"') // 2
            return (OK if n > 1 else PARTIAL), "oci CLI present, instances=%d" % n
    return PARTIAL, "cloud CLI present (%s) but listing failed/unavailable" % ",".join(bins)


def c_spof():
    """Every critical workload on one node is the real risk."""
    rc, out = sh("docker ps --format '{{.Names}}' 2>/dev/null")
    containers = len([l for l in out.split() if l and not l.startswith("permission")])
    units = 0
    rc2, out2 = sh("systemctl --user list-units --type=service --state=running "
                   "--no-legend --plain 2>/dev/null")
    if rc2 == 0:
        units = len([l for l in out2.splitlines() if l.strip()])
    ev = "containers=%d user_services=%d on 1 host" % (containers, units)
    if containers + units > 20:
        return GAP, ev + " -> single point of failure"
    if containers + units > 5:
        return PARTIAL, ev
    return OK, ev


def c_cloud_cli():
    bins = has("aws", "oci", "gcloud", "az")
    creds = [p for p in (".aws", ".oci", ".config/gcloud", ".azure")
             if (HOME / p).exists()]
    ev = "clis=%s cred_dirs=%s" % (",".join(bins) or "none", ",".join(creds) or "none")
    if bins and creds:
        return OK, ev
    if creds or bins:
        return PARTIAL, ev
    return GAP, ev


def c_object_storage():
    remotes = []
    rc, out = sh("rclone listremotes 2>/dev/null")
    if rc == 0:
        remotes = [l.strip().rstrip(":") for l in out.splitlines() if l.strip()]
    s3 = has("s5cmd", "mc", "aws")
    ev = "rclone_remotes=%s s3_clients=%s" % (",".join(remotes) or "none",
                                              ",".join(s3) or "none")
    if any(r for r in remotes) and s3:
        return OK, ev
    if remotes or s3:
        return PARTIAL, ev + " (offsite target, not a data-lake tier)"
    return GAP, ev


def c_lakehouse_libs():
    found = py_imports(["pyarrow", "duckdb", "polars", "delta", "pyiceberg"])
    counts = len(found)
    return (OK if counts >= 3 else PARTIAL if counts else GAP), "importable=%s" % (
        ",".join(found) or "none")


def c_distributed_compute():
    bins = has("spark-submit", "pyspark", "dask", "ray")
    mods = py_imports(["pyspark", "dask", "ray"])
    ev = "bins=%s libs=%s" % (",".join(bins) or "none", ",".join(mods) or "none")
    return (OK if (bins or mods) else GAP), ev


def c_warehouse():
    bins = has("dbt", "snowsql", "clickhouse-client", "psql", "bq")
    mods = py_imports(["dbt", "snowflake", "google.cloud.bigquery", "clickhouse_driver"])
    ev = "bins=%s libs=%s" % (",".join(bins) or "none", ",".join(mods) or "none")
    if "dbt" in bins and (bins or mods):
        return OK, ev
    if bins or mods:
        return PARTIAL, ev + " (a database, no modelling/warehouse layer)"
    return GAP, ev


def c_queue_stream():
    bins = has("redis-cli", "kafka-topics.sh", "rabbitmqctl", "nats")
    rc, out = sh("ss -ltn 2>/dev/null | grep -E ':(6379|9092|5672|4222|5432|3306)'",
                 timeout=15)
    ports = sorted({l.split()[3].rsplit(":", 1)[-1] for l in out.splitlines() if l.split()})
    ev = "clients=%s listening_ports=%s" % (",".join(bins) or "none",
                                            ",".join(ports) or "none")
    if bins or {"6379", "9092", "5672", "4222"} & set(ports):
        return OK, ev
    if ports:
        return PARTIAL, ev
    return GAP, ev + " -> async work = cron + files + webhooks"


def c_scheduler():
    bins = has("airflow", "dagster", "prefect")
    n8n = (HOME / "n8n").exists() or shutil.which("n8n")
    cron_jobs = 0
    try:
        data = json.loads((HOME / ".hermes/cron/jobs.json").read_text())
        cron_jobs = len(data if isinstance(data, list) else data.get("jobs", []))
    except Exception:
        pass
    ev = "de_engines=%s n8n=%s hermes_cron_jobs=%d" % (",".join(bins) or "none",
                                                       bool(n8n), cron_jobs)
    if bins:
        return OK, ev
    if n8n or cron_jobs:
        return PARTIAL, ev
    return GAP, ev


def c_workflow_engine():
    n8n_ports = sh("ss -ltn 2>/dev/null | grep -E ':(5678)'", timeout=15)[1]
    has_n8n = bool(n8n_ports.strip()) or (HOME / "n8n").exists()
    webhooks = 0
    for p in list(HOME.glob("*webhook*")) + list(HOME.glob(".hermes/**/webhook*")):
        webhooks += 1
    return (OK if has_n8n else PARTIAL), "n8n_port=%s webhook_artifacts=%d" % (
        bool(n8n_ports.strip()), webhooks)


def c_iac():
    bins = has("terraform", "tofu", "pulumi", "cdk")
    files = 0
    for pat in ("**/*.tf", "**/Pulumi.yaml", "**/cdk.json"):
        try:
            files += len([p for p in HOME.glob(pat) if p.is_file()][:50])
        except Exception:
            pass
    ev = "bins=%s config_files=%d" % (",".join(bins) or "none", files)
    if bins and files:
        return OK, ev
    if bins or files:
        return PARTIAL, ev
    return GAP, ev + " -> infra hand-typed (bash + systemd), not reproducible"


def c_operational_db():
    found = []
    total = 0
    for pat in (".hermes/state.db", ".hermes/profiles/*/state.db",
                "*.db", "clients/*/*.db", "projects/*/*.db", "ops/*.db"):
        for p in HOME.glob(pat):
            try:
                if p.is_file() and p.stat().st_size > 4096:
                    found.append(p)
                    total += p.stat().st_size
            except Exception:
                pass
    pg = sh("ss -ltn 2>/dev/null | grep -E ':(5432|3306)'", timeout=15)[1].strip()
    uniq = sorted({str(p.relative_to(HOME)) for p in found})
    ev = "sqlite=%d (%s) server_db_port=%s" % (len(uniq), human_bytes(total),
                                               bool(pg))
    if len(uniq) > 1 and pg:
        return OK, ev
    if uniq:
        return PARTIAL, ev
    return GAP, ev


def c_vector_store():
    dirs = [p for p in HOME.glob("**/chroma*") if p.is_dir()][:20]
    docker_vec = sh("docker ps --format '{{.Names}}' 2>/dev/null | grep -iE "
                    "'chroma|qdrant|weaviate|milvus'")[1].strip()
    size = 0
    for d in dirs:
        try:
            for f in d.rglob("*"):
                if f.is_file():
                    size += f.stat().st_size
        except Exception:
            pass
    ev = "chroma_dirs=%d size=%s container=%s" % (len(dirs), human_bytes(size),
                                                  bool(docker_vec))
    if dirs or docker_vec:
        return PARTIAL, ev
    return GAP, ev


def c_analytics_formats():
    n = 0
    for pat in ("ops/**/*.parquet", "projects/**/*.parquet", "clients/**/*.parquet",
                "brains/**/*.parquet", "**/*.iceberg"):
        try:
            n += len([p for p in HOME.glob(pat) if p.is_file()][:200])
        except Exception:
            pass
    return (OK if n else GAP), "columnar_files=%d" % n


def c_backup_volume():
    best, total = None, 0
    for pat in ("ops/backups/*", "backups/*"):
        for p in HOME.glob(pat):
            try:
                if p.is_file():
                    total += p.stat().st_size
                else:
                    for f in p.rglob("*"):
                        if f.is_file():
                            total += f.stat().st_size
            except Exception:
                pass
    best = newest("ops/backups/*")
    days = age_days(best) if best else None
    ev = "local_backup=%s newest_age=%s" % (human_bytes(total),
                                            "n/a" if days is None else "%.1fd" % days)
    if total and days is not None and days <= 3:
        return OK, ev
    if total:
        return PARTIAL, ev
    return GAP, ev


def c_ci():
    repos = 0
    with_ci = 0
    for gitdir in HOME.glob("*/.git"):
        repos += 1
        if (gitdir.parent / ".github/workflows").exists():
            with_ci += 1
    for gitdir in HOME.glob("*/*/.git"):
        repos += 1
        if (gitdir.parent / ".github/workflows").exists():
            with_ci += 1
    ev = "repos=%d with_github_actions=%d" % (repos, with_ci)
    if repos and with_ci >= max(1, repos // 2):
        return OK, ev
    if with_ci:
        return PARTIAL, ev
    return GAP, ev


def c_offsite_dr():
    remotes = []
    rc, out = sh("rclone listremotes 2>/dev/null")
    if rc == 0:
        remotes = [l.strip().rstrip(":") for l in out.splitlines() if l.strip()]
    if not remotes:
        return GAP, "no rclone remote configured"
    remote = remotes[0]
    size = None
    for folder in ("", "Hermes-Telegram-Backup/", "backups/"):
        rc2, out2 = sh("rclone size '%s:%s' --json --timeout 60s" % (remote, folder),
                       timeout=90)
        if rc2 == 0 and out2.strip().startswith("{"):
            try:
                info = json.loads(out2.strip().splitlines()[0])
                size = info.get("bytes")
                break
            except Exception:
                pass
    if size:
        return OK, "remote=%s bytes=%s" % (remote, human_bytes(size))
    return PARTIAL, "remote=%s present but size probe failed" % remote


def c_secrets_hygiene():
    vault = has("vault", "sops", "age", "gpg", "pass")
    secret_files = []
    for pat in (".aws/credentials", ".config/rclone/rclone.conf", ".oci/config",
                "clients/*/.secrets", ".hermes/config.yaml", ".env"):
        for p in HOME.glob(pat):
            if p.exists():
                secret_files.append(str(p.relative_to(HOME)))
    ev = "vault_tools=%s secret_files_on_disk=%d (names withheld)" % (
        ",".join(vault) or "none", len(secret_files))
    if vault and len(secret_files) <= 2:
        return OK, ev
    if vault:
        return PARTIAL, ev
    return GAP, ev + " -> no rotation/vault"


def c_verify_ledger():
    hits = []
    for pat in ("ops/verify/*", "ops/observability/*", "ops/evals/*"):
        for p in HOME.glob(pat):
            hits.append(p.name)
    return (PARTIAL if hits else GAP), "verify_artifacts=%d" % len(hits)


def c_model_providers():
    names = [k for k in os.environ if k.endswith(("_API_KEY", "_TOKEN", "API_KEY"))
             and len(k) > 6]
    return (OK if names else GAP), "provider_env_names=%d (values withheld)" % len(names)


def c_agent_ops():
    skills = 0
    try:
        skills = len([p for p in HOME.glob(".hermes/skills/**/SKILL.md")])
    except Exception:
        pass
    cron_jobs = 0
    try:
        data = json.loads((HOME / ".hermes/cron/jobs.json").read_text())
        cron_jobs = len(data if isinstance(data, list) else data.get("jobs", []))
    except Exception:
        pass
    ev = "skills=%d cron_jobs=%d" % (skills, cron_jobs)
    return (OK if skills > 20 else PARTIAL if skills else GAP), ev


CHECKS = [
    ("Compute & resilience", "host capacity (cpu/ram/disk)", c_host_capacity, False),
    ("Compute & resilience", "container orchestrator", c_orchestrator, False),
    ("Compute & resilience", "multi-node / cluster", c_cluster_nodes, False),
    ("Compute & resilience", "single point of failure", c_spof, True),
    ("Cloud & data services", "cloud CLI + credentials", c_cloud_cli, False),
    ("Cloud & data services", "object storage tier", c_object_storage, False),
    ("Cloud & data services", "lakehouse/columnar libs", c_lakehouse_libs, False),
    ("Cloud & data services", "distributed compute", c_distributed_compute, True),
    ("Cloud & data services", "warehouse / modelling", c_warehouse, False),
    ("Cloud & data services", "queue / event bus", c_queue_stream, True),
    ("Orchestration", "scheduler (airflow-class)", c_scheduler, False),
    ("Orchestration", "workflow/webhook engine", c_workflow_engine, False),
    ("Orchestration", "infrastructure as code", c_iac, True),
    ("Data assets", "operational data store", c_operational_db, False),
    ("Data assets", "vector / RAG store", c_vector_store, False),
    ("Data assets", "analytics-ready formats", c_analytics_formats, False),
    ("Data assets", "backup volume + freshness", c_backup_volume, False),
    ("Delivery & ops", "CI pipelines", c_ci, False),
    ("Delivery & ops", "offsite DR replication", c_offsite_dr, True),
    ("Delivery & ops", "secrets hygiene", c_secrets_hygiene, False),
    ("Delivery & ops", "verify / observability ledger", c_verify_ledger, False),
    ("Delivery & ops", "model provider keys", c_model_providers, False),
    ("Delivery & ops", "agent-ops surface", c_agent_ops, False),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--severity", choices=["all", OK, PARTIAL, GAP, "critical"],
                    default="all")
    ap.add_argument("--fail-on-critical", action="store_true")
    args = ap.parse_args()

    rows = []
    for layer, name, fn, critical in CHECKS:
        try:
            status, evidence = fn()
        except Exception as exc:
            status, evidence = GAP, "probe error: %s" % exc
        rows.append({"layer": layer, "check": name, "status": status,
                     "critical": critical, "evidence": evidence})

    counts = {OK: 0, PARTIAL: 0, GAP: 0}
    for r in rows:
        counts[r["status"]] += 1
    crit_gaps = [r for r in rows if r["critical"] and r["status"] == GAP]
    summary = {"total": len(rows), "ok": counts[OK], "partial": counts[PARTIAL],
               "gap": counts[GAP], "critical_gaps": len(crit_gaps)}
    payload = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "host": os.uname().nodename, "summary": summary, "checks": rows}

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("Infra capability audit - %s" % payload["generated"])
        cur = None
        for r in rows:
            if args.severity != "all":
                if args.severity == "critical" and not (r["critical"]
                                                        and r["status"] == GAP):
                    continue
                if args.severity in (OK, PARTIAL, GAP) and r["status"] != args.severity:
                    continue
            if r["layer"] != cur:
                cur = r["layer"]
                print("\n[%s]" % cur)
            mark = {"ok": "OK  ", "partial": "PART", "gap": "GAP "}[r["status"]]
            flag = "!" if (r["critical"] and r["status"] == GAP) else " "
            print("  %s%s %-32s %s" % (mark, flag, r["check"], r["evidence"]))
        print("\nsummary: total=%(total)d ok=%(ok)d partial=%(partial)d gap=%(gap)d "
              "critical_gaps=%(critical_gaps)d" % summary)
        if crit_gaps:
            print("critical gaps:")
            for r in crit_gaps:
                print("  ! %s - %s" % (r["check"], r["evidence"]))

    if args.fail_on_critical and crit_gaps:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
