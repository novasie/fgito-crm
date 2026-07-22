# Copyright (c) 2026, FGITO and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CRMLeadObstacle(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Literal[
			"Buying Decision",
			"Product",
			"Operations",
			"Commercial",
			"Communication",
			"Lost",
			"Invalid",
		]
		description: DF.SmallText | None
		obstacle_name: DF.Data
	# end: auto-generated types

	pass
