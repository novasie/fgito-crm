# Fgito Lead — Custom Field Spec

The Fgito (food-delivery) additions to the **CRM Lead**. Everything here is applied
**in code** (reproducible, version-controlled) by an idempotent seed —
[`crm/setup/lead_config.py`](../crm/setup/lead_config.py) — wired into `after_install`
and `after_migrate`, so it re-applies on every `bench migrate` and on fresh sites.

> Scope is **Lead only**. Deals come later. On lead→deal conversion, a custom field
> carries over to the Deal **only if CRM Deal has the same fieldname** — noted for that phase.

## New custom fields on CRM Lead

| # | Label | fieldname | Type | Options / default |
|---|---|---|---|---|
| 1 | Lead Potential | `lead_potential` | Select | Hot / Warm / Cold / Invalid |
| 2 | Service Type | `service_type` | Link → `CRM Service Type` | dynamic — create on the fly (like Territory) |
| 3 | Lead Type | `lead_type` | Select | Corporate / Retail |
| 4 | Address Line 1 | `address_line1` | Data | — |
| 5 | Address Line 2 | `address_line2` | Data | — |
| 6 | City | `city` | Data | — |
| 7 | State | `state` | Data | — |
| 8 | PIN Code | `pincode` | Data | — |
| 9 | Order Date | `order_date` | Date | — |
| 10 | Order Count | `order_count` | Int | default `0` |
| 11 | Budget | `budget` | Currency | system-default currency |

Three **Section Break** fields group these tidily in `/app` Customize Form:
`fgito_qualification_sb` (Qualification), `fgito_address_sb` (Address), `fgito_order_sb` (Order & Budget).

## Reused / unchanged

| Field | Change |
|---|---|
| `source` (Link → CRM Lead Source) | Relabeled to **"Lead Source"** via Property Setter; values `Meta Ads` + `Google Ads` seeded (Referral ≈ Reference and Walk-in ≈ Walk In already ship). Stays a dynamic, filterable dropdown. |
| `status` (Link → CRM Lead Status) | **No change** — kept exactly as-is. |

## Service Type master — `CRM Service Type`

A flat master (mirrors `CRM Lead Source`, **not** the Territory tree) at
[`crm/fcrm/doctype/crm_service_type/`](../crm/fcrm/doctype/crm_service_type/):
one field `service_type_name` (Data, required, unique), module FCRM, `quick_entry` on.
Starts **empty** — sales users type a new service type in the Lead's Service Type dropdown
and pick **"Create New"** to add it. Pre-seed defaults later by adding names to
`EXTRA_*`-style loops in the seed if wanted.

## Where the fields show in `/crm`

The seed merges new sections into two `CRM Fields Layout` records (idempotent by section
name; user edits via the in-app pencil editors are preserved):

- **Create-Lead form** (`CRM Lead-Quick Entry`): **Qualification** (Lead Potential, Lead Type,
  Service Type, Lead Source) + **Address** group. *(Order Date / Count / Budget are omitted from
  the create form — filled later during nurture.)*
- **Lead side panel** (`CRM Lead-Side Panel`): **Qualification**, **Address**, and **Order & Budget**
  sections, all editable on the Lead page.

## Apply / re-apply

```bash
bench --site crm.localhost migrate
# or, without a full migrate:
bench --site crm.localhost execute crm.setup.lead_config.apply_fgito_lead_config
```

## Verify

1. `/crm` → **+ Create Lead** shows Lead Potential, Service Type, Lead Type, Lead Source, and the Address group; the Service Type dropdown offers **"Create New"**.
2. Open a Lead → side panel shows **Qualification / Address / Order & Budget**; Budget formats as currency, Order Count is numeric, Order Date is a date picker.
3. A fresh site (`bench new-site … && install-app crm`) comes up with all fields already present.
