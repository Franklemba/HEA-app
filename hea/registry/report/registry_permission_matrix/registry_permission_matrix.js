frappe.query_reports["Registry Permission Matrix"] = {
	filters: [],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "doctype" && data && data.notes) value = `<b>${value}</b>`;
		return value;
	},
};
