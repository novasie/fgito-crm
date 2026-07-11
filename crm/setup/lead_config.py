"""FGITO Lead custom-field configuration.

Idempotently shapes the CRM Lead to Fgito's food-delivery sales process:

- Adds business fields (Lead Potential, Service Type, Lead Type, Address group,
  Order Date/Count, Budget) as Custom Fields on ``CRM Lead``.
- Relabels the built-in ``source`` field to "Lead Source" (kept as the dynamic,
  create-on-the-fly marketing-channel dropdown) and seeds Meta Ads / Google Ads.
- Injects the new fields into the ``/crm`` create form (``CRM Lead-Quick Entry``)
  and the detail Side Panel (``CRM Lead-Side Panel``).

Wired into ``after_install`` (crm/install.py) and ``after_migrate`` (crm/hooks.py) so it
re-applies on fresh sites and every migrate. Mirrors ``crm/setup/branding.py`` — the whole
body is wrapped in try/except so a bad seed never blocks a migrate. Every step is idempotent.

"Service Type" is a Link to the flat ``CRM Service Type`` master (mirrors CRM Lead Source),
so users create new service types on the fly exactly like Territory.
"""

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# ── Custom fields added to CRM Lead ──────────────────────────────────────────────
# Section Breaks group them tidily in /app Customize Form; /crm sections come from
# the layout records below (patched in _inject_layout).
LEAD_CUSTOM_FIELDS = {
	"CRM Lead": [
		# Qualification
		{
			"fieldname": "fgito_qualification_sb",
			"fieldtype": "Section Break",
			"label": "Qualification",
			"insert_after": "lead_owner",
		},
		{
			"fieldname": "lead_potential",
			"fieldtype": "Select",
			"label": "Lead Potential",
			"options": "\nHot\nWarm\nCold\nInvalid",
			"insert_after": "fgito_qualification_sb",
		},
		{
			"fieldname": "service_type",
			"fieldtype": "Link",
			"label": "Service Type",
			"options": "CRM Service Type",
			"insert_after": "lead_potential",
		},
		{
			"fieldname": "lead_type",
			"fieldtype": "Select",
			"label": "Lead Type",
			"options": "\nCorporate\nRetail",
			"insert_after": "service_type",
		},
		# Address
		{
			"fieldname": "fgito_address_sb",
			"fieldtype": "Section Break",
			"label": "Address",
			"insert_after": "lead_type",
		},
		{
			"fieldname": "address_line1",
			"fieldtype": "Data",
			"label": "Address Line 1",
			"insert_after": "fgito_address_sb",
		},
		{
			"fieldname": "address_line2",
			"fieldtype": "Data",
			"label": "Address Line 2",
			"insert_after": "address_line1",
		},
		{
			"fieldname": "city",
			"fieldtype": "Data",
			"label": "City",
			"insert_after": "address_line2",
		},
		{
			"fieldname": "state",
			"fieldtype": "Data",
			"label": "State",
			"insert_after": "city",
		},
		{
			"fieldname": "pincode",
			"fieldtype": "Data",
			"label": "PIN Code",
			"insert_after": "state",
		},
		# Order & Budget
		{
			"fieldname": "fgito_order_sb",
			"fieldtype": "Section Break",
			"label": "Order & Budget",
			"insert_after": "pincode",
		},
		{
			"fieldname": "order_date",
			"fieldtype": "Date",
			"label": "Order Date",
			"insert_after": "fgito_order_sb",
		},
		{
			"fieldname": "order_count",
			"fieldtype": "Int",
			"label": "Order Count",
			"default": "0",
			"insert_after": "order_date",
		},
		{
			"fieldname": "budget",
			"fieldtype": "Currency",
			"label": "Budget",
			"insert_after": "order_count",
		},
	]
}

# Marketing-channel values added to the existing (dynamic) CRM Lead Source list.
# Referral ≈ Reference and Walk-in ≈ Walk In already ship as defaults.
EXTRA_LEAD_SOURCES = ["Meta Ads", "Google Ads"]

