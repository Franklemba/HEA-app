# Copyright (c) 2026, Higher Education Authority and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import add_days, cint, getdate, nowdate

from hea.registry.drive import DRIVE_URL_PREFIX, file_scan_in_drive

SERIES_FIELD = {"Incoming": "incoming_series", "Outgoing": "outgoing_series", "Internal": "internal_series"}
REGISTRY_ROLES = {"Documentation and Registry Officer", "Registry Staff", "System Manager"}

# Stage -> who has the item. None means Registry.
HOLDER_FIELD = {
	"Assigned to Department": "department_head",
	"Assigned to Officer": "assigned_officer",
	"Action Taken": "department_head",
	"Under Review": "department_head",
}
FINISHED_STAGES = ("Filed", "Closed")

# What a head or an officer may change on an item; everything else is Registry's.
HEAD_FIELDS = {"assigned_officer", "due_date", "send_back_reason", "send_back_pending", "escalation_level", "escalated_on"}
OFFICER_FIELDS = {"action_taken"}
# Checked by the workflow (stage) or worked out again on every save (holder).
SYSTEM_FIELDS = {"workflow_state", "current_holder"}


class Correspondence(Document):
	def autoname(self):
		series = (frappe.db.get_single_value("Registry Settings", SERIES_FIELD[self.direction]) or "").strip()
		if not series:
			frappe.throw(_("Set the {0} reference series in Registry Settings.").format(_(self.direction)))
		self.reference_number = make_autoname(series, doc=self)
		self.name = self.reference_number

	def onload(self):
		from hea.registry.confidentiality import log_view
		log_view(self)

	def before_cancel(self):
		from hea.registry.records import block_cancel
		block_cancel(self)

	def validate(self):
		self.subject = " ".join((self.subject or "").split())
		self.inherit_file_confidentiality()
		self.keep_restricted_scans_out_of_drive()
		self.check_edit_rights()
		self.check_file_is_open()
		self.assign_folio()
		self.set_department_head()
		self.set_due_date()
		self.check_stage_change()
		self.set_current_holder()
		if self.direction != "Outgoing":
			for field in ("copies_sent_to", "dispatch_mode", "dispatched_on", "dispatched_by", "received_by"):
				self.set(field, None)

	def on_update(self):
		if self.scan and self.registry_file and not self.scan.startswith(DRIVE_URL_PREFIX):
			file_scan_in_drive(self)

	# ---- confidentiality ---------------------------------------------------------------------

	def inherit_file_confidentiality(self):
		"""An item is at least as confidential as the file it is on."""
		if not self.registry_file:
			return
		file_level = frappe.db.get_value("Registry File", self.registry_file, "confidentiality_level")
		if not file_level or file_level == self.confidentiality_level:
			return
		rank = lambda lvl: cint(frappe.db.get_value("Confidentiality Level", lvl, "rank")) if lvl else -1
		if rank(file_level) > rank(self.confidentiality_level):
			self.confidentiality_level = file_level

	def keep_restricted_scans_out_of_drive(self):
		from hea.registry.confidentiality import is_restricted
		if self.drive_file and is_restricted(self.confidentiality_level) and self.has_value_changed("confidentiality_level"):
			frappe.throw(_("This item's scan is already in the shared Drive folder. Restricted items keep their scan as a "
				"private attachment: ask the Documentation and Registry Officer to move the scan before restricting the item."))

	# ---- routing ---------------------------------------------------------------------------------

	def is_registry_user(self):
		return bool(REGISTRY_ROLES.intersection(frappe.get_roles()))

	def check_edit_rights(self):
		"""Heads and officers act on an item through its stages; only Registry edits the registration details."""
		if self.is_new() or self.is_registry_user() or frappe.flags.in_escalation:
			return
		before = self.get_doc_before_save()
		changed = {df.fieldname for df in self.meta.fields if before and before.get(df.fieldname) != self.get(df.fieldname)}
		user = frappe.session.user
		allowed = set(SYSTEM_FIELDS)
		if user == (before.department_head if before else None):
			allowed |= HEAD_FIELDS
		if user == (before.assigned_officer if before else None):
			allowed |= OFFICER_FIELDS
		not_allowed = changed - allowed
		if not_allowed:
			labels = ", ".join(_(self.meta.get_label(f)) for f in sorted(not_allowed))
			frappe.throw(_("You cannot change {0} on this item.").format(labels), frappe.PermissionError)

	def set_department_head(self):
		if self.direction == "Outgoing" or not self.department:
			return
		if self.is_new() or self.has_value_changed("department") or not self.department_head:
			self.department_head = department_head(self.department)

	def set_due_date(self):
		if self.direction == "Outgoing" or self.due_date or not self.urgency:
			return
		days = frappe.db.get_value("Correspondence Urgency", self.urgency, "response_days")
		if days:
			self.due_date = add_days(self.register_date or nowdate(), cint(days))

	def check_stage_change(self):
		if self.is_new() or not self.has_value_changed("workflow_state"):
			return
		before = self.get_doc_before_save().workflow_state
		stage = self.workflow_state
		if stage == "Assigned to Department":
			if not self.department:
				frappe.throw(_("Set the Department Responsible first."))
			if not self.department_head:
				frappe.throw(_("No Departmental Head is set for {0} in Registry Settings.").format(frappe.bold(self.department)))
		if stage == "Assigned to Officer":
			if not self.assigned_officer:
				frappe.throw(_("Choose the Action Officer first."))
			if before == "Under Review":
				if not self.send_back_pending:
					frappe.throw(_("Give the reason for sending the item back."))
				self.send_back_pending = 0
		if stage == "Action Taken" and not (self.action_taken or "").strip():
			frappe.throw(_("Record the action taken first."))
		if stage == "Filed" and not (self.registry_file and self.folio_number):
			frappe.throw(_("Put the item on a file and folio before filing it."))
		if stage in FINISHED_STAGES or stage == "Approved":
			self.escalation_level = None

	def set_current_holder(self):
		field = HOLDER_FIELD.get(self.workflow_state)
		self.current_holder = self.get(field) if field else None

	@frappe.whitelist()
	def prepare_action(self, action, values=None):
		"""Save what a workflow action needs (officer, action taken, send-back reason) before the action runs."""
		values = frappe._dict(frappe.parse_json(values) or {})
		if action == "Assign to Officer":
			self.assigned_officer = values.assigned_officer
			if values.due_date:
				self.due_date = values.due_date
		elif action == "Record Action":
			self.action_taken = values.action_taken
		elif action == "Send Back":
			reason = (values.reason or "").strip()
			if not reason:
				frappe.throw(_("Give the reason for sending the item back."))
			self.send_back_reason = reason
			self.send_back_pending = 1
		else:
			return
		self.save()
		if action == "Send Back":
			self.add_comment("Comment", _("Sent back: {0}").format(reason))

	@frappe.whitelist()
	def change_due_date(self, due_date, reason=None):
		self.due_date = getdate(due_date)
		self.escalation_level = None
		self.escalated_on = None
		self.save()
		self.add_comment("Info", _("Due date changed to {0}. {1}").format(
			frappe.format(self.due_date, "Date"), reason or ""))

	def check_file_is_open(self):
		if not self.registry_file or not (self.is_new() or self.has_value_changed("registry_file")):
			return
		if frappe.db.get_value("Registry File", self.registry_file, "status") == "Closed":
			frappe.throw(
				_("File {0} is closed. Put the item on another file, or ask Registry to reopen it.").format(
					frappe.bold(self.registry_file)),
				title=_("Closed file"),
			)

	def assign_folio(self):
		"""Folios per file: main (20), enclosures of a folio (20/1, 20/2) and folios inserted after it (20A, 20B)."""
		if not self.registry_file:
			self.folio_number = self.folio_main = self.folio_sub = self.folio_insert = None
			return
		changed = any(self.has_value_changed(f) for f in ("registry_file", "folio_placement", "folio_reference"))
		if self.folio_number and not changed:
			return

		# One registration at a time per file, so two people never get the same folio.
		frappe.db.sql("select name from `tabRegistry File` where name=%s for update", self.registry_file)
		placement = self.folio_placement or "Next Folio"
		ref = cint(self.folio_reference)
		if placement != "Next Folio" and ref < 1:
			frappe.throw(_("Give the folio number."))

		main, sub, insert = ref, 0, ""
		if placement == "Next Folio":
			main = cint(self.max_on_file("folio_main")) + 1
		elif placement == "Enclosure":
			sub = cint(self.max_on_file("folio_sub", folio_main=main, folio_insert="")) + 1
		elif placement == "Inserted Folio":
			used = self.values_on_file("folio_insert", folio_main=main, folio_sub=0)
			insert = next_insert_letter(used)

		folio = f"{main}{insert}" + (f"/{sub}" if sub else "")
		clash = frappe.db.exists("Correspondence", {
			"registry_file": self.registry_file, "folio_number": folio, "name": ["!=", self.name or ""]})
		if clash:
			frappe.throw(_("Folio {0} on file {1} is already {2}.").format(
				frappe.bold(folio), self.registry_file, frappe.get_desk_link("Correspondence", clash)))
		self.folio_main, self.folio_sub, self.folio_insert, self.folio_number = main, sub, insert, folio

	def other_items_on_file(self, **filters):
		return {"registry_file": self.registry_file, "name": ["!=", self.name or ""], **filters}

	def max_on_file(self, field, **filters):
		values = self.values_on_file(field, **filters)
		return max(values) if values else 0

	def values_on_file(self, field, **filters):
		return [v for v in frappe.get_all("Correspondence", self.other_items_on_file(**filters), pluck=field) if v]

	@frappe.whitelist()
	def record_dispatch(self, dispatch_mode=None, received_by=None, copies_sent_to=None):
		if self.direction != "Outgoing":
			frappe.throw(_("Only outgoing items are dispatched."))
		self.dispatched_on = frappe.utils.nowdate()
		self.dispatched_by = frappe.session.user
		self.dispatch_mode = dispatch_mode or self.dispatch_mode
		self.received_by = received_by or self.received_by
		self.copies_sent_to = copies_sent_to or self.copies_sent_to
		self.save()


