# FGITO CRM — local setup

There are **two ways** to run FGITO CRM on a Mac. In both, the **app runs natively**
(`bench start` + `yarn dev`) — only the **data layer** differs. Pick the one for your machine:

| Setup | MariaDB | Redis | Who uses it | Files |
|---|---|---|---|---|
| **A · Local Docker** *(default — what we do)* | Docker, on this Mac | Docker, on this Mac | The **primary dev machine** — holds the real data | `local-dev.yml` |
| **B · Shared Azure DB** | On the Azure VM, via SSH tunnel | local (brew) | **Extra laptops / CEO** viewing the same data | `db-only.yml`, `db-tunnel.sh`, `setup-mac.sh` |

> If you're not sure, you want **A**. Setup B is the "everyone shares one database" path and is
> slower (many DB round-trips over the internet) — treat it as a future/shared-data option.

---

# A · Local Docker (default)

MariaDB + Redis run in Docker **on your Mac**; the Frappe app runs natively and connects over
`127.0.0.1`. This is the machine that owns the real data.

```
   This Mac
   ┌────────────────────────────────────────────────┐
   │  bench start  +  yarn dev     (native)          │
   │        │ 127.0.0.1                              │
   │        ▼                                        │
   │  Docker:  MariaDB :3306        Redis :6379      │
   └────────────────────────────────────────────────┘
```

## Daily start
```bash
cd ~/frappe-bench/apps/crm
docker compose -f setup/local-dev.yml up -d       # 1) DB + Redis (safe to re-run; no-op if up)
cd ~/frappe-bench && bench start                  # 2) app        (terminal 1)
cd apps/crm/frontend && yarn dev                  # 3) frontend   (terminal 2)
```
Open **http://crm.localhost:8080/crm**.

Because `local-dev.yml` sets `restart: unless-stopped`, the containers **auto-start after a
reboot or Docker Desktop restart** — so you stop getting `ECONNREFUSED` (Redis) or
`Can't connect to MySQL` (MariaDB) when you run `bench start` / `yarn dev`.

## bench config
`~/frappe-bench/sites/common_site_config.json` points bench at the local Docker services:
```json
{
  "db_host": "127.0.0.1",
  "redis_cache": "redis://127.0.0.1:6379",
  "redis_queue": "redis://127.0.0.1:6379",
  "redis_socketio": "redis://127.0.0.1:6379",
  "developer_mode": 1,
  "ignore_csrf": 1
}
```
`db_port` is omitted → defaults to **3306** (the Docker MariaDB). The per-site DB name/password
live in `sites/crm.localhost/site_config.json`.

## One-time: adopt existing containers into compose
Your DB + Redis were originally created by hand (`docker run` / ad-hoc compose), so they had
**no restart policy** and weren't reproducible. Switch them to `local-dev.yml` management —
this **keeps your data** (the compose file adopts your existing volumes `db-stack_mariadb-data`
and `fgito-crm-dev_redis-data` as `external`):
```bash
cd ~/frappe-bench/apps/crm
docker rm -f fgito-crm-mariadb fgito-crm-redis     # removes CONTAINERS only — volumes/data stay
docker compose -f setup/local-dev.yml up -d        # recreate, mounting the SAME volumes
docker compose -f setup/local-dev.yml ps           # wait for (healthy)
```
`docker rm` never deletes named volumes, so this is safe. Do it once; after that just use the
**Daily start** commands above.

## Troubleshooting (local Docker)
| Symptom | Fix |
|---|---|
| `ECONNREFUSED 127.0.0.1:6379` (socketio dies, takes bench down) | Redis container is down → `docker compose -f setup/local-dev.yml up -d`. |
| `Can't connect to MySQL server on '127.0.0.1'` / API 500s | MariaDB container is down → same `up -d` command. Check `docker compose -f setup/local-dev.yml ps`. |
| You ran `docker run mariadb...` and got a new broken container | Don't `docker run` a fresh one — `up -d` the compose stack (it starts your real, data-carrying containers). Remove strays: `docker rm <name>`. |
| Vite: `Failed to resolve ... frappe-ui` | Submodule not initialized — `cd apps/crm && git submodule update --init --recursive`, then `cd frappe-ui && yarn install`. |
| `crm.localhost` won't resolve | Add `127.0.0.1 crm.localhost` to `/etc/hosts` (macOS usually resolves `*.localhost` automatically). |
| Verify you're on the local DB | `bench --site crm.localhost mariadb -e "SELECT COUNT(*) FROM \`tabCRM Lead\`;"` — a row count = data is there. |