# Sections appended to CRM Lead-Quick Entry (the /crm "Create Lead" dialog).
# `source` (relabeled "Lead Source") is not in the default Quick Entry, so it is
# surfaced here. Order/Budget are intentionally omitted from the create form
# (filled later during nurture) and live only in the Side Panel below.
QUICK_ENTRY_SECTIONS = [
	{
		"name": "fgito_qualification_section",
		"label": "Qualification",
		"columns": [
			{"name": "fgito_qe_qual_c1", "fields": ["lead_potential", "lead_type"]},
			{"name": "fgito_qe_qual_c2", "fields": ["service_type", "source"]},
		],
	},
	{
		"name": "fgito_address_section",
		"label": "Address",
		"columns": [
			{"name": "fgito_qe_addr_c1", "fields": ["address_line1", "address_line2"]},
			{"name": "fgito_qe_addr_c2", "fields": ["city", "state"]},
			{"name": "fgito_qe_addr_c3", "fields": ["pincode"]},
		],
	},
]

# Sections appended to CRM Lead-Side Panel (the /crm Lead detail sidebar).
# `source` is already in the default "Details" section, so it is not repeated here.
SIDE_PANEL_SECTIONS = [
	{
		"label": "Qualification",
		"name": "fgito_qualification_section",
		"opened": True,
		"columns": [
			{
				"name": "fgito_sp_qual_c1",
				"fields": ["lead_potential", "service_type", "lead_type"],
			},
		],
	},
	{
		"label": "Address",
		"name": "fgito_address_section",
		"opened": True,
		"columns": [
			{
				"name": "fgito_sp_addr_c1",
				"fields": ["address_line1", "address_line2", "city", "state", "pincode"],
			},
		],
	},
	{
		"label": "Order & Budget",
		"name": "fgito_order_section",
		"opened": True,
		"columns": [
			{"name": "fgito_sp_order_c1", "fields": ["order_date", "order_count", "budget"]},
		],
	},
]


def apply_fgito_lead_config():
	"""Idempotently add FGITO's Lead fields, relabel Source, seed sources, patch layouts."""
	try:
		_add_custom_fields()
		_relabel_source()
		_seed_lead_sources()
		_inject_layout("CRM Lead-Quick Entry", QUICK_ENTRY_SECTIONS)
		_inject_layout("CRM Lead-Side Panel", SIDE_PANEL_SECTIONS)
		frappe.clear_cache(doctype="CRM Lead")
	except Exception:
		# Lead config must never break a migrate.
		frappe.log_error(frappe.get_traceback(), "FGITO lead config seed failed")


def _add_custom_fields():
	"""Create the CRM Lead custom fields, skipping any that already exist."""
	meta = frappe.get_meta("CRM Lead")
	pending = [f for f in LEAD_CUSTOM_FIELDS["CRM Lead"] if not meta.has_field(f["fieldname"])]
	if pending:
		create_custom_fields({"CRM Lead": pending})
		frappe.clear_cache(doctype="CRM Lead")


def _relabel_source():
	"""Relabel the built-in `source` field to 'Lead Source' (idempotent Property Setter)."""
	ps = frappe.db.exists(
		"Property Setter",
		{"doc_type": "CRM Lead", "field_name": "source", "property": "label"},
	)
	if ps:
		frappe.db.set_value("Property Setter", ps, "value", "Lead Source")
	else:
		make_property_setter(
			"CRM Lead",
			"source",
			"label",
			"Lead Source",
			"Data",
			validate_fields_for_doctype=False,
		)


def _seed_lead_sources():
	"""Add FGITO marketing-channel sources to the CRM Lead Source list if missing."""
	for source in EXTRA_LEAD_SOURCES:
		if frappe.db.exists("CRM Lead Source", source):
			continue
		doc = frappe.new_doc("CRM Lead Source")
		doc.source_name = source
		doc.insert(ignore_permissions=True)


def _inject_layout(layout_name, sections):
	"""Append `sections` to a CRM Fields Layout record, idempotent by section `name`.

	Merges in place (does not force-recreate), so user edits made via the in-app
	layout editors are preserved. A section is only added if its `name` is absent.
	"""
	if not frappe.db.exists("CRM Fields Layout", layout_name):
		return
	doc = frappe.get_doc("CRM Fields Layout", layout_name)
	layout = json.loads(doc.layout or "[]")
	existing = {section.get("name") for section in layout}
	changed = False
	for section in sections:
		if section["name"] not in existing:
			layout.append(section)
			changed = True
	if changed:
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
