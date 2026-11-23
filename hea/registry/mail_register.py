"""The incoming, outgoing and internal mail registers (one script report each, sharing this code)."""

import frappe
from frappe import _


def col(fieldname, label, fieldtype="Data", width=120, options=None):
	c = {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "width": width}
	if options:
		c["options"] = options
	return c


REFERENCE = col("name", "Reference Number", "Link", 170, "Correspondence")
FILE = col("registry_file", "File", "Link", 130, "Registry File")
FOLIO = col("folio_number", "Folio", width=70)
SUBJECT = col("subject", "Subject", width=260)
SCAN = col("scanned", "Scan", width=60)

COLUMNS = {
	"Incoming": [
		REFERENCE, col("register_date", "Date Received", "Date", 105), col("their_reference", "Their Reference"),
		col("letter_date", "Letter Date", "Date", 100), col("sender", "From", width=170), SUBJECT,
		col("department", "Department", "Link", 150, "Department"), FILE, FOLIO,
		col("urgency", "Urgency", width=90), col("mode_of_delivery", "Delivered By", width=110),
		col("enclosures", "Encl.", "Int", 60), SCAN,
	],
	"Outgoing": [
		REFERENCE, col("register_date", "Date Sent", "Date", 100), col("recipient", "To", width=170), SUBJECT,
		col("sender_department", "From Department", "Link", 150, "Department"), FILE, FOLIO,
		col("copies_sent_to", "Copies Sent To", width=150), col("dispatch_mode", "Means of Dispatch", width=120),
		col("dispatched_on", "Dispatched", "Date", 100), col("dispatched_by", "Dispatched By", "Link", 140, "User"),
		col("received_by", "Received By", width=130), SCAN,
	],
	"Internal": [
		REFERENCE, col("register_date", "Date", "Date", 100), col("sender", "From", width=150),
		col("sender_department", "From Department", "Link", 150, "Department"), col("recipient", "To", width=150),
		col("department", "Department Responsible", "Link", 150, "Department"), SUBJECT, FILE, FOLIO,
		col("urgency", "Urgency", width=90), SCAN,
	],
}


def execute(direction, filters=None):
	filters = frappe._dict(filters or {})
	conditions = [["direction", "=", direction]]
	if filters.from_date:
		conditions.append(["register_date", ">=", filters.from_date])
	if filters.to_date:
		conditions.append(["register_date", "<=", filters.to_date])
	if filters.registry_file:
		conditions.append(["registry_file", "=", filters.registry_file])
	or_conditions = None
	if filters.department:
		or_conditions = [["department", "=", filters.department], ["sender_department", "=", filters.department]]

	columns = COLUMNS[direction]
	fields = [c["fieldname"] for c in columns if c["fieldname"] != "scanned"] + ["scan"]
	rows = frappe.get_list(
		"Correspondence",
		filters=conditions,
		or_filters=or_conditions,
		fields=fields,
		order_by="register_date asc, creation asc",
		limit_page_length=0,
	)
	for row in rows:
		row["scanned"] = _("Yes") if row.pop("scan", None) else ""
	return columns, rows
