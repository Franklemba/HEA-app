import frappe

DISCIPLINARY_ROLES = (
	"Supervisor",
	"Head of Department",
	"Manager HR",
	"HR Officer",
	"Director General",
	"Disciplinary Board Member",
	"Board Chairperson",
	"HR Board Committee Chairperson",
)


def ensure_roles():
	"""Create the roles the disciplinary workflow, permissions and scripts refer to, if missing."""
	for role in DISCIPLINARY_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def get_employee_user_email(employee):
	"""Email for an Employee, used by notification templates: linked user, then preferred/company/personal email."""
	if not employee:
		return ""
	user_id, prefered_email, company_email, personal_email = frappe.db.get_value(
		"Employee", employee, ["user_id", "prefered_email", "company_email", "personal_email"]
	) or (None, None, None, None)
	return user_id or prefered_email or company_email or personal_email or ""
