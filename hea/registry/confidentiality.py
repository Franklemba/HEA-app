"""Need to know: who may see confidential files and correspondence.

A Confidentiality Level with no roles is open. A level with roles is seen only by those roles and by the people
involved in the item. The rules are applied to lists, searches and links (permission query conditions) and to
opening a record (has_permission), and every view of a restricted item is logged.
"""

import frappe
from frappe.utils import now_datetime

BYPASS_USERS = ("Administrator",)


def restricted_levels():
	"""Levels with roles, and their roles: {level: {roles}}."""
	def load():
		rows = frappe.get_all("Confidentiality Level Role", {"parenttype": "Confidentiality Level"}, ["parent", "role"])
		levels = {}
		for r in rows:
			levels.setdefault(r.parent, set()).add(r.role)
		return levels
	return frappe.cache.get_value("hea_restricted_levels", load)


def clear_cache(doc=None, method=None):
	frappe.cache.delete_value("hea_restricted_levels")


def is_restricted(level):
	return bool(level) and level in restricted_levels()


def hidden_levels(user):
	"""Restricted levels this user has no role for."""
	roles = set(frappe.get_roles(user))
	return [lvl for lvl, allowed in restricted_levels().items() if not roles & allowed]


def headed_departments(user):
	return frappe.get_all("Registry Department Head", {"parenttype": "Registry Settings", "head": user}, pluck="department")


def sql_list(values):
	return ", ".join(frappe.db.escape(v) for v in values)


# ---- list / search conditions ---------------------------------------------------------------

def file_condition(user, table="`tabRegistry File`"):
	hidden = hidden_levels(user)
	if not hidden:
		return ""
	u = frappe.db.escape(user)
	involved = [f"{table}.holder = {u}", f"{table}.owner = {u}"]
	depts = headed_departments(user)
	if depts:
		involved.append(f"{table}.department in ({sql_list(depts)})")
	return f"(ifnull({table}.confidentiality_level, '') not in ({sql_list(hidden)}) or {' or '.join(involved)})"


def correspondence_query(user=None):
	user = user or frappe.session.user
	if user in BYPASS_USERS:
		return ""
	hidden = hidden_levels(user)
	if not hidden:
		return ""
	t, u = "`tabCorrespondence`", frappe.db.escape(user)
	involved = " or ".join(f"{t}.{f} = {u}" for f in ("owner", "department_head", "assigned_officer", "current_holder"))
	return f"(ifnull({t}.confidentiality_level, '') not in ({sql_list(hidden)}) or {involved})"


def registry_file_query(user=None):
	user = user or frappe.session.user
	return "" if user in BYPASS_USERS else file_condition(user)


def _via_file(table, own_field, user):
	cond = file_condition(user, "rf")
	if not cond:
		return ""
	u = frappe.db.escape(user)
	return (f"({table}.{own_field} = {u} or {table}.registry_file in "
		f"(select rf.name from `tabRegistry File` rf where {cond}))")


def file_movement_query(user=None):
	user = user or frappe.session.user
	return "" if user in BYPASS_USERS else _via_file("`tabFile Movement`", "issued_to", user)


def file_request_query(user=None):
	user = user or frappe.session.user
	return "" if user in BYPASS_USERS else _via_file("`tabFile Request`", "requested_by", user)


# ---- opening a record -------------------------------------------------------------------------

def can_see_correspondence(doc, user):
	if not is_restricted(doc.get("confidentiality_level")) or doc.confidentiality_level not in hidden_levels(user):
		return True
	return user in {doc.get("owner"), doc.get("department_head"), doc.get("assigned_officer"), doc.get("current_holder")}


def can_see_file(doc, user):
	if not is_restricted(doc.get("confidentiality_level")) or doc.confidentiality_level not in hidden_levels(user):
		return True
	return user in {doc.get("holder"), doc.get("owner")} or doc.get("department") in headed_departments(user)


def _decide(allowed):
	# None lets the role permissions decide; False refuses.
	return None if allowed else False


def correspondence_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if user in BYPASS_USERS or not getattr(doc, "name", None) or doc.get("__islocal"):
		return None
	return _decide(can_see_correspondence(doc, user))


def registry_file_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if user in BYPASS_USERS or not getattr(doc, "name", None) or doc.get("__islocal"):
		return None
	return _decide(can_see_file(doc, user))


def _file_of(doc):
	return frappe.get_cached_doc("Registry File", doc.registry_file) if doc.get("registry_file") else None


def file_movement_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if user in BYPASS_USERS or doc.get("issued_to") == user:
		return None
	f = _file_of(doc)
	return _decide(not f or can_see_file(f, user))


def file_request_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if user in BYPASS_USERS or doc.get("requested_by") == user or doc.get("__islocal"):
		return None
	f = _file_of(doc)
	return _decide(not f or can_see_file(f, user))


def log_view(doc):
	"""Record who opened a restricted item."""
	if not is_restricted(doc.get("confidentiality_level")) or frappe.flags.in_test_no_view_log:
		return
	frappe.get_doc({
		"doctype": "Confidential View Log",
		"viewed_doctype": doc.doctype,
		"viewed_name": doc.name,
		"confidentiality_level": doc.confidentiality_level,
		"viewed_by": frappe.session.user,
		"viewed_on": now_datetime(),
	}).insert(ignore_permissions=True)
