const REGISTRY_ROLES = ["Documentation and Registry Officer", "Registry Staff", "System Manager"];
const DRIVE_URL_PREFIX = "/api/method/drive.api.files.get_file_content?entity_name=";

frappe.ui.form.on("Correspondence", {
	setup(frm) {
		frm.set_query("registry_file", () => ({ filters: { status: "Open" } }));
		frm.set_query("mode_of_delivery", () => ({ filters: { disabled: 0 } }));
		frm.set_query("dispatch_mode", () => ({ filters: { disabled: 0 } }));
	},

	refresh(frm) {
		if (frm.is_new()) {
			frm.set_intro(__("The reference number and folio are given when you save."));
			return;
		}
		if (frm.doc.drive_file) {
			frm.add_custom_button(__("Open in Drive"), () => window.open(`/drive/f/${frm.doc.drive_file}`), __("Scan"));
			frm.add_custom_button(__("Download"), () => window.open(DRIVE_URL_PREFIX + frm.doc.drive_file + "&trigger_download=1"), __("Scan"));
		}
		const is_registry = REGISTRY_ROLES.some((r) => frappe.user.has_role(r));
		if (is_registry && frm.doc.direction === "Outgoing" && !frm.doc.dispatched_on) {
			frm.add_custom_button(__("Record Dispatch"), () => record_dispatch(frm));
		}
	},

	folio_placement(frm) {
		if (frm.doc.folio_placement === "Next Folio") frm.set_value("folio_reference", null);
	},
});

function record_dispatch(frm) {
	frappe.prompt(
		[
			{ fieldname: "dispatch_mode", fieldtype: "Link", options: "Delivery Mode", label: __("Means of Dispatch"),
				reqd: 1, default: frm.doc.dispatch_mode, get_query: () => ({ filters: { disabled: 0 } }) },
			{ fieldname: "received_by", fieldtype: "Data", label: __("Received By"), default: frm.doc.received_by },
			{ fieldname: "copies_sent_to", fieldtype: "Small Text", label: __("Copies Sent To"), default: frm.doc.copies_sent_to },
		],
		(values) => frm.call("record_dispatch", values).then(() => frm.reload_doc()),
		__("Record Dispatch"),
		__("Save")
	);
}
