"""The role permission matrix as the system enforces it: for HEA to sign off (Phase 5)."""

import frappe
from frappe import _

from hea.registry.mail_register import col

ROLES = ("System Manager", "Documentation and Registry Officer", "Registry Staff", "Departmental Head", "General Staff",
	"Management and Authorised Auditors")
DOCTYPES = ("Correspondence", "Registry File", "File Subject", "File Movement", "File Request", "Registry Settings",
	"Confidentiality Level", "Correspondence Urgency", "Delivery Mode", "Registry Deletion Log", "Confidential View Log")
RIGHTS = ("read", "write", "create", "submit", "delete", "report", "export", "print")
NOTES = {
	"Correspondence": _("Need to know applies. Heads and officers act only through their workflow steps. Declared when "
		"Closed: no further changes, no cancel. Delete only by the Officer, with a reason."),
	"Registry File": _("Need to know applies. Paper file actions (issue, transfer, return) by Registry; Put Away and "
		"Bring Up by the holder. Delete only by the Officer, with a reason."),
	"File Movement": _("Created by Registry's issue and transfer actions only."),
	"File Request": _("Users see and cancel their own requests; Registry answers them."),
	"Registry Deletion Log": _("Written by the system; nobody edits or deletes it."),
	"Confidential View Log": _("Written by the system; nobody edits or deletes it."),
}


def execute(filters=None):
	columns = [col("doctype", "Record", width=180), col("role", "Role", width=230)] + \
		[col(r, r.title(), "Data", 70) for r in RIGHTS] + [col("only_own", "Own Only", width=80), col("notes", "Rules", width=420)]
	rows = []
	for dt in DOCTYPES:
		perms = {p.role: p for p in frappe.get_meta(dt).permissions if p.permlevel == 0}
		for role in ROLES:
			p = perms.get(role)
			row = {"doctype": dt, "role": role, "notes": NOTES.get(dt, "") if role == ROLES[0] else ""}
			for r in RIGHTS:
				row[r] = "✓" if p and p.get(r) else ""
			row["only_own"] = "✓" if p and p.get("if_owner") else ""
			rows.append(row)
	return columns, rows
