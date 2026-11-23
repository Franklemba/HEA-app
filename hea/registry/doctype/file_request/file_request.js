const REGISTRY_ROLES = ["Documentation and Registry Officer", "Registry Staff", "System Manager"];

frappe.ui.form.on("File Request", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Requested") return;
		const is_registry = REGISTRY_ROLES.some((r) => frappe.user.has_role(r));
		if (is_registry) {
			frm.add_custom_button(__("Issue File"), () =>
				frappe.prompt(
					[
						{ fieldname: "due_back", fieldtype: "Date", label: __("Due Back"),
							description: __("Leave empty for the usual number of days in Registry Settings.") },
						{ fieldname: "urgency", fieldtype: "Link", options: "Correspondence Urgency", label: __("Urgency (colour label)") },
						{ fieldname: "remarks", fieldtype: "Small Text", label: __("Remarks") },
					],
					(values) => frm.call("issue_file", values).then(() => frm.reload_doc()),
					__("Issue File"), __("Issue")
				)).addClass("btn-primary");
			frm.add_custom_button(__("Refuse"), () =>
				frappe.prompt([{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }],
					(values) => frm.call("refuse", values).then(() => frm.reload_doc()), __("Refuse Request"), __("Refuse")));
		}
		if (is_registry || frm.doc.requested_by === frappe.session.user) {
			frm.add_custom_button(__("Cancel Request"), () => frm.call("cancel_request").then(() => frm.reload_doc()));
		}
	},
});
