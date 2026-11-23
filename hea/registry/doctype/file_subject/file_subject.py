# Copyright (c) 2026, Higher Education Authority and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet

CODE_PATTERN = re.compile(r"^\d+/\d+$")


class FileSubject(NestedSet):
	nsm_parent_field = "parent_file_subject"

	def autoname(self):
		# Subjects are known by their code (52/12, 101/1); groups by their name.
		if not self.is_group and not self.subject_code and self.subject_type == "Domestic":
			self.subject_code = next_domestic_code()
		self.name = self.subject_name if self.is_group else self.subject_code

	def validate(self):
		self.subject_code = (self.subject_code or "").strip() or None
		self.subject_name = (self.subject_name or "").strip()

		if self.is_group:
			return

		if not self.subject_code:
			frappe.throw(_("Enter the subject code, for example 52/12."))
		if not CODE_PATTERN.match(self.subject_code):
			frappe.throw(_("Subject code {0} must be two numbers separated by /, for example 52/12.").format(
				frappe.bold(self.subject_code)))

		domestic = self.subject_code.split("/")[0] == domestic_code()
		if self.subject_type == "Domestic" and not domestic:
			frappe.throw(_("Domestic subject codes start with {0}/.").format(domestic_code()))
		if self.subject_type == "Portfolio" and domestic:
			frappe.throw(_("Codes starting with {0}/ are domestic subjects.").format(domestic_code()))

		if not self.parent_file_subject:
			self.parent_file_subject = frappe.db.get_value(
				"File Subject", {"is_group": 1, "subject_type": self.subject_type}, "name")

	def on_update(self):
		super().on_update()


def domestic_code():
	return (frappe.db.get_single_value("Registry Settings", "domestic_code") or "101").strip()


def next_domestic_code():
	"""Next free domestic subject code: 101/24 when 101/1 ... 101/23 exist."""
	prefix = domestic_code() + "/"
	codes = frappe.get_all("File Subject", filters={"subject_code": ["like", prefix + "%"]}, pluck="subject_code")
	numbers = [int(c.split("/")[1]) for c in codes if CODE_PATTERN.match(c)]
	return f"{prefix}{max(numbers, default=0) + 1}"


def code_sort_key(code):
	try:
		return tuple(int(p) for p in (code or "").split("/"))
	except ValueError:
		return (10**9,)


@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False, **filters):
	"""Tree nodes ordered by code (2/7 before 2/16), labelled 'code – name'."""
	nodes = frappe.get_list(
		"File Subject",
		fields=["name as value", "subject_code", "subject_name", "is_group as expandable"],
		filters={"parent_file_subject": parent or ""} if parent else {"parent_file_subject": ["is", "not set"]},
	)
	for n in nodes:
		n["title"] = f"{n.subject_code} – {n.subject_name}" if n.subject_code else n.subject_name
	return sorted(nodes, key=lambda n: (not n.expandable, code_sort_key(n.subject_code), n.subject_name))


@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = make_tree_args(**frappe.form_dict)
	if args.get("parent_file_subject") == "File Subject":
		args.parent_file_subject = None
	frappe.get_doc(args).insert()
