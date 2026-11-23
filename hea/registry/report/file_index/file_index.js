frappe.query_reports["File Index"] = {
	filters: [
		{ fieldname: "subject_type", label: __("Subject Type"), fieldtype: "Select", options: "\nPortfolio\nDomestic" },
		{
			fieldname: "file_subject",
			label: __("Subject"),
			fieldtype: "Link",
			options: "File Subject",
			get_query: () => ({ filters: { is_group: 0 } }),
		},
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nOpen\nClosed" },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
	],
	tree: true,
	name_field: "number",
	parent_field: "",
	initial_depth: 1,
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) value = `<b>${value}</b>`;
		if (column.fieldname === "number" && data && data.file) {
			value = `<a href="/app/registry-file/${encodeURIComponent(data.file)}">${data.file}</a>`;
		}
		return value;
	},
};
