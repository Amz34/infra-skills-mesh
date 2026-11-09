#!/usr/bin/env bash
# noVNC chain self-heal: Xvfb display -> x11vnc :5900 -> websockify :6080 -> cloudflared quick tunnel.
# Idempotent + SILENT on success (logs only when it takes an action) => safe on a 2-min systemd oneshot timer.
#
# Why not PID counts: websockify forks a child, so 2 PIDs = 1 logical process. We count process GROUPS.
#
# Env overrides (all optional):
#   DISPLAY_NUM=99 VNC_PORT=5900 WEB_PORT=6080
#   X11VNC_UNIT=munder-vnc.service NOVNC_UNIT=munder-novnc.service TUNNEL_UNIT=munder-vnc-tunnel.service
#   LOG=/tmp/novnc-chain-health.log
set -u
DISPLAY_NUM=${DISPLAY_NUM:-99}
VNC_PORT=${VNC_PORT:-5900}
WEB_PORT=${WEB_PORT:-6080}
X11VNC_UNIT=${X11VNC_UNIT:-munder-vnc.service}
NOVNC_UNIT=${NOVNC_UNIT:-munder-novnc.service}
TUNNEL_UNIT=${TUNNEL_UNIT:-munder-vnc-tunnel.service}
LOG=${LOG:-/tmp/novnc-chain-health.log}

say() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >>"$LOG"; }
u()   { systemctl --user "$@"; }
listen() { ss -ltn 2>/dev/null | grep -q ":$1 "; }

# 1) Xvfb display alive?  (bracket trick: apne shell ko match karne se bachao)
if ! pgrep -f "X[v]fb :$DISPLAY_NUM" >/dev/null; then
  say "Xvfb :$DISPLAY_NUM missing -> starting"
  Xvfb ":$DISPLAY_NUM" -screen 0 1600x900x24 >/dev/null 2>&1 &
  sleep 2
fi

# 2) websockify: exactly ONE process group must own the chain.
groups=$(ps -eo pgid,args | awk '/[w]ebsockify/ {print $1}' | sort -u | tr '\n' ' ')
ngroups=$(printf '%s' "$groups" | wc -w)
if [ "$ngroups" -ne 1 ]; then
  say "websockify process-groups=$ngroups [$groups] -> killing groups + restarting $NOVNC_UNIT"
  for g in $groups; do kill -- "-$g" 2>/dev/null || true; done
  sleep 1
  u restart "$NOVNC_UNIT" || say "restart $NOVNC_UNIT FAILED"
fi

# 3) x11vnc listening?
if ! listen "$VNC_PORT"; then
  say "port $VNC_PORT not listening -> restarting $X11VNC_UNIT"
  u restart "$X11VNC_UNIT" || say "restart $X11VNC_UNIT FAILED"
fi

# 4) noVNC web/websockify port listening?
if ! listen "$WEB_PORT"; then
  say "port $WEB_PORT not listening -> restarting $NOVNC_UNIT"
  u restart "$NOVNC_UNIT" || say "restart $NOVNC_UNIT FAILED"
fi

# 5) quick tunnel process alive? (process = ground truth; log lag kar sakta hai)
if ! pgrep -f "[c]loudflared tunnel --url http://127.0.0.1:$WEB_PORT" >/dev/null; then
  say "tunnel process missing -> restarting $TUNNEL_UNIT"
  u restart "$TUNNEL_UNIT" || say "restart $TUNNEL_UNIT FAILED"
fi
exit 0
