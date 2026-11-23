frappe.listview_settings["File Request"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colour = { Requested: "orange", Issued: "green", Refused: "red", Cancelled: "gray" }[doc.status];
		return [__(doc.status), colour, `status,=,${doc.status}`];
	},
};
