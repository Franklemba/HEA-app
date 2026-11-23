from frappe import _


def get_data():
	return {
		"fieldname": "registry_file",
		"transactions": [{"label": _("Correspondence"), "items": ["Correspondence"]}],
	}
