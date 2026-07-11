# Frappe Desk (`/app`) Guide + Impact on the CRM app (`/crm`)

Two UIs, **one database**:

- **`/crm`** — the FGITO CRM product (Vue SPA). What your sales team uses.
- **`/app`** — the Frappe **Desk**: the framework admin backend. Raw access to every record,
  the data *schema*, config, users, permissions, integrations, and developer tools.

Mental model: **`/crm` renders forms and lists from the DocType *meta* (schema) and reads the same
tables.** So most structural/config changes you make in `/app` show up in `/crm` automatically.
The section [Impact on `/crm`](#impact-on-crm-what-propagates) is the important one.

---

## 1. The `/app` sidebar (workspaces on this site)

| Workspace | Module | What's in it |
|---|---|---|
| **FGITO CRM** | FCRM | Shortcuts to Leads, Deals, Contacts, Organizations, Tasks, Notes, Call Logs + CRM config doctypes |
| **Users** | Core | User, Role, Role Profile, User Permission, User Group |
| **Website** | Website | Website Settings, pages, portal (mostly irrelevant to internal CRM) |
| **Tools** | Automation | Assignment Rules, Notifications, Email, ToDo, Scheduled Jobs |
| **Integrations** | Integrations | Email Account, Webhooks, Social Login, API/OAuth, connected apps |
| **Build** | Core | DocType builder, **Customize Form**, Client/Server Script, Workflow |
| **Welcome Workspace** | Core | Frappe onboarding (ignorable) |

Installed apps: **frappe 15.113.4**, **crm 1.77.0** (no ERPNext / frappe_whatsapp yet).

---

## 2. What you can manage in `/app`

### A. CRM data (records) — same rows as `/crm`
`CRM Lead`, `CRM Deal`, `CRM Organization`, `CRM Task`, `FCRM Note`, `CRM Call Log`,
`Contact` (+ child tables `CRM Contacts`, `CRM Products`). Editing/deleting here = editing in `/crm`.

### B. CRM "list" config — these populate `/crm` dropdowns & kanban columns
`CRM Lead Status`, `CRM Deal Status`, `CRM Communication Status`, `CRM Lead Source`,
`CRM Industry`, `CRM Territory`, `CRM Lost Reason`, `CRM Dropdown Item`, `CRM Product`.

### C. CRM UI customization — changes how `/crm` looks/behaves
- **`CRM Fields Layout`** — field arrangement in the `/crm` detail side-panel & forms.
- **`CRM Form Script`** — client scripts that run inside `/crm` (the fork's scripting engine).
- **`CRM View Settings`** — saved list/kanban/group-by views in `/crm`.
- **`CRM Dashboard`** — dashboard tiles in `/crm`.
- **Customize Form** (`/app/customize-form`) — add **custom fields** to CRM Lead/Deal/etc.

### D. Settings (single doctypes)
- **`FCRM Settings`** — brand (name/logo/favicon), currency, forecasting, sales hierarchy,
  timeline format, auto-status behaviors. (This is what the brand seed writes.)
- **`CRM Global Settings`**, **`ERPNext CRM Settings`**, **`CRM Twilio Settings`**,
  **`CRM Exotel Settings`**.

### E. Integrations
`Email Account` (send/receive → logs to Leads), Telephony (`CRM Twilio/Exotel Settings`,
`CRM Telephony Agent/Phone`), `Webhook`, Social Login, OAuth. (WhatsApp Settings appear here
once `frappe_whatsapp` is installed — Phase 2.)

### F. Automation & SLA
`Assignment Rule` (auto-assign leads/deals), `CRM Service Level Agreement` (+ Service Day,
Priority, Holiday List, Rolling Response Time), `Notification`, scheduled jobs.

### G. Users & permissions
`User`, `Role` (System Manager / Sales Manager / Sales User), `Role Profile`,
`User Permission` (record-level restrictions), `CRM Sales Hierarchy`, `CRM Invitation`.

### H. Lead syncing
`Facebook Lead Form`, `Facebook Page`, `Lead Sync Source`, `Failed Lead Sync Log`.

### I. System / developer (power tools — can break things)
`DocType` builder, `Server Script`, `Client Script`, `Workflow`, `Custom Field`,
`Property Setter`, Data Import/Export, Error Log, System Console, background jobs.

---

## 3. Impact on `/crm` — what propagates

### ✅ Changes in `/app` that DO show up in `/crm`
| You change in `/app` | Effect in `/crm` |
|---|---|
| A **record** (Lead/Deal/Contact/Org/Task) | Same record — it's one database |
| **Custom Field** via Customize Form on CRM Lead/Deal | New field appears in `/crm` forms & can be added to views |
| **DocType field** options / mandatory / label / type | Reflected in `/crm` (it renders from meta) |
| **CRM Lead/Deal Status**, **Lead Source**, **Industry**, **Territory**, **Lost Reason** | Dropdown / kanban options update in `/crm` |
| **CRM Fields Layout** | Field arrangement in `/crm` panels changes |
| **CRM Form Script** | Client logic runs in `/crm` |
| **CRM View Settings / CRM Dashboard** | Views & dashboards in `/crm` |
| **FCRM Settings** (brand, currency, toggles) | Branding & behavior in `/crm` |
| **Roles / User Permissions / Sales Hierarchy** | What each user can see/do in `/crm` |
| **Assignment Rule / SLA** | Auto-assignment & SLA timers on `/crm` leads/deals |
| **Email Account / Telephony / WhatsApp Settings** | Enables those features in `/crm` |
| **User** enable/disable, roles | Who can log into `/crm` and with what access |

### ➖ `/app` changes that DON'T affect `/crm` (Desk-only)
- **Workspaces** (the `/app` sidebar) — `/crm` has its own navigation.
- Desk theme, Number Cards / Charts placed on the Desk workspace, Desk keyboard shortcuts.
- Print Formats, Letterheads, Reports (unless a feature surfaces them).
- Website Settings — *except* favicon + login-page branding (that IS `/app`/login, not `/crm`).
- Other Frappe modules not used by the CRM.

### ⚠️ Risky changes — can BREAK `/crm`
`/crm` code references certain fields **by fieldname**. Avoid, unless you know the impact:
- **Deleting/renaming core fields** the frontend expects (e.g. `status`, `lead_name`,
  `first_name`, `mobile_no`, `email`, `organization`, `deal_owner`).
- **Deleting a Status/Source** that existing records or code rely on.
- **Removing the `Sales User` / `Sales Manager` roles** or the CRM permission rules.
- **Changing a field's type** (e.g. Data → Link) on a field the UI reads.
- Editing **CRM Form Script** with broken JS — it can throw in the `/crm` form.

Rule of thumb: **adding** (custom fields, statuses, views, scripts) is safe; **deleting/renaming
built-ins** is where things break.

---

## 4. Where to make changes — recommendation

| Task | Prefer |
|---|---|
| Add sales users | `/crm` → Settings → Invite (cleaner, auto-role) |
| Brand name/logo/favicon | Seeded in code (`crm/setup/branding.py`) or `/crm` → Settings → Brand |
| Statuses, sources, territories | `/crm` → Settings (falls back to `/app` list if needed) |
| Add a **custom field** | `/app` → Customize Form (then it shows in `/crm`) |
| Assignment rules / SLA | `/crm` → Settings → Assignment Rules / SLA |
| Integrations (email, telephony, WhatsApp) | `/crm` → Settings → Integrations |
| Permissions / roles / record restrictions | `/app` → Users / Role / User Permission |
| Bulk import, data export, error logs, scripts | `/app` (Desk only) |

**Bottom line:** use `/crm` Settings for day-to-day config; drop to `/app` for schema changes
(custom fields), permissions, integrations plumbing, bulk data, and debugging. Almost everything
structural you do in `/app` flows into `/crm` because they share the schema and database — so
**add freely, delete/rename built-ins carefully.**
