"""Port the REA Disciplinary app (Paul1st/Disciplinary) into the hea app's HEA Disciplinary module.

Usage: python3 -I port_rea_to_hea.py <rea_repo_root> <hea_app_root>
Re-runnable: overwrites the generated doctype folders and fixture files.

Offence data is HEA's own (tools/hea_offence_schedule.py), so this script no longer writes the offence
fixtures. It still overwrites the doctype JSON, including HEA changes such as Offence Sanction Matrix's
sanction_level field: diff before committing anything it regenerates.
"""
import ast
import json
import re
import shutil
import sys
from pathlib import Path

SRC = Path(sys.argv[1]) / "rea_disciplinary"
DST = Path(sys.argv[2]) / "hea"
MODULE = "HEA Disciplinary"
MODULE_DIR = DST / "hea_disciplinary"

# ---- tailoring rules (order matters) --------------------------------------
TEXT_RULES = [
	# spelling fix
	("Hearing Commitee", "Hearing Committee"),
	("hearing_commitee", "hearing_committee"),
	("HearingCommitee", "HearingCommittee"),
	# roles
	("Chief Executive Officer", "Director General"),
	("Pending CEO Approval", "Pending DG Approval"),
	(re.compile(r"\bCEO\b"), "Director General"),
	("Director HRA", "Manager HR"),
	(re.compile(r"\bManager HRA+\b"), "Manager HR"),
	("HRO Welfare", "HR Officer"),
	("HRO Employment", "HR Officer"),
	(re.compile(r"\bHRO\b"), "HR Officer"),
	# grades: REA n -> HEA0n
	(re.compile(r"\bREA ?(10|[1-9])\b"), lambda m: f"HEA{int(m.group(1)):02d}"),
	# branding
	("Rural Electrification Authority", "Higher Education Authority"),
	("rea.org.zm", "hea.org.zm"),
	("REA Disciplinary", MODULE),
	("rea-logo", "hea-logo"),
	(re.compile(r"\bREA\b"), "HEA"),
]
# REA has 10 grades, HEA has 9: drop band-table entries keyed on the non-existent HEA10
HEA10_ENTRY = re.compile(r'\\*"HEA10\\*"\s*:\s*\\*"HEA\d\d\\*"\s*,?\s*')

EXCLUDED_DOCTYPES = {"Forced Leave"}  # HEA already has its own "Forced leave"
# the case's "Trigger Forced Leave" button: target HEA's Forced leave and its real fields
FORCED_LEAVE_RULES = [
	(re.compile(r"doctype:(\s*)'Forced Leave'"), r"doctype:\1'Forced leave'"),
	(re.compile(r"from_date:(\s*)values\.from_date"), r"start_date:\1values.from_date"),
	(re.compile(r"to_date:(\s*)values\.to_date"), r"end_date:\1values.to_date"),
	(
		re.compile(r"disciplinary_case:(\s*)frm\.doc\.name"),
		r"disciplinary_case_no:\1frm.doc.name,\n                    leave_type:\1'Forced Leave'",
	),
]
# fixes to REA scripts: {script name: [(old, new)]}
SERVER_SCRIPT_PATCHES = {
	# a new case has no workflow_state until the workflow sets it; treat it as Draft so API/script inserts work
	"Require charge before leaving Charge stage": [
		('if doc.workflow_state not in ("Draft", "Charge")', 'if (doc.workflow_state or "Draft") not in ("Draft", "Charge")'),
	],
}
# HR Settings fields read by "Disciplinary Case Closure" (were on the REA site but not in its export)
HR_SETTINGS_FIELDS = [
	{
		"fieldname": "custom_disciplinary_section",
		"label": "Disciplinary",
		"fieldtype": "Section Break",
		"insert_after": "unlink_payment_on_cancellation_of_employee_advance",
	},
	{
		"fieldname": "custom_verbal_warning_validity_months",
		"label": "Verbal Warning Validity (Months)",
		"fieldtype": "Int",
		"default": "6",
		"insert_after": "custom_disciplinary_section",
	},
	{
		"fieldname": "custom_written_warning_validity_months",
		"label": "Written Warning Validity (Months)",
		"fieldtype": "Int",
		"default": "12",
		"insert_after": "custom_verbal_warning_validity_months",
	},
]
FORCED_LEAVE_CASE_FIELD = {
	"doctype": "Custom Field",
	"name": "Forced leave-disciplinary_case_no",
	"dt": "Forced leave",
	"module": MODULE,
	"fieldname": "disciplinary_case_no",
	"label": "Disciplinary Case No",
	"fieldtype": "Link",
	"options": "Disciplinary",
	"insert_after": "reason",
	"read_only": 1,
	"search_index": 1,
}
EXCLUDED_CUSTOM_FIELDS = {"Forced Leave-workflow_state", "Disciplinary Action-workflow_state"}
DUPLICATE_NOTIFICATION_PREFIX = "Disciplinary — "  # duplicates the "DISC – … – Email" set


