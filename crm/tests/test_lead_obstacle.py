import json

import frappe

from crm.api.lead_obstacle import DEFAULT_OBSTACLES, category_options, obstacle_category
from crm.tests import CRMTestCase as FrappeTestCase


class TestLeadObstacle(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# The obstacle fields and master records are seeded on install/migrate; a test
		# site built by `install-app` may predate this change, so make sure they exist.
		from crm.setup.lead_config import apply_fgito_lead_config

		apply_fgito_lead_config()

	def _lead(self, **kwargs):
		lead = frappe.get_doc({"doctype": "CRM Lead", "first_name": "Obstacle", **kwargs})
		lead.insert(ignore_permissions=True)
		return lead

	def _layout(self, name):
		return json.dumps(frappe.db.get_value("CRM Fields Layout", name, "layout") or "")

	# ── master doctype ───────────────────────────────────────────────────────────

	def test_default_obstacles_are_seeded_with_their_category(self):
		self.assertEqual(len(DEFAULT_OBSTACLES), 20)
		for name, category in DEFAULT_OBSTACLES.items():
			self.assertTrue(frappe.db.exists("CRM Lead Obstacle", name), f"{name} not seeded")
			self.assertEqual(frappe.db.get_value("CRM Lead Obstacle", name, "category"), category)

	def test_obstacle_master_is_addable_from_the_ui(self):
		"""The Link dropdown's "Create New" opens a plain insert — no special handling."""
		meta = frappe.get_meta("CRM Lead Obstacle")
		self.assertTrue(meta.quick_entry)
		self.assertEqual(meta.search_fields, "category")
		self.assertTrue(meta.get_field("category").reqd, "an uncategorised obstacle breaks reporting")

	def test_user_added_obstacle_derives_its_category(self):
		frappe.get_doc(
			{
				"doctype": "CRM Lead Obstacle",
				"obstacle_name": "Awaiting Festival Date",
				"category": "Operations",
			}
		).insert(ignore_permissions=True)

		lead = self._lead(current_obstacle="Awaiting Festival Date")
		self.assertEqual(lead.obstacle_category, "Operations")

	def test_unknown_obstacle_is_rejected_by_link_validation(self):
		lead = frappe.get_doc(
			{"doctype": "CRM Lead", "first_name": "Obstacle", "current_obstacle": "Not A Real Obstacle"}
		)
		self.assertRaises(frappe.LinkValidationError, lead.insert)

	# ── field shape ──────────────────────────────────────────────────────────────

	def test_custom_fields_have_the_expected_shape(self):
		meta = frappe.get_meta("CRM Lead")
		for fieldname in (
			"current_obstacle",
			"obstacle_category",
			"obstacle_updated_on",
			"next_action",
			"next_action_updated_on",
			"obstacle_change_log",
		):
			self.assertTrue(meta.has_field(fieldname), f"{fieldname} is missing")

		obstacle = meta.get_field("current_obstacle")
		self.assertEqual(obstacle.fieldtype, "Link")
		self.assertEqual(obstacle.options, "CRM Lead Obstacle")
		# Not reqd: a hard flag would reject background saves of legacy leads.
		self.assertFalse(obstacle.reqd)

		self.assertEqual(meta.get_field("next_action").fieldtype, "Small Text")
		self.assertEqual(meta.get_field("next_action_date").fieldtype, "Date")
		self.assertFalse(meta.get_field("next_action_date").reqd)
		self.assertEqual(meta.get_field("obstacle_category").options, category_options())
		self.assertTrue(meta.get_field("obstacle_category").read_only)

	def test_obstacle_category_helper(self):
		self.assertEqual(obstacle_category("Awaiting Payment"), "Commercial")
		self.assertEqual(obstacle_category(None), "")

	# ── layout placement ─────────────────────────────────────────────────────────

	def test_section_lives_in_the_data_tab_and_not_the_side_panel(self):
		self.assertIn("fgito_obstacle_section", self._layout("CRM Lead-Data Fields"))
		self.assertIn("current_obstacle", self._layout("CRM Lead-Data Fields"))
		self.assertNotIn("fgito_obstacle_section", self._layout("CRM Lead-Side Panel"))

	def test_next_action_renders_on_the_row_below_the_obstacle(self):
		"""Columns render side by side, so "last row" means a section of its own."""
		layout = json.loads(frappe.db.get_value("CRM Fields Layout", "CRM Lead-Data Fields", "layout"))
		names = [section.get("name") for section in layout]
		self.assertEqual(names[-2:], ["fgito_obstacle_section", "fgito_next_action_section"])

		next_action = layout[-1]
		self.assertTrue(next_action["hideLabel"], "must read as one group with the obstacle above")
		self.assertTrue(next_action["hideBorder"])
		self.assertEqual(
			[column["fields"] for column in next_action["columns"]],
			[["next_action"], ["next_action_date"], ["next_action_updated_on"]],
		)
		# The obstacle row above must not still carry Next Action fields.
		obstacle = layout[-2]
		obstacle_fields = [f for column in obstacle["columns"] for f in column["fields"]]
		self.assertEqual(obstacle_fields, ["current_obstacle", "obstacle_category", "obstacle_updated_on"])

	def test_reapplying_the_config_does_not_duplicate_the_sections(self):
		from crm.setup.lead_config import apply_fgito_lead_config

		apply_fgito_lead_config()
		layout = json.loads(frappe.db.get_value("CRM Fields Layout", "CRM Lead-Data Fields", "layout"))
		names = [section.get("name") for section in layout]
		self.assertEqual(names.count("fgito_obstacle_section"), 1)
		self.assertEqual(names.count("fgito_next_action_section"), 1)

	# ── category + timestamps ────────────────────────────────────────────────────

	def test_category_and_timestamp_are_set_on_create(self):
		lead = self._lead(current_obstacle="Awaiting Payment")
		self.assertEqual(lead.obstacle_category, "Commercial")
		self.assertIsNotNone(lead.obstacle_updated_on)

	def test_lead_without_obstacle_is_not_stamped(self):
		"""has_value_changed reports True for every field on insert; guard against that."""
		lead = self._lead()
		self.assertFalse(lead.current_obstacle)
		self.assertFalse(lead.obstacle_category)
		self.assertIsNone(lead.obstacle_updated_on)
		self.assertEqual(lead.obstacle_change_log, [])

	def test_timestamp_only_moves_when_the_obstacle_changes(self):
		lead = self._lead(current_obstacle="Price Concern")
		stamped = lead.obstacle_updated_on

		lead.first_name = "Renamed"
		lead.save()
		self.assertEqual(lead.obstacle_updated_on, stamped, "unrelated save must not re-stamp")

		lead.current_obstacle = "Wrong Number"
		lead.save()
		self.assertNotEqual(lead.obstacle_updated_on, stamped)
		self.assertEqual(lead.obstacle_category, "Invalid")

	def test_next_action_stamps_independently(self):
		lead = self._lead(current_obstacle="Awaiting Quantity")
		self.assertIsNone(lead.next_action_updated_on)

		lead.next_action = "Call the customer back.\nConfirm headcount for Friday."
		lead.save()
		self.assertIsNotNone(lead.next_action_updated_on)
		stamped = lead.next_action_updated_on

		lead.current_obstacle = "Awaiting Payment"
		lead.save()
		self.assertEqual(lead.next_action_updated_on, stamped, "obstacle change must not re-stamp it")

	def test_next_action_date_is_stored_and_filterable(self):
		lead = self._lead(
			current_obstacle="Awaiting Payment",
			next_action="Send payment link",
			next_action_date="2026-07-23",
		)
		self.assertEqual(str(lead.next_action_date), "2026-07-23")
		overdue = frappe.get_all(
			"CRM Lead",
			filters={"name": lead.name, "next_action_date": ["<", "2026-07-24"]},
			pluck="name",
		)
		self.assertEqual(overdue, [lead.name])

	# ── history log ──────────────────────────────────────────────────────────────

	def test_change_log_opens_a_row_and_closes_it_with_a_duration(self):
		lead = self._lead(current_obstacle="Awaiting Meal Selection")
		self.assertEqual(len(lead.obstacle_change_log), 1)

		opened = lead.obstacle_change_log[0]
		self.assertEqual(opened.get("from"), "Awaiting Meal Selection")
		self.assertEqual(opened.from_type, "Buying Decision")
		self.assertIsNotNone(opened.from_date)
		self.assertFalse(opened.to_date)

		lead.current_obstacle = "Awaiting Payment"
		lead.save()

		self.assertEqual(len(lead.obstacle_change_log), 2)
		closed = lead.obstacle_change_log[0]
		self.assertEqual(closed.to, "Awaiting Payment")
		self.assertEqual(closed.to_type, "Commercial")
		self.assertIsNotNone(closed.to_date)
		self.assertIsNotNone(closed.duration)
		self.assertEqual(lead.obstacle_change_log[1].get("from"), "Awaiting Payment")
		self.assertFalse(lead.obstacle_change_log[1].to_date)

	# ── enforcement ──────────────────────────────────────────────────────────────

	def test_lead_can_be_created_without_an_obstacle(self):
		"""Inbound paths (Facebook sync, data import, API) must not be blocked."""
		lead = self._lead(email="inbound@example.com")
		self.assertTrue(frappe.db.exists("CRM Lead", lead.name))

	def test_legacy_lead_without_an_obstacle_still_saves(self):
		lead = self._lead()
		lead.first_name = "Background Update"
		lead.save()  # must not raise
		self.assertEqual(lead.first_name, "Background Update")

	def test_clearing_a_set_obstacle_is_blocked(self):
		lead = self._lead(current_obstacle="Menu Clarification")
		lead.current_obstacle = None
		self.assertRaises(frappe.MandatoryError, lead.save)
