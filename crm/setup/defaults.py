"""FGITO system defaults.

Idempotently sets the system-wide defaults that the Setup Wizard would normally
populate. Sites created programmatically (Docker ``create-site``, automated
``bench new-site``) skip the wizard, so ``System Settings.language`` comes up
**blank** — and because that field is mandatory, saving System Settings from the
``/crm`` "System Defaults" screen fails with *"Value missing for System Settings:
Language"*. This seed backfills it.

- ``System Settings.language`` → ``en`` and ``time_zone`` → ``Asia/Kolkata``
  (only if empty — never clobbers a deliberate choice made later). Both are
  mandatory, so a blank one blocks saving System Settings from ``/crm``.
- Default currency → ``INR`` (Global Defaults + the ``currency`` default), so the
  Budget / annual_revenue / deal amount Currency fields render as ₹.

Wired into ``after_install`` (crm/install.py) and ``after_migrate`` (crm/hooks.py)
so it re-applies on fresh sites and every migrate. Mirrors ``crm/setup/branding.py``
— the whole body is wrapped in try/except so a bad seed never blocks a migrate.
"""

import frappe

DEFAULT_CURRENCY = "INR"

# Mandatory System Settings fields the Setup Wizard normally fills. Backfilled only
# when blank, so a deliberate change made later is never clobbered. A blank one of
# these blocks saving System Settings from the /crm "System Defaults" screen.
SYSTEM_SETTINGS_DEFAULTS = {
	"language": "en",
	"time_zone": "Asia/Kolkata",
}


def apply_fgito_defaults():
	"""Idempotently backfill mandatory System Settings and set the INR default currency."""
	try:
		_ensure_system_settings()
		_ensure_currency()
		frappe.clear_cache()
	except Exception:
		# Defaults must never break a migrate.
		frappe.log_error(frappe.get_traceback(), "FGITO defaults seed failed")


def _ensure_system_settings():
	"""Backfill blank mandatory System Settings fields (the automated-site gap)."""
	for fieldname, value in SYSTEM_SETTINGS_DEFAULTS.items():
		if not frappe.db.get_single_value("System Settings", fieldname):
			frappe.db.set_single_value("System Settings", fieldname, value)


def _ensure_currency():
	"""Point the system default currency at INR (Global Defaults + currency default)."""
	if frappe.db.get_single_value("Global Defaults", "default_currency") != DEFAULT_CURRENCY:
		frappe.db.set_single_value("Global Defaults", "default_currency", DEFAULT_CURRENCY)
	frappe.db.set_default("currency", DEFAULT_CURRENCY)
