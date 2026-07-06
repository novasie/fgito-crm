#!/usr/bin/env bash
# Start the Frappe backend cleanly: clear any stragglers on the dev ports first,
# then run `bench start`. Avoids the recurring "EADDRINUSE :8000/:9000" from orphaned
# reloader/socketio processes.
#
# Frontend (Vite HMR) runs in a SEPARATE terminal:
#   cd ~/frappe-bench/apps/crm/frontend && yarn dev
set -euo pipefail

BENCH_DIR="${BENCH_DIR:-$HOME/frappe-bench}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. free the ports
bash "$HERE/dev-stop.sh"

# 2. ensure datastores are up (harmless if already running)
docker compose -f "$HERE/../docker/dev-datastores.yml" up -d >/dev/null 2>&1 || true

# 3. start the backend (foreground; Ctrl+C to stop, then re-run this to restart cleanly)
echo "Starting bench at $BENCH_DIR ..."
cd "$BENCH_DIR"
exec bench start
