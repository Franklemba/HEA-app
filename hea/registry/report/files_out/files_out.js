frappe.query_reports["Files Out"] = {
	filters: [
		{ fieldname: "issued_to", label: __("Held By"), fieldtype: "Link", options: "User" },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
		{ fieldname: "registry_file", label: __("File"), fieldtype: "Link", options: "Registry File" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "urgency" && data && data.colour) {
			value = `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${frappe.utils.escape_html(data.colour)}"></span> ${value}`;
		}
		if (column.fieldname === "days_overdue" && data && data.days_overdue > 0) value = `<span class="text-danger">${value}</span>`;
		return value;
	},
};
