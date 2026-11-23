const REGISTRY_ROLES = ["Documentation and Registry Officer", "Registry Staff", "System Manager"];
const PAPER = __("Paper File");

frappe.ui.form.on("Registry File", {
	setup(frm) {
		frm.set_query("file_subject", () => ({ filters: { is_group: 0, disabled: 0 } }));
	},

	refresh(frm) {
		if (frm.is_new()) {
			frm.set_intro(__("The file number is given when you save, as the next number under the subject."));
			return;
		}
		if (frm.doc.drive_folder) {
			frm.add_custom_button(__("Drive Folder"), () => window.open(`/drive/folder/${frm.doc.drive_folder}`));
		}
		const is_registry = REGISTRY_ROLES.some((r) => frappe.user.has_role(r));
		const is_holder = frm.doc.holder === frappe.session.user;
		paper_file_buttons(frm, is_registry, is_holder);
		show_whereabouts(frm);
		render_history(frm);
		if (!is_registry) return;
		if (frm.doc.status === "Open") {
			frm.add_custom_button(__("Register Correspondence"), () =>
				frappe.new_doc("Correspondence", { registry_file: frm.doc.name }));
		}

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

function paper_file_buttons(frm, is_registry, is_holder) {
	const out = !!frm.doc.current_movement;
	const issue_fields = (label) => [
		{ fieldname: "to_user", fieldtype: "Link", options: "User", label: label, reqd: 1,
			get_query: () => ({ filters: { enabled: 1, user_type: "System User" } }) },
		{ fieldname: "due_back", fieldtype: "Date", label: __("Due Back"),
			description: __("Leave empty for the usual number of days in Registry Settings.") },
		{ fieldname: "urgency", fieldtype: "Link", options: "Correspondence Urgency", label: __("Urgency (colour label)") },
		{ fieldname: "correspondence", fieldtype: "Link", options: "Correspondence", label: __("For Correspondence"),
			get_query: () => ({ filters: { registry_file: frm.doc.name } }) },
		{ fieldname: "remarks", fieldtype: "Small Text", label: __("Remarks") },
	];
	if (is_registry && !out) {
		frm.add_custom_button(__("Issue"), () => act(frm, "issue_file", __("Issue File"), issue_fields(__("Issue To"))), PAPER);
	}
	if (is_registry && out) {
		frm.add_custom_button(__("Transfer"), () =>
			act(frm, "transfer_file", __("Transfer File"), issue_fields(__("Transfer To"))), PAPER);
		frm.add_custom_button(__("Record Return"), () =>
			act(frm, "return_file", __("Record Return to Registry"), [{ fieldname: "remarks", fieldtype: "Small Text", label: __("Remarks") }]), PAPER);
		frm.add_custom_button(__("Extend Due Back"), () =>
			act(frm, "extend_due_back", __("Extend Due Back"), [
				{ fieldname: "due_back", fieldtype: "Date", label: __("New Due Back"), reqd: 1, default: frm.doc.due_back },
				{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason") },
			]), PAPER);
	}
	if (is_holder && out && !frm.doc.put_away_requested) {
		frm.add_custom_button(__("Mark Put Away (PA)"), () =>
			act(frm, "mark_put_away", __("Mark Put Away"), [{ fieldname: "note", fieldtype: "Small Text", label: __("Note") }]), PAPER);
	}
	if (is_registry || is_holder) {
		frm.add_custom_button(__("Bring Up (BU)"), () =>
			act(frm, "set_bring_up", __("Bring Up"), [
				{ fieldname: "bring_up_date", fieldtype: "Date", label: __("Bring Up Date"), default: frm.doc.bring_up_date,
					description: __("Leave empty to clear the Bring Up.") },
				{ fieldname: "note", fieldtype: "Small Text", label: __("What to do with the file") },
			]), PAPER);
	}
	if (!is_holder) {
		frm.add_custom_button(__("Request File"), () => frappe.new_doc("File Request", { registry_file: frm.doc.name }), PAPER);
	}
}

function act(frm, method, title, fields) {
	frappe.prompt(fields, (values) => frm.call(method, values).then(() => frm.reload_doc()), title, title);
}

function show_whereabouts(frm) {
	if (frm.doc.status === "Closed") return;
	if (frm.doc.is_overdue) {
		frm.set_intro(__("Overdue: due back in Registry on {0}.", [frappe.datetime.str_to_user(frm.doc.due_back)]), "red");
	} else if (frm.doc.put_away_requested) {
		frm.set_intro(__("Marked Put Away; waiting for Registry to collect it."), "blue");
	}
}

function render_history(frm) {
	const wrapper = frm.get_field("movement_history").$wrapper;
	frappe.call("hea.registry.movement.movement_history", { registry_file: frm.doc.name }).then(({ message: rows }) => {
		if (!rows || !rows.length) {
			wrapper.html(`<p class="text-muted">${__("This file has not left Registry.")}</p>`);
			return;
		}
		const esc = frappe.utils.escape_html;
		const when = (d) => (d ? frappe.datetime.str_to_user(d) : "");
		const body = rows.map((r) => `<tr>
			<td>${r.colour ? `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${esc(r.colour)}" title="${esc(r.urgency || "")}"></span> ` : ""}
				<a href="/app/file-movement/${encodeURIComponent(r.name)}">${esc(r.name)}</a></td>
			<td>${esc(r.issued_to_name)}</td><td>${when(r.issued_on)}</td><td>${esc(r.issued_by_name)}</td>
			<td>${when(r.due_back)}${r.is_overdue ? ` <span class="text-danger">${__("overdue")}</span>` : ""}</td>
			<td>${__(r.status)}</td><td>${when(r.returned_on)}</td><td>${esc(r.received_by_name)}</td></tr>`).join("");
		wrapper.html(`<table class="table table-bordered table-sm"><thead><tr>
			<th>${__("Movement")}</th><th>${__("To")}</th><th>${__("Out")}</th><th>${__("Issued By")}</th>
			<th>${__("Due Back")}</th><th>${__("Status")}</th><th>${__("Back")}</th><th>${__("Received By")}</th>
			</tr></thead><tbody>${body}</tbody></table>`);
	});
}

function ask_reason(frm, method, title) {
	frappe.prompt(
		[{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: method === "reopen_file" }],
		(values) => frm.call(method, { reason: values.reason }).then(() => frm.reload_doc()),
		title,
		title
	);
}