def next_insert_letter(used):
	"""A, B ... Z, then AA, AB ... after the letters already used."""
	def to_number(letters):
		n = 0
		for ch in letters:
			n = n * 26 + (ord(ch) - 64)
		return n

	n = max((to_number(u) for u in used), default=0) + 1
	letters = ""
	while n:
		n, rem = divmod(n - 1, 26)
		letters = chr(65 + rem) + letters
	return letters


def department_head(department):
	return frappe.db.get_value(
		"Registry Department Head",
		{"parent": "Registry Settings", "parenttype": "Registry Settings", "department": department},
		"head",
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def officer_query(doctype, txt, searchfield, start, page_len, filters):
	"""Staff of the department (from Employee), or all active desk users when none are linked."""
	department = (filters or {}).get("department")
	like = f"%{txt}%"
	if department:
		rows = frappe.db.sql(
			"""select e.user_id, e.employee_name from `tabEmployee` e
			where e.department=%s and e.status='Active' and ifnull(e.user_id, '')!=''
			and (e.user_id like %s or e.employee_name like %s)
			order by e.employee_name limit %s offset %s""",
			(department, like, like, page_len, start),
		)
		if rows:
			return rows
	return frappe.db.sql(
		"""select name, full_name from `tabUser`
		where enabled=1 and user_type='System User' and name not in ('Administrator', 'Guest')
		and (name like %s or full_name like %s)
		order by full_name limit %s offset %s""",
		(like, like, page_len, start),
	)
