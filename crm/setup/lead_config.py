"""FGITO Lead custom-field configuration.

Idempotently shapes the CRM Lead to Fgito's food-delivery sales process:

- Adds business fields (Lead Potential, Service Type, Lead Type, Address group,
  Order Date/Count, Budget, Obstacle & Next Action) as Custom Fields on ``CRM Lead``.
- Relabels the built-in ``source`` field to "Lead Source" (kept as the dynamic,
  create-on-the-fly marketing-channel dropdown) and seeds Meta Ads / Google Ads.
- Injects the new fields into the ``/crm`` create form (``CRM Lead-Quick Entry``), the
  detail Side Panel (``CRM Lead-Side Panel``) and the detail Data tab
  (``CRM Lead-Data Fields``).

Wired into ``after_install`` (crm/install.py) and ``after_migrate`` (crm/hooks.py) so it
re-applies on fresh sites and every migrate. Mirrors ``crm/setup/branding.py`` — the whole
body is wrapped in try/except so a bad seed never blocks a migrate. Every step is idempotent.

"Service Type" is a Link to the flat ``CRM Service Type`` master (mirrors CRM Lead Source),
so users create new service types on the fly exactly like Territory.

"Current Obstacle" is a Link to the ``CRM Lead Obstacle`` master (mirrors Service Type), so
sales ops add obstacles from the dropdown's "Create New" rather than by editing code.

"Current Obstacle" is deliberately *not* ``reqd``. Frappe's server-side mandatory check
reads ``reqd`` only, so a hard flag would reject every background save of the pre-existing
obstacle-less backlog (SLA recalcs, communication sync, note sync) — not just interactive
edits. Instead the field is mandatory via ``mandatory_depends_on`` in the UI, and
``crm.api.lead_obstacle`` blocks clearing an obstacle that was already set. See that module
for the derived category and TAT timestamps.
"""

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from crm.api.lead_obstacle import category_options, seed_obstacles

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
		# Obstacle & Next Action
		{
			"fieldname": "fgito_obstacle_sb",
			"fieldtype": "Section Break",
			"label": "Obstacle & Next Action",
			"insert_after": "budget",
		},
		{
			"fieldname": "current_obstacle",
			"fieldtype": "Link",
			"label": "Current Obstacle",
			# Link (not Select) so the /crm dropdown offers "Create New" and sales ops can
			# add an obstacle without a deploy — every Link field except User gets that
			# affordance automatically (frontend/src/components/FieldLayout/Field.vue).
			"options": "CRM Lead Obstacle",
			"in_standard_filter": 1,
			# Client-side only (frappe never evaluates this server-side), and `doc.name`
			# is the create-vs-edit discriminator the /crm frontend actually has —
			# `__islocal` is only set on grid child rows there. See apply_fgito_lead_config.
			"mandatory_depends_on": "eval: !!doc.name",
			"insert_after": "fgito_obstacle_sb",
		},
		{
			"fieldname": "obstacle_category",
			"fieldtype": "Select",
			"label": "Obstacle Category",
			"options": category_options(),
			"read_only": 1,
			"in_standard_filter": 1,
			"insert_after": "current_obstacle",
		},
		{
			"fieldname": "obstacle_updated_on",
			"fieldtype": "Datetime",
			"label": "Obstacle Updated On",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "obstacle_category",
		},
		{
			"fieldname": "next_action",
			"fieldtype": "Small Text",
			"label": "Next Action",
			"insert_after": "obstacle_updated_on",
		},
		{
			"fieldname": "next_action_date",
			"fieldtype": "Date",
			"label": "Next Action Date",
			# When the follow-up is due, as opposed to next_action_updated_on (when the
			# text was last edited). Filter `< today` for the overdue-follow-ups list.
			"in_standard_filter": 1,
			"insert_after": "next_action",
		},
		{
			"fieldname": "next_action_updated_on",
			"fieldtype": "Datetime",
			"label": "Next Action Updated On",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "next_action_date",
		},
		{
			"fieldname": "obstacle_change_log",
			"fieldtype": "Table",
			"label": "Obstacle Change Log",
			# Reuses the generic status-change child table; from_type/to_type carry the
			# obstacle category. Kept out of the Side Panel — it is an audit trail, read
			# in /app or via reports.
			"options": "CRM Status Change Log",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "next_action_updated_on",
		},
	]
}

