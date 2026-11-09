---
name: firewatch-ops
description: "Use when testing or managing Fire & Smoke Watch."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [fire-lab, firewatch, computer-vision, yolo, cli]
---

# Fire & Smoke Watch Operations

Use when operating, managing, monitoring, testing, or triggering (kicking) the Fire & Smoke Watch (fire-lab) system in our infrastructure.

## Core Rules & Policies

1. **Autonomous Service Liveness**: Ensure `firewatch.service` (web console + YOLO detector) and `firewatch-tunnel.service` (Cloudflare public egress) are running on the server.
   - Status: `systemctl --user status firewatch` / `firewatch-tunnel`
   - Restart: `systemctl --user restart firewatch` / `firewatch-tunnel`
2. **Access Security**: The public tunnel link gives direct view of the camera stream and trigger privileges. Never write or hardcode the access code `FIREWATCH_CODE` in any public/tracked repos or general logs. Mask it as `[REDACTED]` or extract dynamically.
3. **Shortened Operational Links**: Cloudflare tunnels (`.trycloudflare.com`) are frequently long and are often blacklisted by common shorteners (like `is.gd`, `tinyurl.com`).
   - Use the pre-tested `clck.ru` provider which works beautifully.
   - Active shortened console link is: `https://clck.ru/3WHzcG`

## Triggers & Testing (Kicking Fire)

To kick fire alerts and verify the end-to-end Computer Vision (YOLO) and notification pipeline, use our expert CLI tool `/home/ubuntu/fire-lab/tools/kick_fire.py`.

### 1. Real YOLO Computer Vision Detection (Recommended)
This posts a moving/panning CV sequence of real fire frames to `/api/frame`. It exercises the full YOLO model, creates an event entry in the database, and fires configured alerts (Telegram, Email, WhatsApp).
```bash
/home/ubuntu/fire-lab/venv/bin/python /home/ubuntu/fire-lab/tools/kick_fire.py --mode frame
```
*Note: Cooldown is applied automatically on consecutive alerts from the same camera to prevent spam.*

### 2. Simulated Test Alert (No YOLO)
This bypasses CV inference and directly triggers a notification test for a custom camera name:
```bash
/home/ubuntu/fire-lab/venv/bin/python /home/ubuntu/fire-lab/tools/kick_fire.py --mode alert
```

## Verification Checks
- Check the console logs: `tail -n 100 /home/ubuntu/fire-lab/server.log`
- Retrieve tunnel and code links manually: `/home/ubuntu/fire-lab/deploy/phone_link.sh` or `/home/ubuntu/fire-lab/tools/mini_link.sh`
