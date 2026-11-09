#!/bin/bash
# OCI boot volume grew via API (oci bv boot-volume update --size-in-gbs N)
# but guest still shows old size. Run this on the instance: rescan -> grow partition -> grow fs.
# Online, mounted, ZERO downtime — no reboot needed. Verified 2026-08-31 on Ubuntu (linux-oracle kernel).
set -e
DEV=${1:-/dev/sda}
PART=${2:-1}
FSDEV="${DEV}${PART}"   # /dev/sda1

echo "== Before =="
lsblk -dn -o NAME,SIZE "$DEV"
df -h / | tail -1

echo "== Rescan disk (guest sees new size) =="
echo 1 | sudo tee "/sys/block/$(basename "$DEV")/device/rescan" >/dev/null
sleep 2
lsblk -dn -o NAME,SIZE "$DEV"

echo "== Grow partition =="
sudo growpart "$DEV" "$PART"

echo "== Grow filesystem (online) =="
sudo resize2fs "$FSDEV"

echo "== After =="
df -h / | tail -1
echo "Done. uptime check: uptime"
