#!/usr/bin/env bash
# FGITO CRM — one-shot onboarding for a fresh Mac (developer laptop or CEO laptop).
#
# Installs prerequisites, sets up a native Frappe bench, fetches the fgito-crm app
# (+ its frappe-ui submodule), installs frontend deps, and points bench at the shared
# Azure DB over the SSH tunnel + local Redis.
#
# It does NOT create a site or a database — the data already lives on Azure. It attaches
# to the existing site by copying the origin Mac's site_config.json (holds the DB
# credentials + encryption_key). That copy is a SECRET, so it's not baked in here.
#
# Usage:
#   ./setup-mac.sh
#   SITE_CONFIG_SRC=~/Downloads/site_config.json ./setup-mac.sh   # auto-copies the secret
#
# Safe to re-run: each step checks before acting. Read setup/README.md for the manual walkthrough.

set -euo pipefail

# ── Config (override via env) ────────────────────────────────────────────────
BENCH_DIR="${BENCH_DIR:-$HOME/frappe-bench}"
REPO_URL="${REPO_URL:-https://github.com/novasie/fgito-crm.git}"
APP_BRANCH="${APP_BRANCH:-main}"
FRAPPE_BRANCH="${FRAPPE_BRANCH:-version-15}"
PYTHON_FORMULA="${PYTHON_FORMULA:-python@3.12}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
SITE="${SITE:-crm.localhost}"
LOCAL_DB_PORT="${LOCAL_DB_PORT:-3307}"     # matches setup/db-tunnel.sh
SITE_CONFIG_SRC="${SITE_CONFIG_SRC:-}"     # optional path to origin's site_config.json

say()  { printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m! %s\033[0m\n" "$*"; }

# ── 1. Homebrew ──────────────────────────────────────────────────────────────
if ! command -v brew >/dev/null 2>&1; then
  say "Installing Homebrew"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$($(command -v brew || echo /opt/homebrew/bin/brew) shellenv)"
fi

# ── 2. Prerequisites ─────────────────────────────────────────────────────────
say "Installing prerequisites via brew"
brew install "$PYTHON_FORMULA" node yarn redis wkhtmltopdf mariadb git pipx autossh || true
brew services start redis || true          # local Redis on 127.0.0.1:6379
pipx ensurepath >/dev/null 2>&1 || true

if ! command -v bench >/dev/null 2>&1; then
  say "Installing frappe-bench (pipx)"
  pipx install frappe-bench
  export PATH="$HOME/.local/bin:$PATH"
fi

# ── 3. bench init ────────────────────────────────────────────────────────────
if [[ ! -d "$BENCH_DIR" ]]; then
  say "Initializing bench at $BENCH_DIR (Frappe $FRAPPE_BRANCH, $PYTHON_BIN)"
  bench init --frappe-branch "$FRAPPE_BRANCH" --python "$(command -v "$PYTHON_BIN")" "$BENCH_DIR"
else
  warn "Bench already exists at $BENCH_DIR — skipping bench init"
fi
cd "$BENCH_DIR"

# ── 4. Fetch the app + submodule + frontend deps ─────────────────────────────
if [[ ! -d "$BENCH_DIR/apps/crm" ]]; then
  say "Fetching fgito-crm ($APP_BRANCH) from $REPO_URL"
  bench get-app --branch "$APP_BRANCH" --skip-assets "$REPO_URL"
else
  warn "apps/crm already present — pulling latest"
  git -C "$BENCH_DIR/apps/crm" pull --ff-only || warn "could not fast-forward apps/crm"
fi

say "Initializing frappe-ui submodule (required for the Vite build)"
git -C "$BENCH_DIR/apps/crm" submodule update --init --recursive

say "Installing frontend deps"
( cd "$BENCH_DIR/apps/crm/frontend" && yarn install )
( cd "$BENCH_DIR/apps/crm/frappe-ui" && yarn install )   # submodule's own deps

# ── 5. Point bench at the tunneled DB + local Redis ──────────────────────────
say "Writing sites/common_site_config.json (remote DB via tunnel, local Redis)"
CSC="$BENCH_DIR/sites/common_site_config.json"
[[ -f "$CSC" ]] || echo "{}" > "$CSC"
"$PYTHON_BIN" - "$CSC" "$LOCAL_DB_PORT" <<'PY'
import json, sys
path, port = sys.argv[1], int(sys.argv[2])
cfg = json.load(open(path))
cfg.update({
    "db_host": "127.0.0.1",
    "db_port": port,
    "redis_cache": "redis://127.0.0.1:6379",
    "redis_queue": "redis://127.0.0.1:6379",
    "redis_socketio": "redis://127.0.0.1:6379",
    "developer_mode": 1,
    "ignore_csrf": 1,
})
json.dump(cfg, open(path, "w"), indent=1)
print("updated", path)
PY

# ── 6. Attach to the shared site (copy the secret site_config.json) ──────────
SITE_DIR="$BENCH_DIR/sites/$SITE"
mkdir -p "$SITE_DIR"
if [[ -n "$SITE_CONFIG_SRC" && -f "$SITE_CONFIG_SRC" ]]; then
  say "Installing site_config.json for $SITE from $SITE_CONFIG_SRC"
  cp "$SITE_CONFIG_SRC" "$SITE_DIR/site_config.json"
  echo "$SITE" > "$BENCH_DIR/sites/currentsite.txt"
elif [[ ! -f "$SITE_DIR/site_config.json" ]]; then
  warn "MISSING: $SITE_DIR/site_config.json"
  warn "Copy it from the origin Mac's sites/$SITE/site_config.json (holds db creds + encryption_key)."
  warn "Then:  echo $SITE > $BENCH_DIR/sites/currentsite.txt"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
cat <<EOF

$(say "Almost there — remaining manual steps")
  1) Ensure this Mac's SSH key is added to the Azure VM (ssh-copy-id or paste into authorized_keys).
  2) Start the DB tunnel:
       $BENCH_DIR/apps/crm/setup/db-tunnel.sh <vm_user> <vm_host>
  3) (if you didn't pass SITE_CONFIG_SRC) copy site_config.json into sites/$SITE/ and run:
       echo $SITE > $BENCH_DIR/sites/currentsite.txt
  4) Start the app:
       cd $BENCH_DIR && bench start                       # terminal 1
       cd $BENCH_DIR/apps/crm/frontend && yarn dev         # terminal 2
     (CEO / view-only laptop: use  honcho start web socketio watch  instead of  bench start)
  5) Open http://$SITE:8080/crm

Full walkthrough + troubleshooting: apps/crm/setup/README.md
EOF
