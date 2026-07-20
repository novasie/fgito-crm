import frappe

from crm.fcrm.doctype.fcrm_note.fcrm_note import get_reference_details


def execute():
	"""Populate the denormalized first_name / mobile_no / organization fields on
	existing FCRM Notes from their referenced CRM Lead or CRM Deal."""
	notes = frappe.get_all(
		"FCRM Note",
		filters={
			"reference_doctype": ["in", list(("CRM Lead", "CRM Deal"))],
			"reference_docname": ["is", "set"],
		},
		fields=["name", "reference_doctype", "reference_docname"],
	)

	for note in notes:
		details = get_reference_details(note.reference_doctype, note.reference_docname)
		frappe.db.set_value("FCRM Note", note.name, details, update_modified=False)
