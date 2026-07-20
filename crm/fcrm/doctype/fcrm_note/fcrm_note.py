# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# Maps a note's reference doctype to the source fields that feed the
# denormalized {first_name, mobile_no, organization} columns on FCRM Note.
# The note reference is a Dynamic Link, so these values cannot be joined or
# filtered across it in the list query and must be copied onto the note.
NOTE_REFERENCE_FIELD_MAP = {
	"CRM Lead": {"first_name": "first_name", "mobile_no": "mobile_no", "organization": "organization"},
	"CRM Deal": {"first_name": "first_name", "mobile_no": "mobile_no", "organization": "organization_name"},
}


def get_reference_details(reference_doctype, reference_docname):
	"""Resolve the denormalized note fields from the referenced lead/deal.

	Returns a dict with keys first_name, mobile_no, organization. Values are
	None when there is no reference, the reference points to an unsupported
	doctype, or the referenced record no longer exists.
	"""
	empty = {"first_name": None, "mobile_no": None, "organization": None}
	field_map = NOTE_REFERENCE_FIELD_MAP.get(reference_doctype)
	if not (field_map and reference_docname):
		return empty

	values = frappe.db.get_value(
		reference_doctype, reference_docname, list(field_map.values()), as_dict=True
	)
	if not values:
		return empty

	return {note_field: values.get(src) for note_field, src in field_map.items()}


def sync_reference_notes(doc, method=None):
	"""on_update hook for CRM Lead / CRM Deal: keep referencing notes in sync.

	Only writes when a relevant source field actually changed, and updates all
	matching notes in a single query without bumping their `modified` (so an
	unrelated lead/deal edit does not reorder the Notes list).
	"""
	field_map = NOTE_REFERENCE_FIELD_MAP.get(doc.doctype)
	if not field_map:
		return
	if not any(doc.has_value_changed(src) for src in field_map.values()):
		return

	values = {note_field: doc.get(src) for note_field, src in field_map.items()}
	frappe.db.set_value(
		"FCRM Note",
		{"reference_doctype": doc.doctype, "reference_docname": doc.name},
		values,
		update_modified=False,
	)


class FCRMNote(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		content: DF.TextEditor | None
		first_name: DF.Data | None
		mobile_no: DF.Data | None
		organization: DF.Data | None
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.set_reference_details()

	def set_reference_details(self):
		details = get_reference_details(self.reference_doctype, self.reference_docname)
		self.first_name = details["first_name"]
		self.mobile_no = details["mobile_no"]
		self.organization = details["organization"]

	@staticmethod
	def default_list_data():
		rows = [
			"name",
			"title",
			"content",
			"reference_doctype",
			"reference_docname",
			"first_name",
			"mobile_no",
			"organization",
			"owner",
			"modified",
		]
		return {"columns": [], "rows": rows}