---

# B · Shared Azure DB (secondary laptops / CEO)

Run FGITO CRM on **another Mac** (your other laptops, or the **CEO's laptop**) so it runs locally
but uses the **one shared database on the Azure VM**.

```
   Mac (you / CEO)                              Azure VM
   ┌───────────────────────────┐               ┌────────────────────┐
   │ bench start  +  yarn dev   │  SSH tunnel   │ MariaDB (Docker)   │
   │ Redis  (local, on the Mac) │ 3307 ───────► │ 127.0.0.1:3306     │
   └───────────────────────────┘               └────────────────────┘
```
- **App runs on the Mac**, the **DB lives on Azure**, **Redis stays local** on each Mac.
- The Mac reaches the DB through an **SSH tunnel** (no public DB port).

> ⚠️ **Expect lag.** Frappe makes many DB queries per page; over the internet, pages feel slower
> than local. Good for *shared data*, but for snappy daily use the endgame is hosting the whole
> app on the VM. Treat this as the shared-DB stepping stone.

Files for this path:
| File | Runs on | Purpose |
|---|---|---|
| `db-only.yml` | **Azure VM** | MariaDB only, bound to localhost (tunnel-only) |
| `db-tunnel.sh` | **Mac** | opens/keeps the SSH tunnel (autossh) |
| `setup-mac.sh` | **Mac** | one-shot onboarding automation (installs bench + app, writes tunnel config) |

## Part A — one-time, on the Azure VM (DB host)

Do this **once**, on the VM.

1. **Create the VM:** Ubuntu 22.04. In the Azure **NSG**, allow **SSH (22) from your IPs only**.
   **Do NOT open 3306** — the DB is reached only through SSH.
2. **Install Docker:** `curl -fsSL https://get.docker.com | sh`
3. **Copy `db-only.yml` to the VM** and start MariaDB:
   ```bash
   export MARIADB_ROOT_PASSWORD='<a-strong-password>'
   docker compose -f db-only.yml up -d
   docker compose -f db-only.yml ps        # wait for (healthy)
   ```
4. **Add each Mac's SSH key** to the VM (so the tunnel can connect):
   ```bash
   # run FROM each Mac:
   ssh-copy-id azureuser@<VM_IP>
   ```

### Load your existing data into the VM (one time)
Your current data lives in this Mac's **local Docker DB** (setup A). Move it to Azure:
```bash
# On your ORIGIN Mac (setup A — the one that has the data):
cd ~/frappe-bench
git -C apps/crm push                         # make sure code is pushed too (see Part B)
bench --site crm.localhost backup --with-files
#   -> note the printed path to  <timestamp>-crm_localhost-database.sql.gz

# open the tunnel (Part C step 5), point bench at it (Part C step 3), then:
bench --site crm.localhost restore \
  sites/crm.localhost/private/backups/<...>-database.sql.gz \
  --mariadb-root-password '<MARIADB_ROOT_PASSWORD>'
```
`restore` recreates the DB + user on the VM and imports everything. After this, every secondary
Mac just **attaches** to that DB — no one runs `new-site`, `install-app`, or `migrate` again.

---

## Part B — before onboarding any Mac (once)

The new Mac pulls code from GitHub, so make sure GitHub has your latest:
```bash
cd ~/frappe-bench/apps/crm      # (or your working copy)
git push origin main
```

You'll also need, from your **origin Mac**, the file:
```
~/frappe-bench/sites/crm.localhost/site_config.json
```
This holds `db_name`, `db_password`, and the **`encryption_key`**. Every Mac must use the **same**
`site_config.json` or encrypted fields (passwords/tokens) won't decrypt. **Transfer it securely**
(AirDrop / 1Password / USB — not Slack/email).

---

## Part C — on each new (secondary) Mac

### Fast path (automated)
```bash
# 1) get the repo's setup script onto the Mac (clone once, or copy the setup/ folder)
git clone https://github.com/novasie/fgito-crm.git ~/fgito-src

# 2) run onboarding — pass the secret site_config.json you transferred
SITE_CONFIG_SRC=~/Downloads/site_config.json ~/fgito-src/setup/setup-mac.sh
```
`setup-mac.sh` installs everything, sets up the bench, fetches the app + `frappe-ui` submodule,
installs frontend deps, and writes the tunnel DB/Redis config. Then finish with steps 5–6 below.

### Manual path (what the script does — for understanding / troubleshooting)

**1. Prerequisites (Homebrew):**
```bash
brew install python@3.12 node yarn redis wkhtmltopdf mariadb git pipx autossh
brew services start redis                    # local Redis on 127.0.0.1:6379
pipx install frappe-bench && pipx ensurepath
```
*(`mariadb` is installed for its client libraries so bench can build; on this path the server is remote.)*

**2. Bench + app + submodule:**
```bash
bench init --frappe-branch version-15 --python "$(command -v python3.12)" ~/frappe-bench
cd ~/frappe-bench
bench get-app --branch main --skip-assets https://github.com/novasie/fgito-crm.git
cd apps/crm && git submodule update --init --recursive        # frappe-ui — REQUIRED
( cd frontend && yarn install )
( cd ~/frappe-bench/apps/crm/frappe-ui && yarn install )       # submodule's own deps
cd ~/frappe-bench
```

**3. Point bench at the remote DB + local Redis** — edit `sites/common_site_config.json`:
```json
{
  "db_host": "127.0.0.1",
  "db_port": 3307,
  "redis_cache": "redis://127.0.0.1:6379",
  "redis_queue": "redis://127.0.0.1:6379",
  "redis_socketio": "redis://127.0.0.1:6379",
  "developer_mode": 1,
  "ignore_csrf": 1
}
```
> Note the **3307** here (the tunnel port) vs **3306** in setup A (local Docker). That's the only
> config difference between the two paths.

**4. Attach to the shared site (NO new-site):**
```bash
mkdir -p sites/crm.localhost
cp /path/to/site_config.json sites/crm.localhost/site_config.json   # the secret from Part B
echo crm.localhost > sites/currentsite.txt
```

**5. Open the tunnel** (needs this Mac's SSH key on the VM — Part A step 4):
```bash
apps/crm/setup/db-tunnel.sh azureuser <VM_IP>
```

**6. Run it:**
```bash
bench start                                   # terminal 1  (web + socketio + workers)
cd apps/crm/frontend && yarn dev              # terminal 2  (Vite on :8080)
```
Open **http://crm.localhost:8080/crm**.

> **CEO / view-only laptop:** run `honcho start web socketio watch` instead of `bench start`.
> This skips the scheduler + background worker so the laptop doesn't fire **duplicate** scheduled
> jobs against the shared DB. Only **one** machine should own background jobs.

## Daily start (setup B)
```bash
cd ~/frappe-bench
apps/crm/setup/db-tunnel.sh azureuser <VM_IP>     # 1) tunnel first
bench start                                       # 2) app   (CEO: honcho start web socketio watch)
cd apps/crm/frontend && yarn dev                  # 3) frontend (new terminal)
```

## Troubleshooting (setup B)
| Symptom | Fix |
|---|---|
| `Can't connect to MySQL ... 3307` | Tunnel isn't up — run `db-tunnel.sh` first. Check SSH access to the VM. |
| Vite: `Failed to resolve ... frappe-ui` | Submodule not initialized — `cd apps/crm && git submodule update --init --recursive`, then `cd frappe-ui && yarn install`. |
| Login works but fields blank / decrypt errors | Wrong `site_config.json` — must be the exact one from the origin (same `encryption_key`). |
| `crm.localhost` won't resolve | Add `127.0.0.1 crm.localhost` to `/etc/hosts`. |
| Tunnel keeps dropping | That's why we use `autossh` in `db-tunnel.sh`; confirm it's running (`pgrep -f 3307`). |
| Pages slow | Expected over WAN. Put the VM in your nearest Azure region, or move to full VM hosting. |

## Security notes (setup B)
- The DB port is **never public** — only SSH (22), locked to your IPs in the NSG.
- `site_config.json` is a **secret** (DB password + encryption key). Transfer it securely; don't commit it.
- Each Mac authenticates to the VM with its own SSH key.
