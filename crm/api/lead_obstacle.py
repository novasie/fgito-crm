"""FGITO lead obstacle tracking.

Records *why* a lead has not placed an order yet (``current_obstacle``) and *what
happens next* (``next_action``), so every lead carries an explicit follow-up strategy
rather than just a stage bucket.

``current_obstacle`` is a Link to the ``CRM Lead Obstacle`` master (mirrors CRM Lead
Source / CRM Service Type), so sales ops can add an obstacle on the fly from the Link
dropdown's "Create New" without a deploy. ``DEFAULT_OBSTACLES`` below is therefore *seed
data*, not the live vocabulary — the category of an obstacle is always read from its
master record so user-added obstacles behave identically to seeded ones.

Turnaround time is tracked two ways:

- ``obstacle_updated_on`` / ``next_action_updated_on`` are stamped on every change, so
  "how long has this lead been stuck?" is ``now() - obstacle_updated_on`` — cheap to
  sort and filter in the list view.
- ``obstacle_change_log`` keeps the full transition history for "average days spent in
  Awaiting Payment" analysis. It reuses the generic ``CRM Status Change Log`` child
  doctype (from/to/from_date/to_date/duration/log_owner) with ``from_type``/``to_type``
  holding the obstacle category *as it was at the time of the change*, so recategorising
  a master record later does not rewrite history.

Wired to CRM Lead's ``validate`` via ``doc_events`` in crm/hooks.py.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import get_duration

# The seven groupings from the sales playbook. Fixed: they are the reporting axis, and
# they are the `category` Select options on the CRM Lead Obstacle master.
OBSTACLE_CATEGORIES = [
	"Buying Decision",
	"Product",
	"Operations",
	"Commercial",
	"Communication",
	"Lost",
	"Invalid",
]

# Seed vocabulary, written to CRM Lead Obstacle on install/migrate if missing. Users may
# add more from the UI; nothing here is re-checked or enforced after seeding, and a
# record the user renamed or deleted is not recreated.
DEFAULT_OBSTACLES = {
	"Awaiting Meal Selection": "Buying Decision",
	"Awaiting Quantity": "Buying Decision",
	"Awaiting Family Confirmation": "Buying Decision",
	"Awaiting Budget Decision": "Buying Decision",
	"Wants Customization": "Product",
	"Ingredient Query": "Product",
	"Menu Clarification": "Product",
	"Awaiting Delivery Address": "Operations",
	"Awaiting Delivery Time": "Operations",
	"Service Area Confirmation": "Operations",
	"Awaiting Payment": "Commercial",
	"Price Concern": "Commercial",
	"No Response (Seen)": "Communication",
	"No Response (Unseen)": "Communication",
	"Chose Another Option": "Lost",
	"Not Required Anymore": "Lost",
	"Outside Service Area": "Invalid",
	"Duplicate Lead": "Invalid",
	"Wrong Number": "Invalid",
	"Spam": "Invalid",
}


def category_options():
	"""Select options for the derived, read-only `obstacle_category` on CRM Lead."""
	return "\n" + "\n".join(OBSTACLE_CATEGORIES)


def obstacle_category(obstacle):
	"""Category of `obstacle` from its master record, or "" if unset/unknown."""
	if not obstacle:
		return ""
	return frappe.get_cached_value("CRM Lead Obstacle", obstacle, "category") or ""


def validate(doc, method=None):
	"""CRM Lead validate hook: derive the category and stamp the TAT timestamps."""
	# The custom fields are seeded by crm.setup.lead_config on install/migrate. Guard so
	# a lead can still be saved on a site where that seed has not run (or has failed).
	if not doc.meta.has_field("current_obstacle"):
		return

	_sync_obstacle(doc)
	_sync_next_action(doc)


def _sync_obstacle(doc):
	before, current = _change(doc, "current_obstacle")
	if before == current:
		return

	doc.obstacle_category = obstacle_category(current)
	doc.obstacle_updated_on = now_datetime() if current else None

	# Clearing an obstacle on an existing lead is always a mistake: it strips the
	# follow-up strategy the lead is meant to carry. Blocking only this transition keeps
	# background saves of legacy obstacle-less leads working — see the note in
	# lead_config.py on why `reqd` is not used.
	if before and not current:
		frappe.throw(
			_("Current Obstacle cannot be cleared. Pick the obstacle that applies now."),
			frappe.MandatoryError,
		)

	_log_obstacle_change(doc, current)


def _sync_next_action(doc):
	before, current = _change(doc, "next_action")
	if before == current:
		return

	doc.next_action_updated_on = now_datetime() if current else None


def _change(doc, fieldname):
	"""Return (previous, current) for `fieldname`, normalising None/"" to "".

	`Document.has_value_changed` reports True for every field on insert, which would
	stamp a timestamp onto leads created without an obstacle. Comparing normalised
	values instead means "no obstacle before, no obstacle now" is correctly a no-op.
	"""
	previous = doc.get_doc_before_save()
	before = (previous.get(fieldname) if previous else None) or ""
	return before, (doc.get(fieldname) or "")


def _log_obstacle_change(doc, current):
	"""Close the open history row and open a new one, mirroring add_status_change_log."""
	now = now_datetime()

	open_row = doc.obstacle_change_log[-1] if doc.obstacle_change_log else None
	if open_row and not open_row.to_date:
		open_row.to = current
		open_row.to_type = doc.obstacle_category or ""
		open_row.to_date = now
		open_row.log_owner = frappe.session.user
		open_row.duration = get_duration(open_row.from_date, now)

	if not current:
		# Obstacle cleared: close the history, do not open an empty row.
		return

	doc.append(
		"obstacle_change_log",
		{
			"from": current,
			"from_type": doc.obstacle_category or "",
			"to": "",
			"to_type": "",
			"from_date": now,
			"to_date": "",
			"log_owner": frappe.session.user,
		},
	)


def seed_obstacles():
	"""Create the default CRM Lead Obstacle records, skipping any that already exist.

	Must run before `current_obstacle` is switched to a Link (crm/setup/lead_config.py):
	leads already carrying a Select value would otherwise fail link validation.
	"""
	for name, category in DEFAULT_OBSTACLES.items():
		if frappe.db.exists("CRM Lead Obstacle", name):
			continue
		doc = frappe.new_doc("CRM Lead Obstacle")
		doc.obstacle_name = name
		doc.category = category
		doc.insert(ignore_permissions=True)
