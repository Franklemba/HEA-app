const REGISTRY_ROLES = ["Documentation and Registry Officer", "Registry Staff", "System Manager"];
const DRIVE_URL_PREFIX = "/api/method/drive.api.files.get_file_content?entity_name=";

frappe.ui.form.on("Correspondence", {
	setup(frm) {
		frm.set_query("registry_file", () => ({ filters: { status: "Open" } }));
		frm.set_query("mode_of_delivery", () => ({ filters: { disabled: 0 } }));
		frm.set_query("dispatch_mode", () => ({ filters: { disabled: 0 } }));
		frm.set_query("assigned_officer", () => officer_query(frm));
	},

	before_workflow_action(frm) {
		const ask = ACTION_PROMPTS[frm.selected_workflow_action];
		if (!ask) return;
		// Frappe freezes the screen before this runs; lift it so the dialog can be used.
		frappe.dom.unfreeze();
		return new Promise((resolve, reject) => {
			let sent = false;
			const d = new frappe.ui.Dialog({
				title: __(frm.selected_workflow_action),
				fields: ask.fields(frm),
				primary_action_label: __(frm.selected_workflow_action),
				primary_action(values) {
					sent = true;
					d.hide();
					frappe.dom.freeze();
					frm.call("prepare_action", { action: frm.selected_workflow_action, values })
						.then(() => resolve())
						.catch((e) => { frappe.dom.unfreeze(); reject(e); });
				},
			});
			d.onhide = () => { if (!sent) reject(); };
			d.show();
		});
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
		const finished = ["Approved", "Filed", "Closed"].includes(frm.doc.workflow_state);
		const is_head = frm.doc.department_head === frappe.session.user;
		if (frm.doc.direction !== "Outgoing" && !finished && (is_head || is_registry)) {
			frm.add_custom_button(__("Change Due Date"), () => change_due_date(frm));
		}
		show_routing_intro(frm, finished);
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

const ACTION_PROMPTS = {
	"Assign to Officer": {
		fields: (frm) => [
			{ fieldname: "assigned_officer", fieldtype: "Link", options: "User", label: __("Action Officer"), reqd: 1,
				default: frm.doc.assigned_officer, get_query: () => officer_query(frm) },
			{ fieldname: "due_date", fieldtype: "Date", label: __("Due Date"), default: frm.doc.due_date },
		],
	},
	"Record Action": {
		fields: (frm) => [
			{ fieldname: "action_taken", fieldtype: "Small Text", label: __("Action Taken"), reqd: 1,
				default: frm.doc.action_taken },
		],
	},
	"Send Back": {
		fields: () => [
			{ fieldname: "reason", fieldtype: "Small Text", label: __("What needs to be done"), reqd: 1 },
		],
	},
};

function officer_query(frm) {
	return {
		query: "hea.registry.doctype.correspondence.correspondence.officer_query",
		filters: { department: frm.doc.department },
	};
}

function change_due_date(frm) {
	frappe.prompt(
		[
			{ fieldname: "due_date", fieldtype: "Date", label: __("New Due Date"), reqd: 1, default: frm.doc.due_date },
			{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason") },
		],
		(values) => frm.call("change_due_date", values).then(() => frm.reload_doc()),
		__("Change Due Date"),
		__("Save")
	);
}

function show_routing_intro(frm, finished) {
	if (frm.doc.workflow_state === "Assigned to Officer" && frm.doc.send_back_reason) {
		frm.set_intro(__("Sent back: {0}", [frappe.utils.escape_html(frm.doc.send_back_reason)]), "orange");
	} else if (!finished && frm.doc.due_date && frm.doc.due_date < frappe.datetime.get_today()) {
		frm.set_intro(__("Overdue since {0}.", [frappe.datetime.str_to_user(frm.doc.due_date)]), "red");
	}
}
