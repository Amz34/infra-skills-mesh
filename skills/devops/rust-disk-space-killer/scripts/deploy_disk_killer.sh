#!/usr/bin/env bash
set -euo pipefail

echo "[+] Auditing storage architecture and binary toolchain..."
mkdir -p "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$PATH"

# Install dust if missing
if ! command -v dust &> /dev/null; then
    echo "[+] Installing dust (du-dust) aarch64..."
    curl -fsSL https://github.com/bootandy/dust/releases/download/v1.2.7/dust-v1.2.7-aarch64-unknown-linux-musl.tar.gz | tar -xz -C /tmp
    mv /tmp/dust-v1.2.7-aarch64-unknown-linux-musl/dust "$HOME/.local/bin/dust"
    chmod +x "$HOME/.local/bin/dust"
fi

# Install kondo if missing
if ! command -v kondo &> /dev/null; then
    echo "[+] Installing kondo aarch64..."
    curl -fsSL https://github.com/tbillington/kondo/releases/download/v0.9/kondo-aarch64-unknown-linux-gnu.tar.gz | tar -xz -C /tmp
    mv /tmp/kondo "$HOME/.local/bin/kondo"
    chmod +x "$HOME/.local/bin/kondo"
fi

echo "[+] Deployed Toolchain:"
dust --version
kondo --help | head -n 3

echo "[+] VM Root Filesystem Status:"
df -h /
