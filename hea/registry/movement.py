"""Paper file movement: issue, transfer through Registry, return, Bring Up (BU), Put Away (PA), overdue files.

Every move goes through Registry, as the file index requires: users ask for a file (File Request), Registry
issues it, records transfers to other users and records its return to the shelf.
"""

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
from frappe.utils import add_days, cint, date_diff, get_fullname, get_url_to_form, getdate, now_datetime, nowdate

REGISTRY_ROLES = {"Documentation and Registry Officer", "Registry Staff", "System Manager"}


def is_registry(user=None):
	return bool(REGISTRY_ROLES.intersection(frappe.get_roles(user)))


def require_registry():
	if not is_registry():
		frappe.throw(_("Only Registry records the movement of paper files."), frappe.PermissionError)


def registry_users():
	users = frappe.get_all("Has Role", {"role": ["in", ["Registry Staff", "Documentation and Registry Officer"]],
		"parenttype": "User"}, pluck="parent")
	return sorted(set(frappe.get_all("User", {"name": ["in", users or [""]], "enabled": 1}, pluck="name")))


def setting(field, default=None):
	value = frappe.db.get_single_value("Registry Settings", field)
	return default if value in (None, "") else value


def default_due_back():
	return add_days(nowdate(), cint(setting("file_keep_days", 5)))


def user_department(user):
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "department")


def get_file(name):
	frappe.db.sql("select name from `tabRegistry File` where name=%s for update", name)
	return frappe.get_doc("Registry File", name)


def save_file(doc):
	# Holders and Registry act through these functions only; the checks are made here.
	doc.flags.ignore_permissions = True
	doc.save()


def issue(file_name, to_user, due_back=None, urgency=None, correspondence=None, remarks=None, file_request=None,
		_transferred_from=None):
	"""Registry gives a paper file to a user."""
	require_registry()
	doc = get_file(file_name)
	if doc.current_movement and not _transferred_from:
		frappe.throw(_("File {0} is out with {1}. Record its return, or transfer it.").format(
			doc.name, get_fullname(doc.holder)))
	if not frappe.db.get_value("User", to_user, "enabled"):
		frappe.throw(_("{0} is not an active user.").format(to_user))
	movement = frappe.get_doc({
		"doctype": "File Movement",
		"registry_file": doc.name,
		"issued_to": to_user,
		"department": user_department(to_user),
		"issued_on": now_datetime(),
		"issued_by": frappe.session.user,
		"due_back": due_back or default_due_back(),
		"urgency": urgency,
		"correspondence": correspondence,
		"remarks": remarks,
		"file_request": file_request,
		"transferred_from": _transferred_from,
	}).insert()
	doc.update({"holder": to_user, "current_movement": movement.name, "out_since": movement.issued_on,
		"due_back": movement.due_back, "is_overdue": 0, "put_away_requested": 0, "put_away_by": None, "put_away_on": None})
	save_file(doc)
	return movement


def transfer(file_name, to_user, due_back=None, urgency=None, correspondence=None, remarks=None, file_request=None):
	"""A user passes the file to a colleague; Registry records both steps."""
	require_registry()
	doc = get_file(file_name)
	if not doc.current_movement:
		frappe.throw(_("File {0} is in Registry. Issue it instead.").format(doc.name))
	if doc.holder == to_user:
		frappe.throw(_("File {0} is already with {1}.").format(doc.name, get_fullname(to_user)))
	current = frappe.get_doc("File Movement", doc.current_movement)
	current.update({"status": "Transferred", "returned_on": now_datetime(), "received_by": frappe.session.user})
	current.save()
	movement = issue(file_name, to_user, due_back, urgency, correspondence, remarks, file_request,
		_transferred_from=current.name)
	current.db_set("transferred_to", movement.name)
	return movement


def return_to_registry(file_name, remarks=None):
	"""Registry records the file back on the shelf (after Put Away, or whenever it comes back)."""
	require_registry()
	doc = get_file(file_name)
	if not doc.current_movement:
		frappe.throw(_("File {0} is already in Registry.").format(doc.name))
	current = frappe.get_doc("File Movement", doc.current_movement)
	current.update({"status": "Returned", "returned_on": now_datetime(), "received_by": frappe.session.user})
	if remarks:
		current.remarks = "\n".join(filter(None, [current.remarks, remarks]))
	current.save()
	doc.update({"holder": None, "current_movement": None, "out_since": None, "due_back": None, "is_overdue": 0,
		"put_away_requested": 0})
	save_file(doc)
	return current


