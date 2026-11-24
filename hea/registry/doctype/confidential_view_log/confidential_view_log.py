# Copyright (c) 2026, Higher Education Authority and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ConfidentialViewLog(Document):
	def on_trash(self):
		if not (frappe.flags.in_uninstall or frappe.flags.in_install or frappe.flags.registry_lab_reset):
			frappe.throw("The view log cannot be deleted.", frappe.PermissionError)
