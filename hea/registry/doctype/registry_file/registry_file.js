const REGISTRY_ROLES = ["Documentation and Registry Officer", "Registry Staff", "System Manager"];

frappe.ui.form.on("Registry File", {
	setup(frm) {
		frm.set_query("file_subject", () => ({ filters: { is_group: 0, disabled: 0 } }));
	},

	refresh(frm) {
		if (frm.is_new()) {
			frm.set_intro(__("The file number is given when you save, as the next number under the subject."));
			return;
		}
		const is_registry = REGISTRY_ROLES.some((r) => frappe.user.has_role(r));
		if (!is_registry) return;

		if (frm.doc.status === "Open") {
			frm.add_custom_button(__("Close File"), () => ask_reason(frm, "close_file", __("Close File")));
		} else {
			frm.add_custom_button(__("Reopen File"), () => ask_reason(frm, "reopen_file", __("Reopen File")));
		}
		if (frm.doc.status === "Closed") {
			frm.set_intro(__("This file was closed on {0}.", [frappe.datetime.str_to_user(frm.doc.closed_on)]), "orange");
		}
	},
});

function ask_reason(frm, method, title) {
	frappe.prompt(
		[{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: method === "reopen_file" }],
		(values) => frm.call(method, { reason: values.reason }).then(() => frm.reload_doc()),
		title,
		title
	);
}
