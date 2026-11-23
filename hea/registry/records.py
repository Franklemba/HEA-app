"""Records control: deletion only by the Documentation and Registry Officer, with a reason, logged."""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

OFFICER = "Documentation and Registry Officer"
PROTECTED = ("Correspondence", "Registry File", "File Subject", "File Movement", "File Request")


def is_officer(user=None):
	return OFFICER in frappe.get_roles(user)


def check_delete(doc, method=None):
	"""on_trash of every protected Registry doctype: only through delete_record, by the Officer."""
	if frappe.flags.in_install or frappe.flags.in_uninstall or frappe.flags.in_patch or frappe.flags.in_migrate:
		return
	allowed = frappe.flags.registry_deletion or {}
	if not is_officer():
		frappe.throw(_("Only the Documentation and Registry Officer can delete registry records."), frappe.PermissionError)
	if (allowed.get("doctype"), allowed.get("name")) != (doc.doctype, doc.name):
		frappe.throw(_("Delete registry records with Delete with Reason, so the reason is logged."), frappe.PermissionError)


@frappe.whitelist()
def delete_record(doctype, name, reason):
	if doctype not in PROTECTED:
		frappe.throw(_("{0} is not a registry record.").format(doctype))
	if not is_officer():
		frappe.throw(_("Only the Documentation and Registry Officer can delete registry records."), frappe.PermissionError)
	reason = (reason or "").strip()
	if len(reason) < 5:
		frappe.throw(_("Give the reason for deleting {0}.").format(name))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("delete")
	declared = doc.docstatus == 1
	data = doc.as_json()
	title = doc.get_title()
	if declared:
		# A declared record cannot be cancelled by anyone; the Officer's deletion takes it out of force first.
		doc.db_set("docstatus", 2, update_modified=False)
	frappe.flags.registry_deletion = {"doctype": doctype, "name": name}
	try:
		frappe.delete_doc(doctype, name)
	finally:
		frappe.flags.registry_deletion = None
	copy = frappe.db.get_value("Deleted Document", {"deleted_doctype": doctype, "deleted_name": name}, "name",
		order_by="creation desc")
	log = frappe.get_doc({
		"doctype": "Registry Deletion Log",
		"deleted_doctype": doctype,
		"deleted_name": name,
		"deleted_title": (title or "")[:255],
		"deleted_by": frappe.session.user,
		"deleted_on": now_datetime(),
		"was_declared": 1 if declared else 0,
		"reason": reason,
		"deleted_document": copy,
		"data": data,
	}).insert(ignore_permissions=True)
	return log.name


def block_cancel(doc, method=None):
	frappe.throw(_("A declared record cannot be cancelled. Register a correction that refers to it."),
		frappe.PermissionError)


@frappe.whitelist()
def correction_defaults(name):
	"""Values for a new item that corrects a declared record."""
	old = frappe.get_doc("Correspondence", name)
	old.check_permission("read")
	keep = ("direction", "their_reference", "letter_date", "sender", "sender_department", "recipient", "department",
		"subject", "urgency", "confidentiality_level", "mode_of_delivery", "enclosures", "registry_file")
	values = {f: old.get(f) for f in keep}
	values["corrects_item"] = old.name
	values["subject"] = _("Correction: {0}").format(old.subject)[:255]
	return values