DEBUG_TITLE = re.compile(r"^DEBUG Script(?: \d+)? — ")


def strip_debug_logging(script):
	"""Drop REA's frappe.log_error("DEBUG …") trace calls; keep the failure logs under a plain title."""
	lines = script.splitlines(keepends=True)
	for node in sorted(ast.walk(ast.parse(script)), key=lambda n: -getattr(n, "lineno", 0)):
		if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
			continue
		call = node.value
		if ast.unparse(call.func) != "frappe.log_error":
			continue
		title = next((k.value.value for k in call.keywords if k.arg == "title" and isinstance(k.value, ast.Constant)), "")
		if DEBUG_TITLE.match(title) and "Failure" not in title:
			indent = re.match(r"\s*", lines[node.lineno - 1]).group()
			eol = "\r\n" if lines[node.end_lineno - 1].endswith("\r\n") else "\n"
			lines[node.lineno - 1 : node.end_lineno] = [f"{indent}pass{eol}"]
	return re.sub(r'title="DEBUG Script(?: \d+)? — ', 'title="Disciplinary — ', "".join(lines))


def tailor(text):
	for old, new in TEXT_RULES:
		text = old.sub(new, text) if isinstance(old, re.Pattern) else text.replace(old, new)
	return HEA10_ENTRY.sub("", text)


def load(name):
	return json.loads(tailor((SRC / "fixtures" / f"{name}.json").read_text()))


def dump(path, data):
	path.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n")


def port_doctypes():
	src_root = SRC / "rea_disciplinary" / "doctype"
	dst_root = MODULE_DIR / "doctype"
	names = []
	for folder in sorted(p for p in src_root.iterdir() if p.is_dir()):
		meta = json.loads(tailor((folder / f"{folder.name}.json").read_text()))
		if meta["name"] in EXCLUDED_DOCTYPES:
			continue
		new_folder_name = tailor(folder.name)
		out = dst_root / new_folder_name
		shutil.rmtree(out, ignore_errors=True)
		out.mkdir(parents=True)
		for f in folder.iterdir():
			if f.suffix not in (".py", ".js", ".json") or f.name.startswith("test_"):
				continue
			target = out / tailor(f.name)
			if f.suffix == ".json":
				meta["module"] = MODULE
				dump(target, meta)
			else:
				target.write_text(tailor(f.read_text()))
		names.append(meta["name"])
	return names


def is_disc_doctype(dt, ported):
	return dt in ported


