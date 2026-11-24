"""Registry Test Lab: sample users, a lab subject with lab files, a clock you can move forward, and a reset.

Everything the lab creates is marked: users end in @hea-lab.test, files sit under the subject "LAB – TEST LAB SUBJECT".
Real files and correspondence are never touched. Run from the Registry Lab screen (System Manager).
"""

import re
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date

DOMAIN = "hea-lab.test"
LAB_SUBJECT = "LAB – TEST LAB SUBJECT"
QA, LEGAL = "Quality Assurance - HEA", "Legal - HEA"

USERS = (  # login, first name, last name, role
	("lab.officer", "Lab", "Records Officer", "Documentation and Registry Officer"),
	("lab.registry", "Lab", "Registry Clerk", "Registry Staff"),
	("lab.qa.head", "Lab", "QA Director", "Departmental Head"),
	("lab.legal.head", "Lab", "Legal Director", "Departmental Head"),
	("lab.qa.officer", "Lab", "QA Officer", "General Staff"),
	("lab.qa.officer2", "Lab", "QA Officer Two", "General Staff"),
	("lab.dg", "Lab", "Director General", "Management and Authorised Auditors"),
	("lab.sysadmin", "Lab", "System Administrator", "System Manager"),
)
HEADS = {QA: "lab.qa.head", LEGAL: "lab.legal.head"}
FILES = (  # title, department
	("LAB – ACCREDITATION OF LEARNING PROGRAMMES – SAMPLE UNIVERSITY", QA),
	("LAB – COMPLAINTS AGAINST HIGHER EDUCATION INSTITUTIONS", QA),
	("LAB – STAFF DISCIPLINARY CASES", LEGAL),
	("LAB – BOARD PAPERS 2025", QA),
)


def email(login):
	return f"{login}@{DOMAIN}"


def lab_users():
	return [email(u[0]) for u in USERS]


def require_admin():
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only a System Manager can run the Registry Lab."), frappe.PermissionError)


def lab_subject():
	return frappe.db.get_value("File Subject", {"subject_name": LAB_SUBJECT}, "name")


def lab_files():
	subject = lab_subject()
	return frappe.get_all("Registry File", {"file_subject": subject}, pluck="name", order_by="file_sequence") if subject else []


def lab_correspondence():
	files = lab_files() or [""]
	on_files = frappe.get_all("Correspondence", {"registry_file": ["in", files]}, pluck="name")
	loose = frappe.get_all("Correspondence", {"owner": ["in", lab_users()], "registry_file": ["is", "not set"]}, pluck="name")
	return on_files + loose


# ---- set up ----------------------------------------------------------------------------------

@frappe.whitelist()
def setup_lab():
	require_admin()
	for login, first, last, role in USERS:
		if not frappe.db.exists("User", email(login)):
			frappe.get_doc({"doctype": "User", "email": email(login), "first_name": first, "last_name": last,
				"send_welcome_email": 0, "user_type": "System User", "roles": [{"role": role}]}).insert(ignore_permissions=True)

	settings = frappe.get_single("Registry Settings")
	taken = {row.department for row in settings.department_heads}
	for department, login in HEADS.items():
		if department not in taken:
			settings.append("department_heads", {"department": department, "head": email(login)})
	if email("lab.dg") not in {r.user for r in settings.escalation_contacts}:
		settings.append("escalation_contacts", {"user": email("lab.dg")})
	settings.save(ignore_permissions=True)

	if settings.drive_team:  # lab users are HEA staff too, so they join the Drive team that holds the scans
		team = frappe.get_doc("Drive Team", settings.drive_team)
		members = {m.user for m in team.users}
		for u in lab_users():
			if u not in members:
				team.append("users", {"user": u, "access_level": 1})
		team.save(ignore_permissions=True)

	if not lab_subject():
		frappe.get_doc({"doctype": "File Subject", "subject_name": LAB_SUBJECT, "subject_type": "Domestic",
			"description": "Test Lab only. Removed by Reset Lab."}).insert(ignore_permissions=True)
	existing = set(frappe.get_all("Registry File", {"file_subject": lab_subject()}, pluck="file_title"))
	for title, department in FILES:
		if title not in existing:
			frappe.get_doc({"doctype": "Registry File", "file_subject": lab_subject(), "file_title": title,
				"department": department, "physical_location": "Lab shelf A"}).insert(ignore_permissions=True)
	frappe.db.commit()
	return status()


