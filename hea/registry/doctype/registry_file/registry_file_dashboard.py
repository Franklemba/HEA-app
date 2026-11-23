from frappe import _


def get_data():
	return {
		"fieldname": "registry_file",
		"transactions": [
			{"label": _("Correspondence"), "items": ["Correspondence"]},
			{"label": _("Paper File"), "items": ["File Movement", "File Request"]},
		],
	}
