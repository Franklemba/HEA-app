frappe.listview_settings["Registry File"] = {
	add_fields: ["status", "needs_review"],
	get_indicator(doc) {
		if (doc.needs_review) return [__("Needs Review"), "orange", "needs_review,=,1"];
		return doc.status === "Closed"
			? [__("Closed"), "gray", "status,=,Closed"]
			: [__("Open"), "green", "status,=,Open"];
	},
};
