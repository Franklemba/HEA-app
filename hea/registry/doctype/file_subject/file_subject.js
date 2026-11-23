frappe.ui.form.on("File Subject", {
	refresh(frm) {
		frm.set_query("parent_file_subject", () => ({ filters: { is_group: 1 } }));
		if (!frm.is_new() && !frm.doc.is_group && frm.doc.subject_code) {
			frm.add_custom_button(__("Open a File"), () => {
				frappe.new_doc("Registry File", { file_subject: frm.doc.name });
			});
			frm.add_custom_button(__("Files"), () => {
				frappe.set_route("List", "Registry File", { file_subject: frm.doc.name });
			});
		}
	},
});
