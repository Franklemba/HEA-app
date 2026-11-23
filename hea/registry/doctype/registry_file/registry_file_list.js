frappe.listview_settings["Registry File"] = {
	add_fields: ["status", "needs_review", "holder", "is_overdue", "put_away_requested"],
	get_indicator(doc) {
		if (doc.needs_review) return [__("Needs Review"), "orange", "needs_review,=,1"];
		if (doc.status === "Closed") return [__("Closed"), "gray", "status,=,Closed"];
		if (doc.is_overdue) return [__("Overdue"), "red", "is_overdue,=,1"];
		if (doc.put_away_requested) return [__("Put Away"), "blue", "put_away_requested,=,1"];
		if (doc.holder) return [__("Out"), "yellow", "holder,is,set"];
		return [__("In Registry"), "green", "status,=,Open|holder,is,not set"];
	},
};
