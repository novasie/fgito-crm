# Local Dev Setup (live reload)

Run **MariaDB + Redis in Docker** and the **Frappe bench + Vite frontend natively** on the
Mac. This gives Python autoreload (`bench start`) and Vite HMR (`yarn dev`) so code changes
show up live.

```
┌─────────────── Docker ───────────────┐   ┌──────────── Native (host) ────────────┐
│  MariaDB :3306   Redis :6379          │◀──│  bench start  → web :8000, socket :9000│
│  (docker/dev-datastores.yml)          │   │  yarn dev     → Vite HMR   :8080        │
└───────────────────────────────────────┘   └────────────────────────────────────────┘
```

Repo path referenced below: `/Users/ddharmacharya/Desktop/Fgito/Products/fgito-crm` (this fork).

---

## 0. Prerequisites

| Tool | Required | This machine |
|---|---|---|
| Docker + Compose | yes | ✅ |
| Python **3.10–3.12** (Frappe v15 does **not** support 3.13/3.14) | yes | ✅ use `/opt/homebrew/bin/python3.12` |
| Node 18+ / Yarn 1.x | yes | ✅ node 22, yarn 1.22 |
| bench CLI | yes | ✅ 5.31 |
| Redis client libs | via bench | ✅ |
| wkhtmltopdf | only for PDF export | ❌ `brew install --cask wkhtmltopdf` (optional, defer) |

**Check out the `frappe-ui` submodule AND install its deps.** In dev, `vite.config.js` builds
frappe-ui *from source* (the npm package ships uncompiled `src/` that uses `~icons/*` and
tiptap), so the submodule and its own `node_modules` are required — without them the dev
server fails with `Could not resolve "~icons/lucide/..."`:

```bash
git submodule update --init --recursive
cd frappe-ui && yarn install && cd ..     # ~2-3 min, 76 deps
```

---

## 1. Start datastores (Docker)

The repo bundles a self-contained MariaDB + Redis stack — this is the single source of truth:

```bash
cd /Users/ddharmacharya/Desktop/Fgito/Products/fgito-crm
docker compose -f docker/dev-datastores.yml up -d
```

- Containers: `fgito-crm-mariadb` (:3306, root pw `123`, override with `MARIADB_ROOT_PASSWORD`)
  and `fgito-crm-redis` (:6379).
- **Volume note:** this compose currently reuses the pre-existing `db-stack_mariadb-data`
  volume (from an earlier, now-deleted `db-stack` compose) so the local site DB is preserved.
  On a **fresh machine**, delete the `external:`/`name:` lines under `volumes:` in
  `docker/dev-datastores.yml` so Compose creates a clean project-owned volume.
- Stop with `docker compose -f docker/dev-datastores.yml down` (keeps data);
  `down -v` wipes it (won't remove the external `db-stack_mariadb-data` volume — do that with
  `docker volume rm db-stack_mariadb-data`).

---

## 2. Create a native bench (once)

Create the bench **outside** the repo (e.g. `~/frappe-bench`), using Python 3.12:

```bash
cd ~
bench init --frappe-branch version-15 --python /opt/homebrew/bin/python3.12 frappe-bench
cd frappe-bench

# Point the bench at the Docker datastores
bench set-mariadb-host 127.0.0.1
bench set-redis-cache-host    redis://127.0.0.1:6379
bench set-redis-queue-host    redis://127.0.0.1:6379
bench set-redis-socketio-host redis://127.0.0.1:6379

# Redis is managed by Docker, not the Procfile — drop the bundled redis/watch lines
sed -i '' '/redis/d;/watch/d' ./Procfile
```

---

## 3. Link THIS fork as the `crm` app

Symlink the fork into the bench so edits are live (do **not** `bench get-app crm` — that
pulls the upstream repo from GitHub):

```bash
ln -s /Users/ddharmacharya/Desktop/Fgito/Products/fgito-crm ~/frappe-bench/apps/crm

# Register the app with the bench's environment
cd ~/frappe-bench
./env/bin/pip install -e apps/crm
bench build --app crm      # optional first-time asset build
```

Install the frontend deps (native, for HMR):

```bash
cd ~/frappe-bench/apps/crm/frontend
yarn install
```

---

## 4. Create the dev site

```bash
cd ~/frappe-bench
bench new-site crm.localhost \
  --mariadb-root-password 123 \
  --admin-password admin \
  --no-mariadb-socket

bench --site crm.localhost install-app crm
bench --site crm.localhost set-config developer_mode 1   # required: enables get_context_for_dev
bench --site crm.localhost set-config ignore_csrf 1       # required: Vite proxy CSRF
bench --site crm.localhost set-config server_script_enabled 1
bench use crm.localhost
```

> `developer_mode` is mandatory — the dev frontend boots via
> `crm.www.crm.get_context_for_dev`, which throws when developer mode is off.

---

## 5. Run (two terminals)

```bash
# Terminal 1 — backend (web :8000, socketio :9000, Python autoreload)
cd ~/frappe-bench && bench start

# Terminal 2 — frontend (Vite HMR :8080)
cd ~/frappe-bench/apps/crm/frontend && yarn dev
```

Open **http://crm.localhost:8080/crm** — login `Administrator` / `admin`.

- Edit a `.vue` file → instant HMR.
- Edit a `.py` file → `bench start` autoreloads the worker.

---

## Day-to-day

```bash
docker compose -f docker/dev-datastores.yml up -d     # datastores
cd ~/frappe-bench && bench start                       # terminal 1
cd ~/frappe-bench/apps/crm/frontend && yarn dev        # terminal 2
```

## Troubleshooting

- **CSRFToken error** → `bench --site crm.localhost set-config ignore_csrf 1`, restart `bench start`.
- **Blank page / boot error** → confirm `developer_mode 1`; hard-refresh; check `bench start` logs.
- **Socket not connecting** → socketio must be on :9000 and reachable (`frontend/src/socket.js`).
- **`bench start` fails with `EADDRINUSE :9000` (or :8000)** → a previous `bench start`
  didn't fully die (orphaned reloader keeps respawning). Free both ports, then start again:
  ```bash
  lsof -ti:8000 -ti:9000 -sTCP:LISTEN | xargs kill -9
  ```
  (If :8000 keeps coming back, kill the parent `bench serve` PID first — it's the werkzeug
  reloader respawning the child. `ps -o ppid= -p <child-pid>` finds it.)
- **`/assets/crm/...` 404s (logo/branding missing)** → the bench is missing the app's asset
  symlink (normally created by `bench build`). Create it once, from the bench root:
  `ln -sfn "$(pwd)/apps/crm/crm/public" sites/assets/crm` (or run `bench build --app crm`).
- **`~icons/lucide/...` could not be resolve** → the `frappe-ui` submodule deps aren't
  installed. Run `cd apps/crm/frappe-ui && yarn install`, then `rm -rf apps/crm/frontend/node_modules/.vite` and restart `yarn dev`.
- **`No common_site_config.json found, using default port 8000`** (in the vite log) → harmless
  here. Because `apps/crm` is a **symlink**, the frappe-ui plugin resolves the config's real
  path (the fork) and can't walk up to the bench's `sites/`, so it falls back to :8000 — which
  is exactly where `bench start` serves, so the proxy still works.
- **`Access-Control` / port issues** → the frappe-ui Vite plugin normally auto-detects the
  backend port from `~/frappe-bench/sites/common_site_config.json` (`webserver_port`, default 8000).
- **DB connection refused** → is the Docker MariaDB healthy? `docker compose -f docker/dev-datastores.yml ps`.