@frappe.whitelist()
def status():
	require_admin()
	users = {u.name: u.full_name for u in frappe.get_all("User", {"name": ["in", lab_users()]}, ["name", "full_name"])}
	files = lab_files()
	return {
		"ready": bool(users and files),
		"users": [{"user": email(login), "name": users.get(email(login)), "role": role}
			for login, _f, _l, role in USERS if email(login) in users],
		"subject": lab_subject(),
		"files": [{"name": f, "title": frappe.db.get_value("Registry File", f, "file_title")} for f in files],
		"correspondence": len(lab_correspondence()),
		"movements": frappe.db.count("File Movement", {"registry_file": ["in", files or [""]]}),
	}


# ---- time --------------------------------------------------------------------------------------

@frappe.whitelist()
def fast_forward(days=1):
	"""Move the lab N days into the future (lab dates move N days back), then run the registry's daily jobs."""
	require_admin()
	days = int(days)
	if not 0 <= days <= 60:
		frappe.throw(_("Choose between 0 and 60 days."))
	if days:
		back = lambda value: add_days(value, -days) if value else value
		back_dt = lambda value: add_to_date(value, days=-days) if value else value
		for name in lab_correspondence():
			row = frappe.db.get_value("Correspondence", name, ["due_date", "escalated_on", "register_date"], as_dict=True)
			frappe.db.set_value("Correspondence", name, {k: back(v) for k, v in row.items()}, update_modified=False)
		for f in lab_files():
			for m in frappe.get_all("File Movement", {"registry_file": f},
					["name", "issued_on", "due_back", "last_reminded_on", "returned_on"]):
				frappe.db.set_value("File Movement", m.name, {"issued_on": back_dt(m.issued_on), "due_back": back(m.due_back),
					"last_reminded_on": back(m.last_reminded_on), "returned_on": back_dt(m.returned_on)}, update_modified=False)
			row = frappe.db.get_value("Registry File", f, ["due_back", "out_since", "bring_up_date"], as_dict=True)
			frappe.db.set_value("Registry File", f, {"due_back": back(row.due_back), "out_since": back_dt(row.out_since),
				"bring_up_date": back(row.bring_up_date)}, update_modified=False)
	frappe.db.commit()
	return run_daily_jobs()


def run_daily_jobs():
	"""The registry's morning jobs, as the scheduler runs them: escalation, overdue files, and date reminders."""
	from hea.registry.escalation import escalate_overdue
	from hea.registry.movement import flag_overdue_files

	result = {"escalated": escalate_overdue(), "overdue_files": flag_overdue_files(), "reminders": []}
	lab_items, files = set(lab_correspondence()), set(lab_files())
	for name in frappe.get_all("Notification", {"event": ["in", ["Days Before", "Days After"]], "enabled": 1,
			"document_type": ["in", ["Correspondence", "Registry File"]]}, pluck="name"):
		n = frappe.get_doc("Notification", name)
		for doc in n.get_documents_for_today():
			if doc.name in lab_items or doc.name in files:  # lab records only; the scheduler handles real ones
				n.send(doc)
				result["reminders"].append(f"{name}: {doc.name}")
	frappe.db.commit()
	return result


# ---- reset -------------------------------------------------------------------------------------

