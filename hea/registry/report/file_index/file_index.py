# Copyright (c) 2026, Higher Education Authority and contributors
# For license information, please see license.txt
"""The file index as the registry prints it: each subject, then the files opened under it."""

import frappe
from frappe import _

from hea.registry.doctype.file_subject.file_subject import code_sort_key


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return columns(), data(filters)


def columns():
	return [
		{"fieldname": "number", "label": _("Subject / File Number"), "fieldtype": "Data", "width": 190},
		{"fieldname": "title", "label": _("Subject / File Title"), "fieldtype": "Data", "width": 460},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 80},
		{"fieldname": "department", "label": _("Department"), "fieldtype": "Link", "options": "Department", "width": 160},
		{"fieldname": "opened_on", "label": _("Opened On"), "fieldtype": "Date", "width": 100},
		{"fieldname": "closed_on", "label": _("Closed On"), "fieldtype": "Date", "width": 100},
		{"fieldname": "file", "label": _("File"), "fieldtype": "Link", "options": "Registry File", "hidden": 1},
	]


def data(filters):
	subject_filters = {"is_group": 0}
	if filters.subject_type:
		subject_filters["subject_type"] = filters.subject_type
	if filters.file_subject:
		subject_filters["name"] = filters.file_subject
	subjects = frappe.get_list(
		"File Subject", filters=subject_filters, fields=["name", "subject_code", "subject_name", "subject_type"]
	)
	subjects.sort(key=lambda s: (s.subject_type != "Portfolio", code_sort_key(s.subject_code)))

	file_filters = {}
	if filters.status:
		file_filters["status"] = filters.status
	if filters.department:
		file_filters["department"] = filters.department
	files_by_subject = {}
	for f in frappe.get_list(
		"Registry File",
		filters=file_filters,
		fields=["name", "file_subject", "file_title", "file_sequence", "status", "department", "opened_on", "closed_on"],
		order_by="file_sequence asc",
		limit_page_length=0,
	):
		files_by_subject.setdefault(f.file_subject, []).append(f)

	rows = []
	for s in subjects:
		files = files_by_subject.get(s.name, [])
		if not files and (filters.status or filters.department):
			continue
		rows.append({"number": s.subject_code, "title": s.subject_name.upper(), "indent": 0, "bold": 1})
		for f in files:
			rows.append({
				"number": f.name, "title": f.file_title, "status": f.status, "department": f.department,
				"opened_on": f.opened_on, "closed_on": f.closed_on, "file": f.name, "indent": 1,
			})
	return rows
