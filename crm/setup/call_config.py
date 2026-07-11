"""FGITO Call Log custom-field configuration.

Idempotently adds a per-call **Call Summary** (Long Text) to ``CRM Call Log`` and
surfaces it in the ``/crm`` "Edit Call Log" form (``CRM Call Log-Quick Entry``), so
reps can jot a summary of each call.

Mirrors ``crm/setup/lead_config.py``: wired into ``after_install`` (crm/install.py)
and ``after_migrate`` (crm/hooks.py), wrapped in try/except so a bad seed never
blocks a migrate, and every step is idempotent.

The fieldname is ``custom_call_summary`` (the ``custom_`` prefix Frappe's Customize
Form applies to UI-added fields) so this seed matches the field first created via the
UI — running it there is a no-op rather than creating a duplicate.
"""

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# ── Custom field added to CRM Call Log ────────────────────────────────────────────
CALL_LOG_CUSTOM_FIELDS = {
	"CRM Call Log": [
		{
			"fieldname": "custom_call_summary",
			"fieldtype": "Long Text",
			"label": "Call Summary",
			"insert_after": "note",
		},
	]
}


def apply_fgito_call_config():
	"""Idempotently add the Call Summary field and surface it in the Edit Call Log form."""
	try:
		_add_custom_fields()
		_ensure_field_in_layout("CRM Call Log-Quick Entry", "custom_call_summary")
		frappe.clear_cache(doctype="CRM Call Log")
	except Exception:
		# Call config must never break a migrate.
		frappe.log_error(frappe.get_traceback(), "FGITO call config seed failed")


def _add_custom_fields():
	"""Create the CRM Call Log custom field, skipping it if it already exists."""
	meta = frappe.get_meta("CRM Call Log")
	pending = [f for f in CALL_LOG_CUSTOM_FIELDS["CRM Call Log"] if not meta.has_field(f["fieldname"])]
	if pending:
		create_custom_fields({"CRM Call Log": pending})
		frappe.clear_cache(doctype="CRM Call Log")


def _ensure_field_in_layout(layout_name, field, section_label="Call Summary"):
	"""Add `field` to a CRM Fields Layout once, idempotent by *field presence*.

	Unlike ``lead_config._inject_layout`` (idempotent by section *name*), this guards on
	whether the field already appears anywhere in the layout — so a field a user already
	added via the in-app / JSON layout editor is never duplicated. Early-returns if the
	layout record is missing (``get_fields_layout`` then falls back to a default layout
	that already includes every field).
	"""
	if not frappe.db.exists("CRM Fields Layout", layout_name):
		return
	doc = frappe.get_doc("CRM Fields Layout", layout_name)
	layout = json.loads(doc.layout or "[]")
	if field in json.dumps(layout):
		return
	layout.append(
		{
			"name": "fgito_call_summary_section",
			"label": section_label,
			"columns": [{"name": "fgito_cl_summary_c1", "fields": [field]}],
		}
	)
	doc.layout = json.dumps(layout)
	doc.save(ignore_permissions=True)
