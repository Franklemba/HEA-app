# Copyright (c) 2026, Higher Education Authority and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint

from hea.registry.drive import DRIVE_URL_PREFIX, file_scan_in_drive

SERIES_FIELD = {"Incoming": "incoming_series", "Outgoing": "outgoing_series", "Internal": "internal_series"}


class Correspondence(Document):
	def autoname(self):
		series = (frappe.db.get_single_value("Registry Settings", SERIES_FIELD[self.direction]) or "").strip()
		if not series:
			frappe.throw(_("Set the {0} reference series in Registry Settings.").format(_(self.direction)))
		self.reference_number = make_autoname(series, doc=self)
		self.name = self.reference_number

	def validate(self):
		self.subject = " ".join((self.subject or "").split())
		self.check_file_is_open()
		self.assign_folio()
		if self.direction != "Outgoing":
			for field in ("copies_sent_to", "dispatch_mode", "dispatched_on", "dispatched_by", "received_by"):
				self.set(field, None)

	def on_update(self):
		if self.scan and self.registry_file and not self.scan.startswith(DRIVE_URL_PREFIX):
			file_scan_in_drive(self)

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
