import frappe
from frappe import _


def validate(doc, method=None):
    # Blank user = general/link access, which is allowed
    if not doc.user:
        return

    if doc.team:
        if not frappe.db.exists("Drive Team", doc.user):
            frappe.throw(_("Team {0} does not exist").format(doc.user))
    else:
        if not frappe.db.exists("User", {"name": doc.user, "enabled": 1}):
            frappe.throw(
                _("'{0}' is not a valid user. Please select a user from the list.").format(doc.user)
            )