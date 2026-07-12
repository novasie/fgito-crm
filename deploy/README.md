# FGITO CRM — Docker deployment on your existing VM (behind your nginx)

The whole app runs in containers on the VM: MariaDB + Redis + the full CRM. The CRM web container
publishes on **127.0.0.1:8080**, and **your existing host nginx** routes **crm.fgito.com → 127.0.0.1:8080**
with TLS from your existing certbot — exactly the pattern you already use for `dev-web.fgito.com → :4000`.
The image is **built on the VM from the pulled git branch** — no registry, no tokens.

```
   You (Mac)          GitHub            VM (Azure, existing)
   git push ────────► main ──► git pull ─┐
                                          ├─ build image (local)
                                          ├─ docker-compose up  (db+redis+crm)  → 127.0.0.1:8080
   Browser ─ https://crm.fgito.com ─► your nginx (TLS) ─────────► 127.0.0.1:8080
```

**Baked-in decisions:** build on the VM · MariaDB container · **your nginx** terminates HTTPS for **crm.fgito.com**.

> **Verified:** the image builds cleanly (frontend + assets baked, custom Lead fields + `CRM Service Type`
> included). Production build skips sourcemaps (smaller image). No `frappe-ui` submodule needed.

| File | Runs on | Purpose |
|---|---|---|
| `Containerfile` | VM (build) | image recipe — builds from the local checkout |
| `build-on-vm.sh` | VM | `docker build` → local image `fgito-crm:latest` |
| `first-deploy.sh` | VM | first-time bring-up (creates site, installs crm) |
| `redeploy.sh` | VM | **the update loop**: git pull → build → up → migrate → restart |
| `compose.yaml` | VM | the stack (db, redis, crm) — publishes 127.0.0.1:8080 |
| `nginx-crm.conf` | VM | server block for your host nginx (crm.fgito.com → :8080) |
| `.env.example` | VM | config (copy to `.env`) |
| `resources/` | build | vendored Frappe entrypoint scripts |

---

## Part A — one-time setup

### A1. DNS
Add an **A-record**: `crm.fgito.com  →  <VM public IP>` (same VM as `dev-web`). Confirm with
`dig +short crm.fgito.com`.

### A2. VM prerequisites (you likely have these already)
- **Docker** installed (`docker --version`). If not: `curl -fsSL https://get.docker.com | sh`.
- **nginx** running (it already serves dev-web.fgito.com).
- **Ports 80/443** already open in the Azure NSG (your nginx uses them) + **22** from your IP.
  The CRM's 8080 is **localhost-only** — never exposed publicly.
- **Resources:** the CRM adds ~7 containers incl. MariaDB, and the build is RAM-hungry — make sure the
  VM has headroom (≈8 GB ideal). It coexists with your dashboard; only the DB/Redis are new long-running load.

### A3. Get the code + config on the VM
```bash
git clone https://github.com/novasie/fgito-crm.git ~/fgito-crm
cd ~/fgito-crm/deploy
cp .env.example .env
nano .env          # set DB_PASSWORD, ADMIN_PASSWORD (strong!); SITE_NAME=crm.fgito.com; HTTP_PORT=8080
```

---

## Part B — first deploy (once)

### B1. Build + start the stack
On your Mac: `git push origin main`. On the VM:
```bash
cd ~/fgito-crm && git pull
cd deploy && ./first-deploy.sh
```
Builds the image (~10–15 min first time), starts the stack, and `create-site` creates `crm.fgito.com`
+ installs crm — running your seeds, so the custom Lead fields, `CRM Service Type`, and branding all
appear automatically. It also sets `host_name=https://crm.fgito.com`.

Smoke-test locally on the VM (before nginx):
```bash
curl -sI -H "Host: crm.fgito.com" http://127.0.0.1:8080/crm    # expect HTTP 200
```

### B2. Wire up your nginx (once)
```bash
sudo cp ~/fgito-crm/deploy/nginx-crm.conf /etc/nginx/sites-available/crm.fgito.com
sudo ln -s /etc/nginx/sites-available/crm.fgito.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d crm.fgito.com        # adds SSL + http→https redirect, same as dev-web
```

Open **https://crm.fgito.com** → log in as **Administrator** / your `ADMIN_PASSWORD`.

---

## Part C — every update (your day-to-day)

On your Mac: `git push origin main`. Then on the VM, one command:
```bash
cd ~/fgito-crm/deploy && ./redeploy.sh
```
Pulls latest code → rebuilds the image → `docker-compose up -d` → `bench migrate` (schema + your
idempotent seeds) → restarts services. nginx keeps routing; no nginx change needed for code updates.

---

## Operations
| Task | Command (on the VM, in `deploy/`) |
|---|---|
| Logs | `docker-compose logs -f backend` |
| Status | `docker-compose ps` |
| Bench shell | `docker-compose exec backend bash` |
| Manual migrate | `docker-compose exec backend bench --site crm.fgito.com migrate` |
| **Backup** | `docker-compose exec backend bench --site crm.fgito.com backup --with-files` |
| Restart | `docker-compose restart backend frontend` |
| Stop (keep data) | `docker-compose down` |

**Nightly backup cron** (VM `crontab -e`), then copy dumps to Azure Blob:
```
0 2 * * * cd ~/fgito-crm/deploy && docker-compose exec -T backend bench --site crm.fgito.com backup --with-files
```

---

## Troubleshooting
| Symptom | Fix |
|---|---|
| Build OOM / killed | VM low on RAM — free memory or size up; build wants a few GB. |
| `curl 127.0.0.1:8080` fails | Stack not up — `docker-compose ps`, `docker-compose logs backend frontend`. |
| 502 from nginx | Container not ready or wrong port — confirm `HTTP_PORT=8080` and the stack is up. |
| CRM realtime not updating | nginx block must forward `Upgrade`/`Connection` headers (it does — don't strip them). |
| Cert not issued | DNS must resolve to the VM + port 80 reachable; re-run `sudo certbot --nginx -d crm.fgito.com`. |
| `create-site` "site exists" | Normal on re-runs — idempotent, skips. |
| Migrate errors | `docker-compose logs backend`; seeds are wrapped in try/except so they log, not crash. |

## Security
- Never commit `.env` (DB/admin passwords) — it lives only on the VM (git-ignored).
- The CRM port **8080 is bound to 127.0.0.1** — not reachable from the internet; only your nginx hits it.
- Data lives in the `db-data` + `sites` Docker volumes — back them up off-box.
