// Records control on every Registry record form: deletion with a reason (Officer only), and corrections of
// declared correspondence.
const REGISTRY_RECORD_DOCTYPES = ["Correspondence", "Registry File", "File Subject", "File Movement", "File Request"];

REGISTRY_RECORD_DOCTYPES.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			if (frm.is_new()) return;
			if (frappe.user.has_role("Documentation and Registry Officer")) {
				frm.page.add_menu_item(__("Delete with Reason"), () => delete_with_reason(frm));
			}
			if (doctype === "Correspondence" && frm.doc.docstatus === 1) {
				frm.set_intro(__("This is a declared record and cannot be changed. Register a correction that refers to it."), "blue");
				if (frappe.user.has_role("Registry Staff") || frappe.user.has_role("Documentation and Registry Officer")) {
					frm.add_custom_button(__("Register Correction"), () =>
						frappe.xcall("hea.registry.records.correction_defaults", { name: frm.doc.name })
							.then((values) => frappe.new_doc("Correspondence", values)));
				}
			}
		},
	});
});

function delete_with_reason(frm) {
	frappe.prompt(
		[{ fieldname: "reason", fieldtype: "Small Text", label: __("Why is this being deleted?"), reqd: 1 }],
		(values) =>
			frappe.xcall("hea.registry.records.delete_record", { doctype: frm.doctype, name: frm.doc.name, reason: values.reason })
				.then((log) => {
					frappe.show_alert({ message: __("Deleted and logged as {0}", [log]), indicator: "green" });
					frappe.set_route("List", frm.doctype);
				}),
		__("Delete {0}", [frm.doc.name]),
		__("Delete")
	);
}
