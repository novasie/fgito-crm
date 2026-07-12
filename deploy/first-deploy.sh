#!/usr/bin/env bash
# FGITO CRM — first-time bring-up, run ON THE VM (once), from ~/fgito-crm/deploy.
#
# Prereqs: Docker + a filled-in .env. HTTPS is handled separately by your host nginx
# (see deploy/README.md: nginx-crm.conf + certbot).
#
# Builds the image locally, starts the stack; create-site then creates the site, installs
# crm (running your seeds), and sets host_name.
#
# Usage (on the VM):   cd ~/fgito-crm/deploy && ./first-deploy.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

[[ -f .env ]] || { echo "Missing .env — copy .env.example to .env and fill it in." >&2; exit 1; }

# Use Compose v2 ("docker compose") if available, else legacy v1 ("docker-compose").
if docker compose version >/dev/null 2>&1; then DC="docker compose"; else DC="docker-compose"; fi

echo "==> building image"
./build-on-vm.sh

echo "==> starting stack (first run creates the site + installs crm)"
$DC up -d

echo "==> watching site creation (Ctrl-C once you see it finish)"
$DC logs -f create-site
