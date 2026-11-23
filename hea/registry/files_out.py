"""Files Out, Overdue Files and Files Due Today: paper files away from Registry (one script report each)."""

import frappe
from frappe import _
from frappe.utils import date_diff, get_fullname, getdate, now_datetime

from hea.registry.mail_register import col

COLUMNS = [
	col("issued_to", "Held By", "Link", 160, "User"),
	col("holder_name", "Name", width=150),
	col("department", "Department", "Link", 150, "Department"),
	col("registry_file", "File", "Link", 130, "Registry File"),
	col("file_title", "File Title", width=240),
	col("issued_on", "Out Since", "Datetime", 150),
	col("due_back", "Due Back", "Date", 100),
	col("days_out", "Days Out", "Int", 80),
	col("days_overdue", "Days Overdue", "Int", 100),
	col("urgency", "Label", width=90),
	col("name", "Movement", "Link", 130, "File Movement"),
]


def execute(which, filters=None):
	filters = frappe._dict(filters or {})
	today = getdate()
	conditions = [["status", "=", "Out"]]
	if which == "overdue":
		conditions.append(["due_back", "<", today])
	elif which == "due_today":
		conditions.append(["due_back", "=", today])
	for field in ("issued_to", "department", "registry_file"):
		if filters.get(field):
			conditions.append([field, "=", filters.get(field)])
	rows = frappe.get_list("File Movement", filters=conditions,
		fields=["name", "issued_to", "department", "registry_file", "file_title", "issued_on", "due_back", "urgency", "colour"],
		order_by="issued_to asc, due_back asc", limit_page_length=0)
	now = now_datetime()
	for r in rows:
		r["holder_name"] = get_fullname(r.issued_to)
		r["days_out"] = date_diff(now, r.issued_on)
		r["days_overdue"] = max(date_diff(today, r.due_back), 0)
	holders = len({r.issued_to for r in rows})
	summary = [
		{"label": _("Files"), "value": len(rows), "indicator": "blue"},
		{"label": _("People Holding Them"), "value": holders, "indicator": "blue"},
		{"label": _("Overdue"), "value": sum(1 for r in rows if r["days_overdue"]), "indicator": "red"},
	]
	return COLUMNS, rows, None, None, summary
