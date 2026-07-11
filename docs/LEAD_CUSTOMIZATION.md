# Lead Customization Playbook — make the Lead "yours"

How to remap the Lead to your business terminology: **field labels**, **which fields show**,
**custom fields**, **statuses**, and **sources**. UI steps first (do it now, this site); the
reproducible **code** path is at the end (bake your set into git).

> The same steps apply to **Deal**, **Contact**, and **Organization** — just swap the DocType.

## The one rule that keeps `/crm` working
`/crm` renders the Lead **from the DocType schema**, and it references fields by their **internal
fieldname** (`status`, `mobile_no`, `organization`, `lead_name`, …).

- ✅ **Relabel** = change the *display name* of a field. Safe. Shows in `/crm` instantly.
- ❌ **Rename the fieldname** = breaks `/crm` (code looks fields up by name). **Don't.**
- Statuses & sources are **records** (values), not schema — free to add/rename/delete.

---

## 1. Rename field labels (your terminology)
**Where:** `/app/customize-form` → **Form Type = CRM Lead**.

1. Find the field row, edit its **Label** (leave **Name**/fieldname alone), click **Update**.
2. Hard-refresh `/crm` — the new label shows everywhere (it renders `__(field.label)` from meta).

Example remap (edit to taste):

| Fieldname (don't change) | Default label | Your label (example) |
|---|---|---|
| `organization` | Organization | Company |
| `mobile_no` | Mobile No. | Contact Number |
| `lead_owner` | Lead Owner | Account Manager |
| `source` | Source | Enquiry Source |
| `annual_revenue` | Annual Revenue | Deal Value |
| `no_of_employees` | No. of Employees | Company Size |

> Customize Form also lets you set a field **mandatory**, **hidden**, **read-only**, change its
> **options** (for Select fields), and reorder — all safe, all reflected in `/crm`.

---

## 2. Choose which fields appear + their order
No desk needed — do this **in `/crm` as a Manager** (pencil icons):

- **Create form** → click **+ Create Lead** → the **pencil / Edit Fields Layout** in the dialog →
  drag fields in/out, group into sections/columns, rename tab & section headings → Save.
  (Stored as `CRM Lead-Quick Entry` in `CRM Fields Layout`.)
- **Detail side panel** → open any Lead → hover a section → **pencil** → add/remove/reorder fields →
  Save. (Stored as `CRM Lead-Side Panel`.)
- **List columns** → Leads list → the **view controls** (top-right) → **Column settings** →
  pick columns, widths, order. (Stored per-view in `CRM View Settings`.)

---

## 3. Add a brand-new custom field
1. `/app/customize-form` → CRM Lead → **Add Row** at the bottom → set **Label**, a **Type**
   (Data, Select, Link, Date, Check, Currency…), and a stable **fieldname** (snake_case). Update.
2. In `/crm`, add that fieldname to the **Quick Entry** and/or **Side Panel** layout (step 2) so it
   shows on the form. Optionally add it to **list columns**.

That's it — the field is now part of the Lead and stored on every record.

---

## 4. Statuses (your pipeline stages)
**Where:** `/app/crm-lead-status` (list). No editor for this in `/crm`.

Each status has: **name**, **type** (`Open` / `Ongoing` / `On Hold` / `Won` / `Lost`),
**color**, **position** (sort order). `/crm` shows them (dropdown + Kanban columns) ordered by `position`.

**Your current statuses:**

| # | Status | type | color |
|---|---|---|---|
| 1 | New | Open | gray |
| 2 | Contacted | Ongoing | orange |
| 3 | Nurture | Ongoing | blue |
| 4 | Qualified | Won | green |
| 5 | Converted | Won | teal |
| 6 | Unqualified | Lost | red |
| 7 | Junk | Lost | purple |

To change: open a row to edit name/color/type/position, or **New** to add one, or delete unwanted
ones. **A status assigned to existing leads can't be deleted** — first re-assign those leads to
another status, then delete. `type` matters: `Won`/`Lost` mark the lead closed; `Open`/`Ongoing`
are active-pipeline. (Deal statuses live at `/app/crm-deal-status` and add a **probability** %.)

---

## 5. Sources
**Where:** `/app/crm-lead-source` (list). Fields: **name** + **details** (description).

**Your current sources:** Email, Existing Customer, Reference, Advertisement, Cold Calling,
Exhibition, Supplier Reference, Mass Mailing, Customer's Vendor, Campaign, Walk In, Facebook, Website.

Add your own (e.g. **WhatsApp**, **Website Form**, **Referral**, **Walk-in**) and delete ones you
don't use. They appear immediately in the Create-Lead **Source** dropdown.

---

## Safety checklist
- Relabel, don't rename fieldnames. Keep the required fields (`first_name`, `status`).
- Don't delete a status/source that's in use — reassign first.
- After each change, **hard-refresh** `/crm` (⇧⌘R) — meta and layouts are cached.
- Changes made in the UI live in the **database (this site only)** — see below to make them permanent.

---

## Making it reproducible (code path — optional)
UI changes don't travel to a fresh site or into git. To lock in your **canonical FGITO set**
(labels + statuses + sources) so it re-applies on every `bench migrate` and new install, we add a
seed — same pattern as the existing brand seed:

- New `crm/setup/lead_config.py::apply_fgito_lead_config()` (idempotent):
  - **Labels** → `frappe.custom.doctype.property_setter.property_setter.make_property_setter(...)`
    for each field's `label` (mirrors how `crm/api/doc.py` already makes property setters).
  - **Statuses / sources** → upsert records following `crm/install.py::add_default_lead_statuses` /
    `add_default_lead_sources`; delete unwanted defaults.
  - Wrap in `try/except` + `frappe.log_error` so a bad seed never breaks migrate.
- Wire it into `after_migrate` in `crm/hooks.py` (next to `crm.setup.branding.apply_fgito_branding`).

**When you're ready:** finalize your label map + status list + source list in the UI, then tell me
the values and I'll generate `crm/setup/lead_config.py` so your set is version-controlled.

---

## Verify
- Relabel `organization` → "Company" in Customize Form → hard-refresh `/crm` Lead → side panel shows **Company**.
- Add a status at `/app/crm-lead-status` → it appears in the `/crm` status dropdown + Kanban.
- Add a source at `/app/crm-lead-source` → it appears in the Create-Lead **Source** dropdown.
