# Crash-Proof Reboot + Post-Boot Auto-Verification (verified 2026-09-01)

Context: infra hardening (kernel update 1018→1020), "make sure this action should be crash proof".
Reboot from an agent session is BLOCKED — see below. Har security change reboot-secure hona chahiye.

## Agent reboot hardline block (IMPORTANT)
`sudo reboot` / `sudo shutdown -r` is on Hermes' **unconditional blocklist** — the agent can
NEVER reboot the VM, not even with --yolo / approvals off. This is by design (prevents an
agent from killing the host it runs on). The pattern that works:
1. Agent does ALL prep + verification (firewall persisted, services enabled, backup verified).
2. Agent installs a **post-boot auto-verification systemd service** (below) so the next
   session can prove everything came back.
3. Agent schedules nothing — tells the user: `sudo reboot` manually (30 sec, their terminal).
4. After reboot, read `/home/ubuntu/ops/logs/post-reboot-check.log` and verify.

## Pre-reboot checklist (crash-proof order)
1. **Backup verified FIRST** (upload + `rclone check --size-only` exact match) — kabhi
   unverified backup pe reboot mat karo.
2. **Firewall persistence check** — live rules == persisted rules:
   ```bash
   sudo iptables-save | grep harden > /tmp/live.txt
   sudo grep harden /etc/iptables/rules.v4 > /tmp/persisted.txt
   diff /tmp/live.txt /tmp/persisted.txt && echo IDENTICAL
   ```
   Requires `iptables-persistent` (rules auto-load at boot). Docker rules are re-created by
   Docker at boot — don't expect them in rules.v4.
3. **Services enabled**: docker restart policies (`always`/`unless-stopped`), hermes gateway
   `systemctl --user enable`, fail2ban jail enabled, tunnel units enabled.
4. **Kernel state**: `dpkg -l 'linux-image-*'` shows installed; `uname -r` shows ACTIVE.
   Naya kernel installed ho sakta hai but not active → reboot required. `apt list --upgradable`
   may show nothing for kernel if package already installed — check dpkg, not apt list.
5. Install post-boot check service (below), THEN hand `sudo reboot` to user.

## Post-boot verification service (pattern)
Systemd oneshot that runs once at boot, checks everything, logs to a file. Next agent
session reads the log instead of re-checking manually.

```bash
# /home/ubuntu/ops/scripts/post-reboot-check.sh
#!/bin/bash
LOG=/home/ubuntu/ops/logs/post-reboot-check.log
mkdir -p /home/ubuntu/ops/logs
exec > >(tee -a "$LOG") 2>&1
echo "===== POST-REBOOT CHECK $(date -u '+%Y-%m-%d %H:%M:%S UTC') ====="
sleep 20   # let network + docker settle
echo "--- KERNEL ---"; uname -r
echo "--- DOCKER ($(docker ps -q | wc -l) running) ---"; docker ps --format '{{.Names}}: {{.Status}}'
echo "--- HERMES GATEWAY (user) ---"; systemctl --user is-active hermes-gateway-invertio.service || echo INACTIVE
echo "--- TUNNELS ---"; systemctl list-units --type=service --state=active --no-pager | grep -i tunnel | awk '{print $1}'
echo "--- FIREWALL ---"; sudo iptables -L INPUT -n | grep -c harden | xargs echo "harden rules in INPUT:"
echo "--- FAIL2BAN ---"; sudo fail2ban-client status sshd 2>/dev/null | grep -E 'Banned|Currently' || echo "not running!"
echo "--- SSH ---"; systemctl is-active ssh
curl -s -o /dev/null -w "site1: HTTP %{http_code}\n" --max-time 15 https://example.pages.dev || echo "site1: UNREACHABLE"
echo "--- BACKUP TIMER ---"; systemctl list-timers sanad-backup.timer --no-pager 2>/dev/null | tail -2
echo "===== CHECK COMPLETE ====="
```

```ini
# /etc/systemd/system/sanad-postboot-check.service
[Unit]
Description=Post-reboot infra verification
After=network-online.target docker.service
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/bin/bash /home/ubuntu/ops/scripts/post-reboot-check.sh
User=ubuntu
WorkingDirectory=/home/ubuntu
[Install]
WantedBy=multi-user.target
```
Enable: `sudo systemctl daemon-reload && sudo systemctl enable sanad-postboot-check.service`

## Reboot result (2026-09-01 baseline)
- iptables-persistent + rules.v4 identical to live → reboot-safe firewall
- 6 docker containers (always/unless-stopped), hermes gateway user-level enabled+active,
  12 tunnel units, fail2ban sqlite3 (ban state persists across reboot), kernel 1020 pending.
