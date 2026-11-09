#!/usr/bin/env bash
# Disk-audit ground-truth scanner (single-root VM, e.g. hermes-vnic Oracle box).
# Writes raw evidence files to /tmp/audit/ — parse THESE (never remembered
# numbers) when building JSON/MD audit artifacts. Run as ubuntu user; sudo
# prompts once for root-owned dirs. Units: MB = MiB (du 1M blocks).
set -u
OUT=/tmp/audit
mkdir -p "$OUT"; cd "$OUT" || exit 1
date -u +%Y-%m-%dT%H:%M:%SZ > asof.txt

df -h / > df.txt
df / | awk 'NR==2 {print $2, $3, $4, $5}' > df_used.txt                      # total used avail pct (blocks)

# NOTE: du -s and --max-depth are mutually exclusive (conflict error + empty out).
du -xBM --max-depth=1 /home/ubuntu 2>/dev/null | sort -rn > home_top.txt
du -xBM --max-depth=1 /home/ubuntu/.hermes 2>/dev/null | sort -rn > hermes_top.txt
du -xBM --max-depth=1 /home/ubuntu/.hermes/profiles 2>/dev/null | sort -rn > profiles.txt
du -xBM --max-depth=1 /home/ubuntu/.hermes/skills /home/ubuntu/.hermes/profiles/*/skills 2>/dev/null | sort -rn > skills_totals.txt
find /home/ubuntu -xdev -type f -size +20M -printf '%s\t%p\n' 2>/dev/null | sort -rn > top_files.txt

# Plain du UNDERCOUNTS root-owned dirs -> /var gap vs df. sudo is mandatory:
du -xBM --max-depth=1 /tmp 2>/dev/null | sort -rn > tmp_top.txt
sudo du -xBM --max-depth=1 /var /var/lib/docker /var/lib/containerd 2>/dev/null | sort -rn > sys_top.txt

# Docker: containerd image store keeps layers in /var/lib/containerd, not docker/overlay2.
docker system df > docker_df.txt
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.ID}}' > docker_images.txt
docker ps -s --format '{{.Names}}\t{{.Image}}\t{{.Size}}' > docker_ps.txt

echo "--- evidence written to $OUT ---"
wc -l ./*.txt 2>/dev/null | tail -1
