#!/usr/bin/env bash
set -euo pipefail

echo "[+] Ensuring RTK binary is present..."
if ! command -v rtk &> /dev/null; then
    curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/develop/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "[+] RTK Version:"
rtk --version

echo "[+] Registering hooks for active agents..."
if [ -d "$HOME/.agents" ] || [ -d "$HOME/.gemini" ]; then
    rtk init --agent antigravity || true
fi

echo "[+] Current savings metrics:"
rtk gain || true
