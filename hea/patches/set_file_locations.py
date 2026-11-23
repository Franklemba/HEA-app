import frappe


def execute():
	"""Files in Registry show where they are: their shelf, or the Registry location."""
	default = frappe.db.get_single_value("Registry Settings", "registry_location") or "Registry"
	frappe.db.sql(
		"""update `tabRegistry File` set current_location = coalesce(nullif(physical_location, ''), %s)
		where ifnull(holder, '') = ''""",
		default,
	)
