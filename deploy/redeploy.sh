#!/usr/bin/env bash
# FGITO CRM — update loop on the VM: pull latest code, rebuild image, up, migrate, restart.
#
# Usage (on the VM):   cd ~/fgito-crm/deploy && ./redeploy.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

[[ -f .env ]] || { echo "Missing deploy/.env — copy .env.example and fill it in." >&2; exit 1; }
SITE_NAME="$(grep -E '^SITE_NAME=' .env | cut -d= -f2- | tr -d '[:space:]')"
SITE_NAME="${SITE_NAME:-crm.fgito.com}"

# Use Compose v2 ("docker compose") if available, else legacy v1 ("docker-compose").
if docker compose version >/dev/null 2>&1; then DC="docker compose"; else DC="docker-compose"; fi

echo "==> pulling latest code"
git -C "$REPO_DIR" pull --ff-only

echo "==> building image"
"$SCRIPT_DIR/build-on-vm.sh"

echo "==> bringing stack up"
$DC up -d

echo "==> migrating ${SITE_NAME}"
$DC exec -T backend bench --site "${SITE_NAME}" migrate

echo "==> restarting app services"
$DC restart backend websocket queue-short queue-long scheduler

echo "==> done → https://${SITE_NAME}"
