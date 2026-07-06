"""FGITO white-label branding.

Single source of truth for the logo: ``crm/public/images/logo.png`` served at
``/assets/crm/images/logo.png``. Every branded surface (CRM sidebar, browser favicon,
Desk navbar, Desk login page, PWA icons) points at that one URL — to change the logo,
replace that single file.

``apply_fgito_branding`` is wired into ``after_migrate`` (see hooks.py) so the branding is
re-applied on every migrate and on fresh sites. It is idempotent.
"""

import frappe

BRAND_NAME = "FGITO"
PRODUCT_NAME = "FGITO CRM"
LOGO = "/assets/crm/images/logo.png"  # logo / app icon (replace crm/public/images/logo.png)
FAVICON = "/assets/crm/images/favicon.svg"  # browser-tab favicon (replace crm/public/images/favicon.svg)


def apply_fgito_branding():
	"""Idempotently seed FGITO branding into the CRM app and the Frappe Desk."""
	try:
		# CRM SPA (/crm) — surfaced via frontend/src/stores/settings.js::setupBrand()
		_set_single(
			"FCRM Settings",
			{
				"brand_name": PRODUCT_NAME,
				"brand_logo": LOGO,
				"favicon": FAVICON,
			},
		)

		# Frappe Desk (/app) — browser-tab title / boot app_name
		_set_single("System Settings", {"app_name": BRAND_NAME})

		# Frappe Desk (/app) — top-left navbar logo
		_set_single("Navbar Settings", {"app_logo": LOGO})

		# Frappe Desk (/app) — login page + website favicon/branding
		_set_single(
			"Website Settings",
			{
				"app_name": BRAND_NAME,
				"app_logo": LOGO,
				"favicon": FAVICON,
				"banner_image": LOGO,
				"splash_image": LOGO,
				"brand_html": f'<img src="{LOGO}" style="height:24px" alt="{PRODUCT_NAME}">',
				"copyright": BRAND_NAME,
				"footer_powered": " ",  # blank out the default "Powered by Frappe"
			},
		)

		frappe.clear_cache()
	except Exception:
		# Branding must never break a migrate.
		frappe.log_error(frappe.get_traceback(), "FGITO branding seed failed")


def _set_single(doctype: str, values: dict):
	"""Set fields on a Single doctype, skipping any field that doesn't exist."""
	if not frappe.db.exists("DocType", doctype):
		return
	meta = frappe.get_meta(doctype)
	for fieldname, value in values.items():
		if meta.has_field(fieldname):
			frappe.db.set_single_value(doctype, fieldname, value)
