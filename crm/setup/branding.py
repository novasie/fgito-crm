"""FGITO white-label branding.

Single source of truth for the logo: ``crm/public/images/logo.png`` served at
``/assets/crm/images/logo.png``. Every branded surface (CRM sidebar, browser favicon,
Desk navbar, Desk login page, PWA icons) points at that one URL — to change the logo,
replace that single file.

``apply_fgito_branding`` is wired into ``after_migrate`` (see hooks.py) so the branding is
re-applied on every migrate and on fresh sites. It is idempotent.
"""

import os

import frappe

BRAND_NAME = "FGITO"
PRODUCT_NAME = "FGITO CRM"
LOGO = "/assets/crm/images/logo.png"  # logo / app icon (replace crm/public/images/logo.png)
FAVICON = "/assets/crm/images/favicon.svg"  # browser-tab favicon (replace crm/public/images/favicon.svg)


def _versioned(url: str) -> str:
	"""Append ``?v=<mtime>`` so browsers refetch the image after the file is replaced.

	``/assets`` is served with ``Cache-Control: max-age=43200``, so a fixed URL keeps
	serving the previous image for up to 12h after the file on disk changes. Stamping
	the mtime changes the URL whenever the file does, which busts the cache.
	"""
	rel = url.removeprefix("/assets/crm/")
	path = os.path.join(frappe.get_app_path("crm", "public"), *rel.split("/"))
	try:
		return f"{url}?v={int(os.path.getmtime(path))}"
	except OSError:
		return url  # file missing -> fall back to the plain URL rather than breaking branding


def apply_fgito_branding():
	"""Idempotently seed FGITO branding into the CRM app and the Frappe Desk."""
	try:
		logo = _versioned(LOGO)
		# CRM SPA (/crm) — surfaced via frontend/src/stores/settings.js::setupBrand()
		_set_single(
			"FCRM Settings",
			{
				"brand_name": PRODUCT_NAME,
				"brand_logo": logo,
				"favicon": FAVICON,
			},
		)

		# Frappe Desk (/app) — browser-tab title / boot app_name
		_set_single("System Settings", {"app_name": BRAND_NAME})

		# Frappe Desk (/app) — top-left navbar logo
		_set_single("Navbar Settings", {"app_logo": logo})

		# Frappe Desk (/app) — login page + website favicon/branding
		_set_single(
			"Website Settings",
			{
				"app_name": BRAND_NAME,
				"app_logo": logo,
				"favicon": FAVICON,
				"banner_image": logo,
				"splash_image": logo,
				"brand_html": f'<img src="{logo}" style="height:24px" alt="{PRODUCT_NAME}">',
				"copyright": BRAND_NAME,
				"footer_powered": " ",  # blank out the default "Powered by Frappe"
			},
		)

		# Desk workspace: /app/frappe-crm -> /app/fgito-crm (rename the record).
		# Duplicate-safe both ways: if migrate already imported the renamed fixture
		# ("FGITO CRM"), drop the stale "Frappe CRM"; otherwise rename in place.
		_rename_workspace("Frappe CRM", PRODUCT_NAME)

		frappe.clear_cache()
	except Exception:
		# Branding must never break a migrate.
		frappe.log_error(frappe.get_traceback(), "FGITO branding seed failed")


def _rename_workspace(old: str, new: str):
	if frappe.db.exists("Workspace", old):
		if frappe.db.exists("Workspace", new):
			# migrate already imported the renamed fixture -> drop the stale one
			frappe.delete_doc("Workspace", old, force=True, ignore_permissions=True)
		else:
			frappe.rename_doc("Workspace", old, new, force=True)  # no ignore_permissions kwarg in v15
	# enforce brand label/title regardless of path (rename_doc leaves title untouched)
	if frappe.db.exists("Workspace", new):
		frappe.db.set_value("Workspace", new, {"label": new, "title": new})


def _set_single(doctype: str, values: dict):
	"""Set fields on a Single doctype, skipping any field that doesn't exist."""
	if not frappe.db.exists("DocType", doctype):
		return
	meta = frappe.get_meta(doctype)
	for fieldname, value in values.items():
		if meta.has_field(fieldname):
			frappe.db.set_single_value(doctype, fieldname, value)
