# Copyright (c) 2026, Higher Education Authority and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

REGISTRY_ROLES = {"Documentation and Registry Officer", "Registry Staff", "System Manager"}


class RegistryFile(Document):
	def autoname(self):
		prefix = settings_value("file_number_prefix", "HEA")
		code = frappe.db.get_value("File Subject", self.file_subject, ["subject_code", "is_group"], as_dict=True)
		if not code or code.is_group or not code.subject_code:
			frappe.throw(_("Choose a subject with a code, not a group."))

		if self.file_number:
			# An existing paper file being recorded (the index import): keep its number, check it fits the subject.
			match = re.match(rf"^{re.escape(prefix)}/{re.escape(code.subject_code)}/(\d+)$", self.file_number)
			if not match:
				frappe.throw(_("File number {0} does not belong to subject {1}.").format(
					frappe.bold(self.file_number), code.subject_code))
			self.file_sequence = int(match.group(1))
		else:
			self.file_sequence = next_sequence(self.file_subject)
			self.file_number = f"{prefix}/{code.subject_code}/{self.file_sequence}"

		if frappe.db.exists("Registry File", self.file_number):
			frappe.throw(_("File {0} already exists.").format(frappe.bold(self.file_number)))
		self.name = self.file_number

	def validate(self):
		self.file_title = " ".join((self.file_title or "").split())
		if frappe.db.get_value("File Subject", self.file_subject, "is_group"):
			frappe.throw(_("Files are opened under a subject, not a group."))
		self.status = self.status or "Open"
		if self.flags.from_index:
			self.set_current_location()
			# Existing paper files keep their index title; a vague one is flagged for Registry, not refused.
			bad = [w for w in blocked_titles() if w.lower() in self.file_title.lower()]
			if bad:
				self.needs_review = 1
				self.review_note = "; ".join(filter(None, [self.review_note, f"Vague title ({bad[0]}): retitle"]))
			return
		self.set_current_location()
		if self.is_new() or self.has_value_changed("file_title"):
			# Only when the title is set or changed, so older titles never block issuing or closing a file.
			check_title(self.file_title)
		if self.is_new():
			self.status = "Open"
			self.opened_on = self.opened_on or nowdate()
			self.opened_by = self.opened_by or frappe.session.user

	def set_current_location(self):
		if self.holder:
			self.current_location = _("With {0}").format(frappe.utils.get_fullname(self.holder))
		else:
			self.current_location = self.physical_location or settings_value("registry_location", "Registry")

	# ---- paper file movement (see hea.registry.movement) -----------------------------------------

	@frappe.whitelist()
	def issue_file(self, to_user, due_back=None, urgency=None, correspondence=None, remarks=None):
		from hea.registry.movement import issue
		return issue(self.name, to_user, due_back, urgency, correspondence, remarks).name

	@frappe.whitelist()
	def transfer_file(self, to_user, due_back=None, urgency=None, correspondence=None, remarks=None):
		from hea.registry.movement import transfer
		return transfer(self.name, to_user, due_back, urgency, correspondence, remarks).name

	@frappe.whitelist()
	def return_file(self, remarks=None):
		from hea.registry.movement import return_to_registry
		return return_to_registry(self.name, remarks).name

	@frappe.whitelist()
	def extend_due_back(self, due_back, reason=None):
		from hea.registry.movement import extend_due_back
		extend_due_back(self.name, due_back, reason)

	@frappe.whitelist()
	def mark_put_away(self, note=None):
		from hea.registry.movement import mark_put_away
		mark_put_away(self.name, note)

	@frappe.whitelist()
	def set_bring_up(self, bring_up_date=None, note=None):
		from hea.registry.movement import set_bring_up
		set_bring_up(self.name, bring_up_date, note)

	@frappe.whitelist()
	def close_file(self, reason=None):
		require_registry_role()
		if self.status == "Closed":
			frappe.throw(_("File {0} is already closed.").format(self.name))
		self.status = "Closed"
		self.closed_on = nowdate()
		self.closed_by = frappe.session.user
		self.closure_reason = reason
		self.save()
		self.add_comment("Info", _("File closed. {0}").format(reason or ""))

	@frappe.whitelist()
	def reopen_file(self, reason=None):
		require_registry_role()
		if self.status != "Closed":
			frappe.throw(_("File {0} is not closed.").format(self.name))
		self.status = "Open"
		self.closed_on = None
		self.closed_by = None
		self.closure_reason = None
		self.save()
		self.add_comment("Info", _("File reopened. {0}").format(reason or ""))


def settings_value(field, default=None):
	return (frappe.db.get_single_value("Registry Settings", field) or default or "").strip()


def blocked_titles():
	return [t.strip() for t in settings_value("blocked_titles").splitlines() if t.strip()]


def check_title(title):
	"""Titles must say what the file is about: 'General Correspondence' or 'Miscellaneous' are refused."""
	lowered = (title or "").lower()
	for word in blocked_titles():
		if word.lower() in lowered:
			frappe.throw(
				_("File titles must give a clear indication of the subject matter. {0} is not allowed.").format(
					frappe.bold(word)),
				title=_("Vague file title"),
			)


def next_sequence(file_subject):
	"""One more than the highest file number under the subject: 101/4/3 when 101/4/1 and 101/4/2 exist."""
	current = frappe.db.sql(
		"select max(file_sequence) from `tabRegistry File` where file_subject=%s for update", file_subject
	)[0][0]
	return (current or 0) + 1


def require_registry_role():
	if not REGISTRY_ROLES.intersection(frappe.get_roles()):
		frappe.throw(_("Only Registry can open, close or reopen files."), frappe.PermissionError)
