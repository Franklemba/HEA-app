frappe.treeview_settings["File Subject"] = {
	get_tree_nodes: "hea.registry.doctype.file_subject.file_subject.get_children",
	add_tree_node: "hea.registry.doctype.file_subject.file_subject.add_node",
	get_tree_root: true,
	root_label: "File Subject",
	ignore_fields: ["parent_file_subject"],
	breadcrumb: "Registry",
	fields: [
		{ fieldtype: "Data", fieldname: "subject_name", label: __("Subject Name"), reqd: 1 },
		{
			fieldtype: "Select",
			fieldname: "subject_type",
			label: __("Subject Type"),
			options: "Portfolio\nDomestic",
			default: "Domestic",
			reqd: 1,
		},
		{
			fieldtype: "Data",
			fieldname: "subject_code",
			label: __("Subject Code"),
			description: __("Leave empty for a domestic subject to get the next code."),
		},
		{ fieldtype: "Check", fieldname: "is_group", label: __("Group Node") },
	],
	onload: function (treeview) {
		treeview.make_tree();
	},
};