# Properties that must be reconciled on sites where the field already exists.
# `create_custom_fields` only ever creates, so a field that shipped earlier with a
# different shape (current_obstacle was a Select before the CRM Lead Obstacle master
# existed; next_action was a Data) would otherwise keep its old definition forever.
MANAGED_FIELD_PROPERTIES = {
	"current_obstacle": {"fieldtype": "Link", "options": "CRM Lead Obstacle"},
	"obstacle_category": {"fieldtype": "Select", "options": category_options()},
	"next_action": {"fieldtype": "Small Text", "options": None},
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
	# Optional at create time (the obstacle is often only known after first contact),
	# but surfaced here so a rep logging a call can capture it immediately.
	{
		"name": "fgito_obstacle_section",
		"label": "Obstacle & Next Action",
		"columns": [
			{"name": "fgito_qe_obs_c1", "fields": ["current_obstacle"]},
			{"name": "fgito_qe_obs_c2", "fields": ["next_action"]},
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

# Sections appended to CRM Lead-Data Fields (the /crm Lead detail "Data" tab).
# Obstacle & Next Action lives here rather than the Side Panel: `next_action` is a
# textarea and the group carries six fields, which the narrow sidebar cannot show well.
#
# Two sections, not one: FieldLayout renders a section's columns side by side
# (`flex sm:flex-row` in Section.vue), so the only way to put Next Action on its own row
# *below* the obstacle is a second section. `hideLabel`/`hideBorder` keep the two reading
# as a single group — the same trick CRM Deal's default Data Fields layout uses.
DATA_FIELDS_SECTIONS = [
	{
		"label": "Obstacle & Next Action",
		"name": "fgito_obstacle_section",
		"opened": True,
		"columns": [
			{"name": "fgito_df_obs_c1", "fields": ["current_obstacle"]},
			{"name": "fgito_df_obs_c2", "fields": ["obstacle_category"]},
			{"name": "fgito_df_obs_c3", "fields": ["obstacle_updated_on"]},
		],
	},
	{
		"label": "Next Action",
		"name": "fgito_next_action_section",
		"opened": True,
		"hideLabel": True,
		"hideBorder": True,
		"columns": [
			{"name": "fgito_df_na_c1", "fields": ["next_action"]},
			{"name": "fgito_df_na_c2", "fields": ["next_action_date"]},
			{"name": "fgito_df_na_c3", "fields": ["next_action_updated_on"]},
		],
	},
]

# Sections retired from a layout they were previously injected into. `_inject_layout` only
# ever adds, so moving a section between layouts needs an explicit removal for sites that
# already received it.
RETIRED_SECTIONS = {
	"CRM Lead-Side Panel": ["fgito_obstacle_section"],
}


def apply_fgito_lead_config():
	"""Idempotently add FGITO's Lead fields, relabel Source, seed sources, patch layouts."""
	try:
		# Seed the obstacle master first: `current_obstacle` becomes a Link to it below,
		# and leads already carrying a value would fail link validation without it.
		seed_obstacles()
		_add_custom_fields()
		_sync_field_properties()
		_relabel_source()
		_seed_lead_sources()
		_inject_layout("CRM Lead-Quick Entry", QUICK_ENTRY_SECTIONS)
		_inject_layout("CRM Lead-Side Panel", SIDE_PANEL_SECTIONS)
		_inject_layout("CRM Lead-Data Fields", DATA_FIELDS_SECTIONS)
		_remove_layout_sections()
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


def _sync_field_properties():
	"""Bring already-created custom fields in line with MANAGED_FIELD_PROPERTIES."""
	changed = False
	for fieldname, properties in MANAGED_FIELD_PROPERTIES.items():
		name = frappe.db.exists("Custom Field", {"dt": "CRM Lead", "fieldname": fieldname})
		if not name:
			continue
		current = frappe.db.get_value("Custom Field", name, list(properties), as_dict=True)
		stale = {k: v for k, v in properties.items() if (current.get(k) or None) != (v or None)}
		if stale:
			frappe.db.set_value("Custom Field", name, stale)
			changed = True
	if changed:
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
	buckets = _section_buckets(layout)
	if not buckets:
		return
	existing = {section.get("name") for bucket in buckets for section in bucket}
	changed = False
	for section in sections:
		if section["name"] not in existing:
			# Append to the last tab so the new section lands at the end of the form.
			buckets[-1].append(section)
			changed = True
	if changed:
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)


def _remove_layout_sections():
	"""Drop sections listed in RETIRED_SECTIONS from layouts that still carry them.

	Needed when a section moves between layouts: `_inject_layout` only ever adds, so
	without this a site that already received the section would end up showing it twice.
	"""
	for layout_name, names in RETIRED_SECTIONS.items():
		drop_layout_sections(layout_name, names)


def drop_layout_sections(layout_name, names):
	"""Remove `names` from a CRM Fields Layout. Returns True if anything was removed.

	Public because patches use it to retire a section shape that `_inject_layout` would
	otherwise leave alone forever — see crm/patches/v1_0/reshape_lead_obstacle_layout.py.
	"""
	if not frappe.db.exists("CRM Fields Layout", layout_name):
		return False
	doc = frappe.get_doc("CRM Fields Layout", layout_name)
	layout = json.loads(doc.layout or "[]")
	changed = False
	for bucket in _section_buckets(layout):
		for section in [s for s in bucket if s.get("name") in names]:
			bucket.remove(section)
			changed = True
	if changed:
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
	return changed


def _section_buckets(layout):
	"""Return the mutable section lists in `layout`, for both flat and tabbed formats.

	CRM Lead's layouts are stored as a flat list of sections, but the in-app editors can
	save the tabbed form (`[{"name": "first_tab", "sections": [...]}]`) that CRM Deal
	already uses. Returning the lists themselves keeps both shapes editable in place.
	"""
	if not isinstance(layout, list):
		return []
	if any(isinstance(entry, dict) and "sections" in entry for entry in layout):
		return [entry["sections"] for entry in layout if isinstance(entry, dict) and "sections" in entry]
	return [layout]
