# FGITO CRM — run on any Mac against the shared Azure database

This folder sets up FGITO CRM on a **new Mac** (your other laptops, or the **CEO's laptop**) so it
runs locally but uses the **one shared database on the Azure VM**.

**Architecture**
```
   Mac (you / CEO)                              Azure VM
   ┌───────────────────────────┐               ┌────────────────────┐
   │ bench start  +  yarn dev   │  SSH tunnel   │ MariaDB (Docker)   │
   │ Redis  (local, on the Mac) │ 3307 ───────► │ 127.0.0.1:3306     │
   └───────────────────────────┘               └────────────────────┘
```
- **App runs on the Mac**, the **DB lives on Azure**, **Redis stays local** on each Mac.
- The Mac reaches the DB through an **SSH tunnel** (no public DB port).

> ⚠️ **Expect lag.** Frappe makes many DB queries per page; over the internet, pages feel slower than
> local. This is a good *shared-data* setup, but for snappy daily use the endgame is hosting the whole
> app on the VM. Treat this as the shared-DB stepping stone.

Files here:
| File | Runs on | Purpose |
|---|---|---|
| `db-only.yml` | **Azure VM** | MariaDB only, bound to localhost (tunnel-only) |
| `db-tunnel.sh` | **Mac** | opens/keeps the SSH tunnel (autossh) |
| `setup-mac.sh` | **Mac** | one-shot onboarding automation |
| `README.md` | — | this guide |

---

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
Your current data (custom Lead fields, statuses, sources, any leads) is in your Mac's local Docker DB.
Move it to Azure:
```bash
# On your ORIGIN Mac (the one that has the data):
cd ~/frappe-bench
git -C apps/crm push                         # make sure code is pushed too (see Part B)
bench --site crm.localhost backup --with-files
#   -> note the printed path to  <timestamp>-crm_localhost-database.sql.gz

# open the tunnel (Part C step 2), point bench at it (Part C step 3), then:
bench --site crm.localhost restore \
  sites/crm.localhost/private/backups/<...>-database.sql.gz \
  --mariadb-root-password '<MARIADB_ROOT_PASSWORD>'
```
`restore` recreates the DB + user on the VM and imports everything. After this, every Mac just
**attaches** to that DB — no one runs `new-site`, `install-app`, or `migrate` again.

---

## Part B — before onboarding any Mac (once)

The new Mac pulls code from GitHub, so make sure GitHub has your latest:
```bash
cd ~/frappe-bench/apps/crm      # (or your working copy)
git push origin main
```
> The custom Lead-fields commit is currently **local-only** until you push.

You'll also need, from your **origin Mac**, the file:
```
~/frappe-bench/sites/crm.localhost/site_config.json
```
This holds `db_name`, `db_password`, and the **`encryption_key`**. Every Mac must use the **same**
`site_config.json` or encrypted fields (passwords/tokens) won't decrypt. **Transfer it securely**
(AirDrop / 1Password / USB — not Slack/email).

---

## Part C — on each new Mac (the repeatable part)

### Fast path (automated)
```bash
# 1) get the repo's setup script onto the Mac (clone once, or copy the setup/ folder)
git clone https://github.com/novasie/fgito-crm.git ~/fgito-src

# 2) run onboarding — pass the secret site_config.json you transferred
SITE_CONFIG_SRC=~/Downloads/site_config.json ~/fgito-src/setup/setup-mac.sh
```
`setup-mac.sh` installs everything, sets up the bench, fetches the app + `frappe-ui` submodule,
installs frontend deps, and writes the DB/Redis config. Then finish with steps 2–5 below.

### Manual path (what the script does — for understanding / troubleshooting)

**1. Prerequisites (Homebrew):**
```bash
brew install python@3.12 node yarn redis wkhtmltopdf mariadb git pipx autossh
brew services start redis                    # local Redis on 127.0.0.1:6379
pipx install frappe-bench && pipx ensurepath
```
*(`mariadb` is installed for its client libraries so bench can build; we never start the server.)*

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
> This skips the scheduler + background worker so the laptop doesn't fire **duplicate** scheduled jobs
> against the shared DB. Only **one** machine (yours) should own background jobs.

---

## Daily start (after first setup)
```bash
cd ~/frappe-bench
apps/crm/setup/db-tunnel.sh azureuser <VM_IP>     # 1) tunnel first
bench start                                       # 2) app   (CEO: honcho start web socketio watch)
cd apps/crm/frontend && yarn dev                  # 3) frontend (new terminal)
```

## Verify you're really on the Azure DB
```bash
bench --site crm.localhost mariadb -e \
  "SELECT COUNT(*) AS leads FROM \`tabCRM Lead\`; SHOW COLUMNS FROM \`tabCRM Lead\` LIKE 'service_type';"
```
Row counts from the shared data + a `service_type` column = you're on the remote DB, not a fresh local one.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `Can't connect to MySQL ... 3307` | Tunnel isn't up — run `db-tunnel.sh` first. Check SSH access to the VM. |
| Vite: `Failed to resolve ... frappe-ui` | Submodule not initialized — `cd apps/crm && git submodule update --init --recursive`, then `cd frappe-ui && yarn install`. |
| Login works but fields blank / decrypt errors | Wrong `site_config.json` — must be the exact one from the origin (same `encryption_key`). |
| `crm.localhost` won't resolve | Add `127.0.0.1 crm.localhost` to `/etc/hosts` (macOS usually resolves `*.localhost` automatically). |
| Tunnel keeps dropping | That's why we use `autossh` in `db-tunnel.sh`; confirm it's the process running (`pgrep -f 3307`). |
| Pages slow | Expected over WAN. Put the VM in your nearest Azure region, or move to full VM hosting. |

## Security notes
- The DB port is **never public** — only SSH (22), locked to your IPs in the NSG.
- `site_config.json` is a **secret** (DB password + encryption key). Transfer it securely; don't commit it.
- Each Mac authenticates to the VM with its own SSH key.
