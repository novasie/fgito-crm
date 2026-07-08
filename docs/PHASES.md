# fgito-crm — Build Phases

Roadmap for turning the FGITO CRM fork into our internal, white-labeled CRM with WhatsApp
lead capture + chat and Zoho email. **We pick one phase at a time.** Setup details live in
[DEV_SETUP.md](./DEV_SETUP.md).

Legend: ✅ done · 🔜 next · ⬜ planned

---

## ✅ Phase 0 — Local dev environment (live reload)

**Goal:** run the fork locally so code changes hot-reload.

**Shipped:**
- MariaDB + Redis in Docker (`docker/dev-datastores.yml`, reuses `db-stack_mariadb-data` volume).
- Native Frappe bench at `~/frappe-bench` (Python 3.12 — v15 doesn't support 3.14), fork
  symlinked as `apps/crm`, site `crm.localhost` with `developer_mode` + `ignore_csrf`.
- `frappe-ui` submodule built from source (its deps installed) — required in dev.
- Verified: page, `main.js`, frappe-ui, dev-boot context, and login all return 200.

**Run it:** Terminal 1 `cd ~/frappe-bench && bench start` · Terminal 2
`cd ~/frappe-bench/apps/crm/frontend && yarn dev` → http://crm.localhost:8080/crm (Administrator/admin).

---

## 🔜 Phase 1 — White-label

**Goal:** replace all "FGITO CRM" branding with our internal name/logo.

**Needs from us:** the internal **brand name** + a **logo** file (SVG/PNG) if we have one.

**Scope:**
- Runtime brand (no code): set Brand Name / Logo / Favicon in **Settings → Brand**
  (`FCRM Settings` → `frontend/src/stores/settings.js` → `BrandSettings.vue`).
- Hardcoded surfaces to edit:
  - `frontend/index.html` (`<title>`, `apple-mobile-web-app-title`)
  - `frontend/vite.config.js` (PWA manifest `name`/`short_name`/icons)
  - `frontend/src/components/Icons/CRMLogo.vue` (default logo SVG)
  - `frontend/src/components/Modals/AboutModal.vue` (name, ©, frappe.io links)
  - `SalesHierarchyBanner.vue`, `pages/NotPermitted.vue`, `pages/PersonaForm.vue`,
    `Layouts/AppSidebar.vue`, `Settings/ERPNextSettings.vue`
  - `crm/hooks.py` → `app_title` (keep `app_name = "crm"`)
  - Assets: `frontend/public/favicon.png`, `crm/public/manifest/*`, `.github/logo.*`
- Optional: hide the "Login to Frappe Cloud" UI (`composables/frappecloud.js`, `UserDropdown.vue`).

**Done when:** brand name/logo/favicon show everywhere; `grep -ri "FGITO CRM"` in
`frontend/src` + `crm/` returns only intentional leftovers.

---

## ⬜ Phase 2 — WhatsApp (Meta Cloud API) + auto-create-lead

**Goal:** capture leads from WhatsApp and chat per lead/deal in the CRM.

**Note:** the chat UI, composer, template selector, backend API, and phone→lead linking
**already exist** — they just need the `frappe_whatsapp` app installed.

**Scope:**
1. Install `frappe_whatsapp` into the bench, `bench --site crm.localhost install-app frappe_whatsapp`, `bench migrate`.
2. Configure Meta Cloud API in **Settings → Integrations → WhatsApp** (phone number ID,
   permanent token, webhook verify token). Expose :8000 via tunnel (ngrok/cloudflared) for Meta's webhook.
3. Verify inbound messages auto-link to existing Lead/Deal (`crm/api/whatsapp.py::validate`).
4. **New code:** auto-create a `CRM Lead` when an *unknown* number messages (mirrors
   `crm/utils/__init__.py::create_lead_from_incoming_email`); add a "WhatsApp" lead source;
   toggle-able; add test in `crm/tests/test_whatsapp.py`.

**Done when:** message from a known contact appears in that Lead/Deal chat tab (live);
message from an unknown number creates a new Lead with the thread attached.

---

## ⬜ Phase 3 — Zoho ZeptoMail email (send-only)

**Goal:** send CRM email via Zoho ZeptoMail. (ZeptoMail is transactional/outbound-only —
no inbound/reply capture; use Zoho Mail IMAP later if we need two-way.)

**Scope:**
- Add a `"Zoho ZeptoMail"` preset to `email_service_config` in `crm/api/settings.py`
  (`smtp.zeptomail.com:587`, TLS, login `emailapikey`, password = Send Mail token).
- Special-case it in `create_email_account` (like `Frappe Mail`): `enable_incoming = 0`,
  skip the IMAP folder + `get_incoming_server()` validation.
- Frontend: add the provider to the email settings list + icon (`Settings/EmailConfig.vue`,
  `emailConfig.js`, `EmailAdd.vue`, `EmailProviderIcon.vue`); hide incoming toggles for it.

**Done when:** a ZeptoMail account saves without IMAP errors and a test email from a Lead
sends and logs as a Communication.

---

## ⬜ Phase 4 — Doppler for secrets (light)

**Goal:** manage secrets via Doppler instead of scattering them in config.

**Scope:**
- Wrap dev processes: `doppler run -- bench start`, `doppler run -- yarn dev`.
- `scripts/apply-secrets.sh` → `bench --site crm.localhost set-config <k> <v>` from Doppler
  (DB/admin passwords, build secrets). Integration tokens (WhatsApp, ZeptoMail) stay in DocTypes.
- Playwright already reads `FRAPPE_USER`/`FRAPPE_PASSWORD`/`BASE_URL` — Doppler-inject as-is.

**Done when:** `doppler run -- bench start` boots and `bench show-config` reflects injected values.

---

## Backlog / ideas (not scheduled)
- Custom fields/logic via the existing Form Scripting engine (`.pi/`, `CRM Form Script`) instead of hardcoding.
- Zoho Mail IMAP inbound (two-way email + inbound→lead) if ZeptoMail send-only isn't enough.
- Remove/replace ERPNext + Frappe Cloud + telemetry hooks for a fully internal build.

---

## Pick next
Current: **Phase 1 (White-label)** is up next. To start it, provide the brand name (+ logo).
