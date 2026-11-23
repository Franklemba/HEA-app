"""Daily escalation of overdue correspondence: first to the Departmental Head, then to Management."""

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
from frappe.utils import cint, date_diff, get_url_to_form, getdate

OPEN_STAGES_EXCLUDED = ("Approved", "Filed", "Closed")


def escalate_overdue():
	settings = frappe.get_single("Registry Settings")
	management = [row.user for row in settings.escalation_contacts]
	wait = cint(settings.management_escalation_days)
	today = getdate()

	items = frappe.get_all(
		"Correspondence",
		filters={"due_date": ["<", today], "direction": ["!=", "Outgoing"],
			"workflow_state": ["not in", OPEN_STAGES_EXCLUDED]},
		fields=["name", "subject", "workflow_state", "due_date", "department_head", "current_holder",
			"escalation_level", "escalated_on"],
	)
	done = []
	for item in items:
		if not item.escalation_level:
			level, users = "Departmental Head", [item.department_head] if item.department_head else management
		elif item.escalation_level == "Departmental Head" and date_diff(today, item.escalated_on) >= wait:
			level, users = "Management", management
		else:
			continue
		users = [u for u in users if u]
		if not users:
			continue
		notify(item, level, users, date_diff(today, item.due_date))
		frappe.db.set_value("Correspondence", item.name, {"escalation_level": level, "escalated_on": today},
			update_modified=False)
		frappe.get_doc("Correspondence", item.name).add_comment(
			"Info", _("Overdue: escalated to {0} ({1}).").format(_(level), ", ".join(users)))
		done.append(item.name)
	frappe.db.commit()
	return done


def notify(item, level, users, days_overdue):
	subject = _("Overdue {0} days: {1} ({2})").format(days_overdue, item.subject, item.name)
	holder = item.current_holder or _("Registry")
	make_notification_logs({
		"type": "Alert",
		"document_type": "Correspondence",
		"document_name": item.name,
		"subject": subject,
		"email_content": _("<p>{0} <b>{1}</b> was due on {2} and is still at {3}, with {4}.</p>"
			"<p>You are receiving this as {5}. <a href=\"{6}\">Open the item</a></p>").format(
			item.name, item.subject, frappe.format(item.due_date, "Date"), _(item.workflow_state), holder,
			_(level), get_url_to_form("Correspondence", item.name)),
	}, users)