def port_fixtures(ported):
	fx = DST / "fixtures"
	fx.mkdir(exist_ok=True)
	out = {}

	out["custom_field"] = [d for d in load("custom_field") if d["name"] not in EXCLUDED_CUSTOM_FIELDS]
	out["custom_field"].append(FORCED_LEAVE_CASE_FIELD)
	for f in HR_SETTINGS_FIELDS:
		out["custom_field"].append(
			{"doctype": "Custom Field", "name": f"HR Settings-{f['fieldname']}", "dt": "HR Settings", "module": MODULE, **f}
		)
	out["property_setter"] = [d for d in load("property_setter") if is_disc_doctype(d["doc_type"], ported)]

	# scripts and notifications that were switched off on REA never ran, so they are not carried over
	out["client_script"] = [
		d for d in load("client_script") if d["dt"] not in EXCLUDED_DOCTYPES and d.get("enabled")
	]
	out["server_script"] = [
		d
		for d in load("server_script")
		if d.get("reference_doctype") not in EXCLUDED_DOCTYPES and not d.get("disabled")
	]
	for key in ("client_script", "server_script"):
		for d in out[key]:
			d["module"] = MODULE
	for d in out["server_script"]:
		for old, new in SERVER_SCRIPT_PATCHES.get(d["name"], []):
			assert old in d["script"], (d["name"], old)
			d["script"] = d["script"].replace(old, new)
		d["script"] = strip_debug_logging(d["script"])
	for d in out["client_script"]:
		for old, new in FORCED_LEAVE_RULES:
			d["script"] = old.sub(new, d["script"])

	out["notification"] = [
		d
		for d in load("notification")
		if d.get("enabled") and not d["name"].startswith(DUPLICATE_NOTIFICATION_PREFIX)
	]

	# collapse permissions that became duplicates after role mapping; employees must not edit sanctions
	perms, seen = [], set()
	for d in load("custom_docperm"):
		if d["parent"] in EXCLUDED_DOCTYPES:
			continue
		if d["parent"] == "Offence Sanction Matrix" and d["role"] == "Employee":
			d["write"] = 0
		key = (d["parent"], d["role"], d["permlevel"])
		if key in seen:
			continue
		seen.add(key)
		perms.append(d)
	out["custom_docperm"] = perms

	workflows = [w for w in load("workflow") if w["document_type"] not in EXCLUDED_DOCTYPES]
	for w in workflows:
		uniq, seen = [], set()
		for t in w["transitions"]:
			key = (t["state"], t["action"], t["next_state"], t["allowed"])
			if key not in seen:
				seen.add(key)
				uniq.append(t)
		w["transitions"] = uniq
	out["workflow"] = workflows
	used_states = {s["state"] for w in workflows for s in w["states"]}
	used_actions = {t["action"] for w in workflows for t in w["transitions"]}
	out["workflow_state"] = [d for d in load("workflow_state") if d["name"] in used_states]
	out["workflow_action_master"] = [d for d in load("workflow_action_master") if d["name"] in used_actions]

	for key in ("report", "print_format", "dashboard_chart", "number_card"):
		docs = load(key)
		for d in docs:
			if "module" in d:
				d["module"] = MODULE
		out[key] = docs

	hea_owned = {"offence_category.json", "offence_master.json", "offence_sanction_matrix.json"}
	for old in fx.glob("*.json"):
		if old.name not in hea_owned:
			old.unlink()
	for key, docs in out.items():
		dump(fx / f"{key}.json", docs)
	return out


def hooks_fixtures(out):
	by_name = [
		("Custom Field", "custom_field"),
		("Property Setter", "property_setter"),
		("Client Script", "client_script"),
		("Server Script", "server_script"),
		("Print Format", "print_format"),
		("Report", "report"),
		("Notification", "notification"),
		("Custom DocPerm", "custom_docperm"),
		("Workflow", "workflow"),
		("Workflow State", "workflow_state"),
		("Workflow Action Master", "workflow_action_master"),
		("Number Card", "number_card"),
		("Dashboard Chart", "dashboard_chart"),
	]
	lines = ["fixtures = ["]
	for dt, key in by_name:
		names = sorted(d["name"] for d in out[key])
		lines.append("\t{")
		lines.append(f'\t\t"dt": "{dt}",')
		lines.append(f'\t\t"filters": [["name", "in", {json.dumps(names, ensure_ascii=False)}]],')
		lines.append("\t},")
	lines += ['\t"Offence Category",', '\t"Offence Master",', '\t"Offence Sanction Matrix",', "]"]
	return "\n".join(lines)


if __name__ == "__main__":
	ported = port_doctypes()
	out = port_fixtures(ported)
	(Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/dev/stdout")).write_text(hooks_fixtures(out) + "\n")
	print("ported doctypes:", ported, file=sys.stderr)
	print({k: len(v) for k, v in out.items()}, file=sys.stderr)
