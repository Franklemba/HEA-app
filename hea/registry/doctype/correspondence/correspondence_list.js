frappe.listview_settings["Correspondence"] = {
	add_fields: ["direction", "dispatched_on", "registry_file"],
	get_indicator(doc) {
		if (doc.direction === "Outgoing") {
			return doc.dispatched_on
				? [__("Dispatched"), "green", "dispatched_on,is,set"]
				: [__("Not Dispatched"), "orange", "direction,=,Outgoing|dispatched_on,is,not set"];
		}
		const colour = doc.direction === "Incoming" ? "blue" : "purple";
		return [__(doc.direction), colour, `direction,=,${doc.direction}`];
	},
};
