frappe.listview_settings["File Movement"] = {
	add_fields: ["status", "is_overdue"],
	get_indicator(doc) {
		if (doc.status === "Out") {
			return doc.is_overdue ? [__("Overdue"), "red", "is_overdue,=,1"] : [__("Out"), "yellow", "status,=,Out"];
		}
		return [__(doc.status), doc.status === "Returned" ? "green" : "gray", `status,=,${doc.status}`];
	},
};
