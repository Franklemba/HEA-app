import re

import frappe

NAMES = ("File Requested", "File Request Answered", "File Issued to You", "File Marked Put Away", "File Bring Up")


def execute():
	"""The first file movement notifications called frappe.utils.get_fullname, which notification templates
	cannot use; look the name up with frappe.db.get_value instead."""
	pattern = re.compile(r"frappe\.utils\.get_fullname\(([a-z_.]+)\)")
	for name in NAMES:
		values = frappe.db.get_value("Notification", name, ["subject", "message"], as_dict=True)
		if not values:
			continue
		fixed = {k: pattern.sub(r"frappe.db.get_value('User', \1, 'full_name')", v or "") for k, v in values.items()}
		if fixed != values:
			frappe.db.set_value("Notification", name, fixed)
