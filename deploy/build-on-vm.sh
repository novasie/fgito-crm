#!/usr/bin/env bash
# Build the FGITO CRM image locally (on the VM) from the checked-out repo.
# No registry, no GitHub auth — the build uses the local source as the `crm` app.
#
# Usage:  ./build-on-vm.sh          # tag=latest (or TAG env)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TAG="${TAG:-latest}"

# The prod build compiles the frappe-ui SUBMODULE from source (so submodule tweaks ship
# to prod), so it must be checked out before we build.
echo "==> ensuring frappe-ui submodule is checked out"
git -C "$REPO_DIR" submodule update --init --recursive

echo "==> building fgito-crm:${TAG} from ${REPO_DIR}"
docker build \
  --tag "fgito-crm:${TAG}" \
  --file "$SCRIPT_DIR/Containerfile" \
  "$REPO_DIR"

echo "==> built fgito-crm:${TAG}"
