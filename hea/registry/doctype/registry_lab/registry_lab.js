// The Registry Test Lab screen: set up lab users and files, move the lab clock, reset.
const LAB = "hea.registry.lab";

frappe.ui.form.on("Registry Lab", {
	refresh(frm) {
		frm.disable_save();
		frm.get_field("intro").$wrapper.html(`
			<div class="text-muted" style="max-width:780px">
				<p>${__("The lab adds eight sample users (one per registry role, ending in @hea-lab.test) and a lab subject with four lab files. Real files and correspondence are never touched.")}</p>
				<p>${__("To act as a lab user: log in as Administrator, open the user (Settings → User), and choose <b>Impersonate</b>. Log out to come back as Administrator.")}</p>
			</div>`);
		load_status(frm);
		frm.add_custom_button(__("Set Up Lab"), () => run(frm, "setup_lab", {}, __("Lab is ready")));
		frm.add_custom_button(__("Fast-Forward and Run Morning Jobs"), () =>
			run(frm, "fast_forward", { days: frm.doc.days || 0 }, __("Morning jobs run")).then((r) => {
				if (!r) return;
				const lines = [
					__("Correspondence escalated: {0}", [(r.escalated || []).join(", ") || __("none")]),
					__("Paper files flagged overdue: {0}", [(r.overdue_files || []).join(", ") || __("none")]),
					__("Reminders sent: {0}", [(r.reminders || []).join(", ") || __("none")]),
				];
				frm.set_value("last_run", `${frappe.datetime.now_datetime()} (+${frm.doc.days || 0} days)\n${lines.join("\n")}`);
				frappe.msgprint(lines.join("<br>"), __("Morning jobs"));
			}));
		frm.add_custom_button(__("Reset Lab Data"), () =>
			frappe.confirm(__("Delete all lab correspondence, file movements, requests, scans and logs, and start again with fresh lab files? Lab users stay."),
				() => run(frm, "reset_lab", { remove_users: 0 }, __("Lab data reset")).then(() => run(frm, "setup_lab", {}, __("Lab is ready")))), __("Reset"));
		frm.add_custom_button(__("Remove Lab Completely"), () =>
			frappe.confirm(__("Remove everything the lab made, including the lab users and their Registry Settings rows?"),
				() => run(frm, "reset_lab", { remove_users: 1 }, __("Lab removed"))), __("Reset"));
	},
});

function run(frm, method, args, done) {
	return frappe.xcall(`${LAB}.${method}`, args, { freeze: true }).then((r) => {
		frappe.show_alert({ message: done, indicator: "green" });
		load_status(frm);
		return r;
	});
}

function load_status(frm) {
	frappe.xcall(`${LAB}.status`).then((s) => {
		const esc = frappe.utils.escape_html;
		if (!s.ready) {
			frm.get_field("lab_status").$wrapper.html(`<p>${__("The lab is not set up. Click <b>Set Up Lab</b>.")}</p>`);
			return;
		}
		const users = s.users.map((u) => `<tr><td><a href="/app/user/${encodeURIComponent(u.user)}">${esc(u.user)}</a></td><td>${esc(u.name || "")}</td><td>${esc(u.role)}</td></tr>`).join("");
		const files = s.files.map((f) => `<tr><td><a href="/app/registry-file/${encodeURIComponent(f.name)}">${esc(f.name)}</a></td><td>${esc(f.title)}</td></tr>`).join("");
		frm.get_field("lab_status").$wrapper.html(`
			<p><b>${__("Lab users")}</b> ${__("(open one and choose Impersonate)")}</p>
			<table class="table table-bordered table-sm"><thead><tr><th>${__("User")}</th><th>${__("Name")}</th><th>${__("Role")}</th></tr></thead><tbody>${users}</tbody></table>
			<p><b>${__("Lab files")}</b> ${__("under subject")} ${esc(s.subject || "")}</p>
			<table class="table table-bordered table-sm"><tbody>${files}</tbody></table>
			<p class="text-muted">${__("{0} lab correspondence items, {1} file movements so far.", [s.correspondence, s.movements])}</p>`);
	});
}
