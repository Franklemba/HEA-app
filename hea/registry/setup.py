"""Registry module setup: roles, subject groups, and the one-off import of the 2020 file index.

Import the index once per site:
    bench --site <site> execute hea.registry.setup.import_file_index
It skips subjects and files that already exist, so it is safe to run again.
"""

import json
from pathlib import Path

import frappe

REGISTRY_ROLES = (
	"Documentation and Registry Officer",
	"Registry Staff",
	"Departmental Head",
	"General Staff",
	"Management and Authorised Auditors",
)

SUBJECT_GROUPS = (
	("Portfolio Subjects", "Portfolio", "Subjects that are responsibilities of other ministries (Registry Service Manual codes)."),
	("Domestic Subjects", "Domestic", "Subjects that are direct responsibilities of the Higher Education Authority."),
)

# Starting lists, created once; Registry edits them in the desk afterwards.
DEFAULT_URGENCIES = (("Immediate", 3, 1), ("Urgent", 2, 3), ("Routine", 1, 14))
DEFAULT_DELIVERY_MODES = ("Hand Delivery", "Post", "Courier", "Email", "Fax")

INDEX_FILE = Path(__file__).parent / "data" / "file_index_2020.json"


def ensure_roles():
	for role in REGISTRY_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def ensure_subject_groups():
	if not frappe.db.table_exists("File Subject"):
		return
	for name, subject_type, description in SUBJECT_GROUPS:
		if not frappe.db.exists("File Subject", name):
			frappe.get_doc({
				"doctype": "File Subject",
				"subject_name": name,
				"subject_type": subject_type,
				"is_group": 1,
				"description": description,
			}).insert(ignore_permissions=True)


def ensure_settings():
	"""Save Registry Settings once so its defaults (prefix, domestic code, blocked titles) are in force."""
	if not frappe.db.exists("DocType", "Registry Settings"):
		return
	# get_single() fills in defaults on load, so compare against what is actually stored.
	stored = frappe.db.get_singles_dict("Registry Settings")
	settings = frappe.get_single("Registry Settings")
	if any(df.default and not stored.get(df.fieldname) for df in settings.meta.fields):
		for df in settings.meta.fields:
			if df.default and not stored.get(df.fieldname):
				settings.set(df.fieldname, df.default)
		settings.save(ignore_permissions=True)


def ensure_starting_lists():
	"""Create the starting urgencies and delivery modes, only while the lists are empty."""
	if frappe.db.table_exists("Correspondence Urgency") and not frappe.db.count("Correspondence Urgency"):
		for urgency, rank, days in DEFAULT_URGENCIES:
			frappe.get_doc({"doctype": "Correspondence Urgency", "urgency": urgency, "rank": rank,
				"response_days": days}).insert(ignore_permissions=True)
	if frappe.db.table_exists("Delivery Mode") and not frappe.db.count("Delivery Mode"):
		for mode in DEFAULT_DELIVERY_MODES:
			frappe.get_doc({"doctype": "Delivery Mode", "mode": mode}).insert(ignore_permissions=True)


def before_migrate():
	ensure_roles()
	from hea.registry.routing_setup import ensure_charts
	ensure_charts()  # before the workspace that shows them is synced


def after_migrate():
	ensure_roles()
	ensure_settings()
	ensure_subject_groups()
	ensure_starting_lists()
	from hea.registry.routing_setup import setup_routing
	setup_routing()
	from hea.registry.movement_setup import setup_movement
	setup_movement()


def import_file_index():
	"""Load the subjects and files of the 2020 Portfolio and Domestic File Index."""
	ensure_roles()
	ensure_settings()
	ensure_subject_groups()
	data = json.loads(INDEX_FILE.read_text())
	frappe.flags.in_import = True

	new_subjects = 0
	for s in data["subjects"]:
		if frappe.db.exists("File Subject", s["subject_code"]):
			continue
		frappe.get_doc({
			"doctype": "File Subject",
			"subject_code": s["subject_code"],
			"subject_name": s["subject_name"],
			"subject_type": s["subject_type"],
			"needs_review": 1 if s.get("review_note") else 0,
			"review_note": s.get("review_note"),
		}).insert(ignore_permissions=True)
		new_subjects += 1

	new_files = 0
	for f in data["files"]:
		if frappe.db.exists("Registry File", f["file_number"]):
			continue
		doc = frappe.get_doc({
			"doctype": "Registry File",
			"file_number": f["file_number"],
			"file_subject": f["file_subject"],
			"file_title": f["file_title"],
			"needs_review": 1 if f.get("review_note") else 0,
			"review_note": f.get("review_note"),
			"opened_on": None,
			"opened_by": None,
			"remarks": "Imported from the 2020 file index.",
		})
		doc.flags.from_index = True
		doc.insert(ignore_permissions=True)
		new_files += 1

	frappe.db.commit()
	frappe.flags.in_import = False
	summary = {
		"subjects_added": new_subjects,
		"files_added": new_files,
		"subjects_in_index": len(data["subjects"]),
		"files_in_index": len(data["files"]),
		"subjects_in_system": frappe.db.count("File Subject", {"is_group": 0}),
		"files_in_system": frappe.db.count("Registry File"),
	}
	print(summary)
	return summary
