# Copyright (c) 2026, Higher Education Authority and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from hea.registry.movement import is_registry, issue, require_registry, transfer, user_department


class FileRequest(Document):
	def before_insert(self):
		self.requested_by = frappe.session.user
		self.status = "Requested"
		self.department = self.department or user_department(self.requested_by)

	def validate(self):
		if self.is_new():
			holder = frappe.db.get_value("Registry File", self.registry_file, "holder")
			if holder == self.requested_by:
				frappe.throw(_("You already hold file {0}.").format(self.registry_file))
			return
		if not is_registry() and not self.flags.from_method:
			before = self.get_doc_before_save()
			if before.status != "Requested" or self.status != before.status or self.registry_file != before.registry_file:
				frappe.throw(_("Registry deals with the request now. You can cancel it while it is open."),
					frappe.PermissionError)

	@frappe.whitelist()
	def issue_file(self, due_back=None, urgency=None, remarks=None):
		"""Registry gives the file to the person who asked: from the shelf, or as a transfer from its holder."""
		require_registry()
		if self.status != "Requested":
			frappe.throw(_("This request is {0}.").format(_(self.status)))
		out = frappe.db.get_value("Registry File", self.registry_file, "current_movement")
		move = transfer if out else issue
		movement = move(self.registry_file, self.requested_by, due_back, urgency, None, remarks or self.purpose,
			file_request=self.name)
		self.update({"status": "Issued", "file_movement": movement.name})
		self.save()
		return movement.name

	@frappe.whitelist()
	def refuse(self, reason):
		require_registry()
		if self.status != "Requested":
			frappe.throw(_("This request is {0}.").format(_(self.status)))
		self.update({"status": "Refused", "refusal_reason": reason})
		self.save()

	@frappe.whitelist()
	def cancel_request(self):
		if frappe.session.user != self.requested_by and not is_registry():
			frappe.throw(_("Only the person who asked can cancel the request."), frappe.PermissionError)
		if self.status != "Requested":
			frappe.throw(_("This request is {0}.").format(_(self.status)))
		self.status = "Cancelled"
		self.flags.from_method = True
		self.save()