@frappe.whitelist()
def reset_lab(remove_users=0):
	"""Delete everything the lab made. With remove_users, also the lab users and their settings rows."""
	require_admin()
	frappe.flags.registry_lab_reset = True
	try:
		files = lab_files()
		items = lab_correspondence()
		folder_titles = [f.replace("/", "-") for f in files] or [""]
		drive = frappe.get_all("Drive File", {"owner": ["in", lab_users()]}, ["name", "path"]) + frappe.get_all(
			"Drive File", {"is_group": 1, "title": ["in", folder_titles]}, ["name", "path"])
		for name in items:
			frappe.db.set_value("Correspondence", name, "docstatus", 2, update_modified=False)
		requests = frappe.get_all("File Request", {"registry_file": ["in", files or [""]]}, pluck="name")
		movements = frappe.get_all("File Movement", {"registry_file": ["in", files or [""]]}, pluck="name")
		for f in files:
			frappe.db.set_value("Registry File", f, "current_movement", None, update_modified=False)
		for dt, names in (("File Request", requests), ("File Movement", movements), ("Correspondence", items)):
			for name in names:
				frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		for log_dt, field in (("Confidential View Log", "viewed_name"), ("Registry Deletion Log", "deleted_name")):
			for name in frappe.get_all(log_dt, {field: ["in", (items + files) or [""]]}, pluck="name"):
				frappe.delete_doc(log_dt, name, force=True, ignore_permissions=True)
		for f in files:
			frappe.delete_doc("Registry File", f, force=True, ignore_permissions=True)
		if lab_subject():
			frappe.delete_doc("File Subject", lab_subject(), force=True, ignore_permissions=True)

		site_files = Path(frappe.get_site_path("private/files")).resolve()
		for d in drive:
			if frappe.db.exists("Drive File", d.name):
				frappe.delete_doc("Drive File", d.name, force=True, ignore_permissions=True)
			path = (site_files / d.path).resolve() if d.path else None
			if path and path != site_files and path.is_relative_to(site_files):
				frappe.db.after_commit.add(lambda p=path: _remove(p))
		for name in frappe.get_all("File", {"owner": ["in", lab_users()], "is_folder": 0}, pluck="name"):
			frappe.delete_doc("File", name, force=True, ignore_permissions=True)
		frappe.db.delete("Notification Log", {"for_user": ["in", lab_users()]})
		rewind_series()

		if int(remove_users):
			settings = frappe.get_single("Registry Settings")
			settings.department_heads = [r for r in settings.department_heads if r.head not in lab_users()]
			settings.escalation_contacts = [r for r in settings.escalation_contacts if r.user not in lab_users()]
			settings.save(ignore_permissions=True)
			if settings.drive_team:
				team = frappe.get_doc("Drive Team", settings.drive_team)
				team.users = [m for m in team.users if m.user not in lab_users()]
				team.save(ignore_permissions=True)
			for u in lab_users():
				if frappe.db.exists("User", u):
					frappe.delete_doc("User", u, force=True, ignore_permissions=True)
		frappe.db.commit()
	finally:
		frappe.flags.registry_lab_reset = False
	return {"removed": True} if int(remove_users) else status()


def _remove(path):
	if path.is_file():
		path.unlink(missing_ok=True)
	elif path.is_dir() and not any(path.iterdir()):
		path.rmdir()


def rewind_series():
	"""Give back the numbers the lab used, so the first real item is still number 1."""
	for like, doctype in (("HEA/%", "Correspondence"), ("FM-%", "File Movement"), ("FR-%", "File Request"),
			("DEL-%", "Registry Deletion Log")):
		for prefix, _current in frappe.db.sql("select name, current from tabSeries where name like %s", like):
			used = [int(m.group(1)) for n in frappe.get_all(doctype, {"name": ["like", prefix + "%"]}, pluck="name")
				if (m := re.match(re.escape(prefix) + r"(\d+)$", n))]
			frappe.db.sql("update tabSeries set current=%s where name=%s", (max(used, default=0), prefix))
