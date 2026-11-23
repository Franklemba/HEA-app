# Copyright (c) 2026, Higher Education Authority and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class FileMovement(Document):
	def validate(self):
		if self.due_back and self.issued_on and getdate(self.due_back) < getdate(self.issued_on):
			frappe.throw(_("Due back cannot be before the file was issued."))
		if not self.is_new() and self.has_value_changed("registry_file"):
			frappe.throw(_("The file of a movement cannot be changed."))

	def on_trash(self):
		if frappe.db.get_value("Registry File", self.registry_file, "current_movement") == self.name:
			frappe.throw(_("This is the file's current movement. Record the file's return first."))
