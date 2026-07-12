#!/usr/bin/env bash
# FGITO CRM — first-time bring-up, run ON THE VM (once), from ~/fgito-crm/deploy.
#
# Prereqs: Docker installed; .env filled in; DNS A-record for SITE_NAME already points
# at this VM and ports 80/443 are open (Caddy needs both to obtain the TLS cert).
#
# Builds the image locally, starts the stack; create-site then creates the site, installs
# crm (running your seeds), and sets host_name. Caddy fetches the HTTPS cert on first hit.
#
# Usage (on the VM):   cd ~/fgito-crm/deploy && ./first-deploy.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

[[ -f .env ]] || { echo "Missing .env — copy .env.example to .env and fill it in." >&2; exit 1; }

echo "==> building image"
./build-on-vm.sh

echo "==> starting stack (first run creates the site + installs crm + gets the TLS cert)"
docker compose up -d

echo "==> watching site creation (Ctrl-C once you see it finish)"
docker compose logs -f create-site
