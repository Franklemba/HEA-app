"""Correspondence not yet approved or filed, with who has it and how overdue it is."""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate

from hea.registry.mail_register import col


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = [["direction", "!=", "Outgoing"], ["workflow_state", "not in", ["Approved", "Filed", "Closed"]]]
	for field in ("department", "assigned_officer", "current_holder", "workflow_state"):
		if filters.get(field):
			conditions.append([field, "=", filters.get(field)])
	if filters.overdue_only:
		conditions.append(["due_date", "<", getdate()])

	columns = [
		col("name", "Reference Number", "Link", 170, "Correspondence"),
		col("register_date", "Registered", "Date", 100),
		col("subject", "Subject", width=240),
		col("workflow_state", "Stage", width=150),
		col("with", "Currently With", width=170),
		col("department", "Department", "Link", 160, "Department"),
		col("assigned_officer", "Action Officer", "Link", 160, "User"),
		col("due_date", "Due Date", "Date", 100),
		col("days_overdue", "Days Overdue", "Int", 100),
		col("escalation_level", "Escalated To", width=130),
	]
	rows = frappe.get_list(
		"Correspondence",
		filters=conditions,
		fields=["name", "register_date", "subject", "workflow_state", "current_holder", "department",
			"assigned_officer", "due_date", "escalation_level"],
		order_by="due_date asc, register_date asc",
		limit_page_length=0,
	)
	today = getdate()
	for row in rows:
		row["with"] = row.pop("current_holder") or _("Registry")
		row["days_overdue"] = max(date_diff(today, row.due_date), 0) if row.due_date else None
	overdue = sum(1 for r in rows if r["days_overdue"])
	summary = [
		{"label": _("Pending"), "value": len(rows), "indicator": "blue"},
		{"label": _("Overdue"), "value": overdue, "indicator": "red" if overdue else "green"},
	]
	return columns, rows, None, None, summary
