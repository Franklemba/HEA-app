frappe.query_reports["Pending Correspondence"] = {
	filters: [
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
		{ fieldname: "assigned_officer", label: __("Action Officer"), fieldtype: "Link", options: "User" },
		{ fieldname: "current_holder", label: __("Currently With"), fieldtype: "Link", options: "User" },
		{ fieldname: "workflow_state", label: __("Stage"), fieldtype: "Link", options: "Workflow State" },
		{ fieldname: "overdue_only", label: __("Overdue Only"), fieldtype: "Check" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "days_overdue" && data && data.days_overdue > 0) value = `<span class="text-danger">${value}</span>`;
		return value;
	},
};
