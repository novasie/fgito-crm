#!/bin/bash
# Vendored from frappe/frappe_docker (resources/core/main-entrypoint.sh).
# Links the image-baked assets into the mounted sites volume at container start.
set -e

ASSETS_PATH="/home/frappe/frappe-bench/sites/assets"
BAKED_PATH="/home/frappe/frappe-bench/assets"

echo "Linking fresh assets to volume..."
rm -rf "$ASSETS_PATH"
mkdir -p "$(dirname "$ASSETS_PATH")"
ln -s "$BAKED_PATH" "$ASSETS_PATH"

exec "$@"
