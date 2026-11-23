import frappe

NAMES = ("Correspondence Reached You", "Correspondence Ready for Filing", "Correspondence Due Soon")


def execute():
	"""The routing notifications were first created on the Email channel, which fails without an outgoing
	Email Account and then skips the in-system notification too. Move them to System Notification."""
	for name in NAMES:
		if frappe.db.get_value("Notification", name, "channel") == "Email":
			frappe.db.set_value("Notification", name, {"channel": "System Notification", "send_system_notification": 0})
	frappe.cache.hdel("notifications", "Correspondence")
