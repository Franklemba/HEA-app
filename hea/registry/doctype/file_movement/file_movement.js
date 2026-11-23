frappe.ui.form.on("File Movement", {
	refresh(frm) {
		if (frm.doc.colour) {
			frm.set_intro(`<span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:${frappe.utils.escape_html(frm.doc.colour)}"></span> `
				+ __("{0} label", [frappe.utils.escape_html(frm.doc.urgency || "")]));
		}
		frm.add_custom_button(__("Open File"), () => frappe.set_route("Form", "Registry File", frm.doc.registry_file));
	},
});
