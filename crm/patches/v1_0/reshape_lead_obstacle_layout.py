"""Re-shape the Lead "Obstacle & Next Action" group so Next Action sits on its own row.

The group originally shipped as a single Data Fields section with Next Action stacked in
the middle column. FieldLayout renders a section's columns side by side, so putting Next
Action (a textarea) on the last row means splitting it into a second, label-less section.

`_inject_layout` deliberately never touches a section that already exists, so sites that
received the first shape would keep it forever. Dropping the old section here lets
`apply_fgito_lead_config` re-inject both sections in their current shape. Runs once.
"""

from crm.setup.lead_config import apply_fgito_lead_config, drop_layout_sections


def execute():
	drop_layout_sections("CRM Lead-Data Fields", ["fgito_obstacle_section"])
	apply_fgito_lead_config()
