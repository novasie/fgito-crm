#!/usr/bin/env bash
# FGITO CRM — SSH tunnel from this Mac to the shared MariaDB on the Azure VM.
#
# Forwards local 127.0.0.1:3307  ->  VM 127.0.0.1:3306, so bench (configured with
# db_host=127.0.0.1, db_port=3307) reaches the remote DB securely over SSH.
# Uses autossh so it auto-reconnects after Wi-Fi drops / sleep.
#
# Prereqs on this Mac:  brew install autossh   AND this Mac's SSH key added to the VM.
#
# Usage:
#   ./db-tunnel.sh azureuser 20.40.50.60
#   VM_USER=azureuser VM_HOST=20.40.50.60 ./db-tunnel.sh
#   LOCAL_PORT=3307 ./db-tunnel.sh azureuser myvm.example.com     # override local port
#
# Stop it:   pkill -f "3307:127.0.0.1:3306"

set -euo pipefail

VM_USER="${1:-${VM_USER:-}}"
VM_HOST="${2:-${VM_HOST:-}}"
LOCAL_PORT="${LOCAL_PORT:-3307}"
REMOTE_PORT="${REMOTE_PORT:-3306}"

if [[ -z "$VM_USER" || -z "$VM_HOST" ]]; then
  echo "Usage: $0 <vm_user> <vm_host>   (or set VM_USER / VM_HOST env vars)" >&2
  exit 1
fi

if ! command -v autossh >/dev/null 2>&1; then
  echo "autossh not found. Install it:  brew install autossh" >&2
  exit 1
fi

# Already up? (idempotent — don't stack tunnels)
if pgrep -f "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" >/dev/null 2>&1; then
  echo "Tunnel already running on 127.0.0.1:${LOCAL_PORT}. Nothing to do."
  exit 0
fi

echo "Opening tunnel: 127.0.0.1:${LOCAL_PORT} -> ${VM_USER}@${VM_HOST} -> 127.0.0.1:${REMOTE_PORT}"
AUTOSSH_GATETIME=0 autossh -M 0 -fN \
  -o "ServerAliveInterval=30" \
  -o "ServerAliveCountInterval=3" \
  -o "ExitOnForwardFailure=yes" \
  -L "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" \
  "${VM_USER}@${VM_HOST}"

sleep 1
if pgrep -f "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" >/dev/null 2>&1; then
  echo "Tunnel up. bench can now reach the DB at 127.0.0.1:${LOCAL_PORT}."
else
  echo "Tunnel failed to start — check SSH access to ${VM_USER}@${VM_HOST}." >&2
  exit 1
fi