def extend_due_back(file_name, due_back, reason=None):
	require_registry()
	doc = get_file(file_name)
	if not doc.current_movement:
		frappe.throw(_("File {0} is in Registry.").format(doc.name))
	if getdate(due_back) < getdate(nowdate()):
		frappe.throw(_("The new due-back date cannot be in the past."))
	current = frappe.get_doc("File Movement", doc.current_movement)
	current.update({"due_back": due_back, "is_overdue": 0, "last_reminded_on": None})
	current.save()
	doc.update({"due_back": due_back, "is_overdue": 0})
	save_file(doc)
	doc.add_comment("Info", _("Due back extended to {0}. {1}").format(frappe.format(getdate(due_back), "Date"), reason or ""))


def mark_put_away(file_name, note=None):
	"""The holder has finished with the file (PA on the minute sheet); Registry is asked to collect it."""
	doc = get_file(file_name)
	if not doc.current_movement:
		frappe.throw(_("File {0} is in Registry.").format(doc.name))
	if frappe.session.user != doc.holder and not is_registry():
		frappe.throw(_("Only the person holding the file can mark it Put Away."), frappe.PermissionError)
	doc.update({"put_away_requested": 1, "put_away_by": frappe.session.user, "put_away_on": now_datetime()})
	save_file(doc)
	doc.add_comment("Info", _("Marked Put Away (PA) by {0}. {1}").format(get_fullname(frappe.session.user), note or ""))


def set_bring_up(file_name, bring_up_date=None, note=None):
	"""Bring Up: Registry and the user are reminded about the file on the date. No date clears it."""
	doc = get_file(file_name)
	if frappe.session.user != doc.holder and not is_registry():
		frappe.throw(_("Only Registry or the person holding the file can set a Bring Up date."), frappe.PermissionError)
	if bring_up_date and getdate(bring_up_date) < getdate(nowdate()):
		frappe.throw(_("The Bring Up date cannot be in the past."))
	doc.update({"bring_up_date": bring_up_date or None, "bring_up_by": frappe.session.user if bring_up_date else None,
		"bring_up_note": note if bring_up_date else None})
	save_file(doc)
	doc.add_comment("Info", _("Bring Up set for {0}. {1}").format(frappe.format(getdate(bring_up_date), "Date"), note or "")
		if bring_up_date else _("Bring Up cleared."))


# ---- daily job ----------------------------------------------------------------------------------

def flag_overdue_files():
	"""Flag files kept past their due-back date and remind the holder and Registry."""
	today = getdate()
	repeat = cint(setting("overdue_reminder_days", 3))
	registry = registry_users()
	flagged = []
	for mv in frappe.get_all("File Movement", {"status": "Out", "due_back": ["<", today]},
			["name", "registry_file", "file_title", "issued_to", "due_back", "is_overdue", "last_reminded_on"]):
		first = not mv.is_overdue
		again = repeat and mv.last_reminded_on and date_diff(today, mv.last_reminded_on) >= repeat
		if not (first or again):
			continue
		days = date_diff(today, mv.due_back)
		make_notification_logs({
			"type": "Alert",
			"document_type": "Registry File",
			"document_name": mv.registry_file,
			"subject": _("File overdue {0} days: {1} {2}").format(days, mv.registry_file, mv.file_title),
			"email_content": _("<p>Paper file <b>{0}</b> {1} was due back in Registry on {2} and is still with {3}.</p>"
				"<p><a href=\"{4}\">Open the file</a></p>").format(mv.registry_file, mv.file_title,
				frappe.format(mv.due_back, "Date"), get_fullname(mv.issued_to), get_url_to_form("Registry File", mv.registry_file)),
		}, sorted(set([mv.issued_to] + registry)))
		frappe.db.set_value("File Movement", mv.name, {"is_overdue": 1, "last_reminded_on": today}, update_modified=False)
		frappe.db.set_value("Registry File", mv.registry_file, "is_overdue", 1, update_modified=False)
		flagged.append(mv.registry_file)
	frappe.db.commit()
	return flagged


@frappe.whitelist()
def movement_history(registry_file):
	frappe.has_permission("Registry File", "read", registry_file, throw=True)
	rows = frappe.get_all("File Movement", {"registry_file": registry_file},
		["name", "issued_to", "issued_on", "issued_by", "due_back", "status", "returned_on", "received_by",
			"is_overdue", "colour", "urgency", "transferred_from"], order_by="issued_on desc")
	for r in rows:
		r.issued_to_name = get_fullname(r.issued_to)
		r.issued_by_name = get_fullname(r.issued_by)
		r.received_by_name = get_fullname(r.received_by) if r.received_by else ""
	return rows
