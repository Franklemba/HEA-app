"""Phase 3 setup: the Correspondence workflow, its notifications, and the Registry charts and cards.

Each record is created once, the way the desk creates it, and is then HEA's to edit in the desk:
re-running migrate never overwrites it.
"""

import json

import frappe

WORKFLOW = "Correspondence Routing"
REGISTRY = ("Registry Staff", "Documentation and Registry Officer")
HEADS = ("Departmental Head",)
OFFICERS = ("General Staff", "Departmental Head", "Registry Staff", "Management and Authorised Auditors")
IS_HEAD = "doc.department_head == frappe.session.user"
IS_OFFICER = "doc.assigned_officer == frappe.session.user"

STATES = (  # state, style
	("Registered", "Primary"),
	("Assigned to Department", "Info"),
	("Assigned to Officer", "Info"),
	("Action Taken", "Warning"),
	("Under Review", "Warning"),
	("Approved", "Success"),
	("Filed", "Success"),
	("Closed", "Inverse"),
)

TRANSITIONS = (  # from, action, to, roles, condition
	("Registered", "Assign to Department", "Assigned to Department", REGISTRY, "doc.direction != 'Outgoing'"),
	("Registered", "File", "Filed", REGISTRY, "doc.direction == 'Outgoing'"),
	("Assigned to Department", "Assign to Officer", "Assigned to Officer", HEADS, IS_HEAD),
	("Assigned to Officer", "Record Action", "Action Taken", OFFICERS, IS_OFFICER),
	("Action Taken", "Start Review", "Under Review", HEADS, IS_HEAD),
	("Under Review", "Approve", "Approved", HEADS, IS_HEAD),
	("Under Review", "Send Back", "Assigned to Officer", HEADS, IS_HEAD),
	("Approved", "File", "Filed", REGISTRY, None),
	("Filed", "Close", "Closed", REGISTRY, None),
)

NOTIFICATIONS = (
	{
		"name": "Correspondence Reached You",
		"event": "Value Change", "value_changed": "current_holder",
		"condition": "doc.current_holder",
		"recipients": [{"receiver_by_document_field": "current_holder"}],
		"subject": "{{ doc.workflow_state }}: {{ doc.subject }} ({{ doc.name }})",
		"message": """<p>{{ doc.name }} <b>{{ doc.subject }}</b> is now with you ({{ doc.workflow_state }}).</p>
{% if doc.workflow_state == "Assigned to Officer" and doc.send_back_reason %}<p>It was sent back: {{ doc.send_back_reason }}</p>{% endif %}
{% if doc.due_date %}<p>Due: {{ frappe.format(doc.due_date, {"fieldtype": "Date"}) }}</p>{% endif %}
<p><a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">Open the item</a></p>""",
	},
	{
		"name": "Correspondence Ready for Filing",
		"event": "Value Change", "value_changed": "workflow_state",
		"condition": 'doc.workflow_state == "Approved"',
		"recipients": [{"receiver_by_role": "Registry Staff"}],
		"subject": "Ready for filing: {{ doc.subject }} ({{ doc.name }})",
		"message": """<p>{{ doc.name }} <b>{{ doc.subject }}</b> was approved and can be filed{% if doc.registry_file %} on {{ doc.registry_file }}{% endif %}.</p>
<p><a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">Open the item</a></p>""",
	},
	{
		"name": "Correspondence Due Soon",
		"event": "Days Before", "date_changed": "due_date", "days_in_advance": 1,
		"condition": 'doc.current_holder and doc.workflow_state not in ("Approved", "Filed", "Closed")',
		"recipients": [{"receiver_by_document_field": "current_holder"}],
		"subject": "Due tomorrow: {{ doc.subject }} ({{ doc.name }})",
		"message": """<p>{{ doc.name }} <b>{{ doc.subject }}</b> ({{ doc.workflow_state }}) is due on {{ frappe.format(doc.due_date, {"fieldtype": "Date"}) }}.</p>
<p><a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">Open the item</a></p>""",
	},
)

PENDING = [["Correspondence", "workflow_state", "not in", ["Approved", "Filed", "Closed"]],
	["Correspondence", "direction", "!=", "Outgoing"]]

CHARTS = (
	("Pending Correspondence by Department", "department", PENDING),
	("Pending Correspondence by Officer", "assigned_officer", PENDING),
	("Correspondence by Stage", "workflow_state", [["Correspondence", "direction", "!=", "Outgoing"]]),
)

CARDS = (
	("Pending Correspondence", PENDING, []),
	("Overdue Correspondence", PENDING, [["Correspondence", "due_date", "<", "frappe.datetime.get_today()"]]),
)


def ready():
	return frappe.db.exists("DocType", "Correspondence") and frappe.get_meta("Correspondence").has_field("workflow_state")


def ensure_workflow():
	if not ready() or frappe.db.exists("Workflow", WORKFLOW):
		return
	for state, style in STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(
				ignore_permissions=True)
	for action in {t[1] for t in TRANSITIONS}:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
				ignore_permissions=True)
	wf = frappe.get_doc({
		"doctype": "Workflow",
		"workflow_name": WORKFLOW,
		"document_type": "Correspondence",
		"workflow_state_field": "workflow_state",
		"is_active": 1,
		"send_email_alert": 0,  # the Notifications below tell the right person instead
		"override_status": 1,
	})
	for state, _style in STATES:
		for role in REGISTRY:  # heads and officers act through the stage actions, not by editing the form
			wf.append("states", {"state": state, "doc_status": "0", "allow_edit": role})
	for state, action, next_state, roles, condition in TRANSITIONS:
		for role in roles:
			wf.append("transitions", {"state": state, "action": action, "next_state": next_state, "allowed": role,
				"allow_self_approval": 1, "condition": condition})
	wf.insert(ignore_permissions=True)


def ensure_notifications():
	if not ready():
		return
	for n in NOTIFICATIONS:
		if frappe.db.exists("Notification", n["name"]):
			continue
		doc = frappe.new_doc("Notification")
		# In-system notifications; each one is also emailed to the user (their Notification Settings) once
		# an outgoing Email Account exists. An Email channel would fail outright until then.
		doc.update({**n, "document_type": "Correspondence", "channel": "System Notification",
			"enabled": 1, "message_type": "HTML"})
		doc.name = n["name"]
		doc.insert(ignore_permissions=True, set_name=n["name"])


def ensure_charts():
	if not ready():
		return
	for name, field, filters in CHARTS:
		if frappe.db.exists("Dashboard Chart", name):
			continue
		frappe.get_doc({
			"doctype": "Dashboard Chart", "chart_name": name, "chart_type": "Group By", "document_type": "Correspondence",
			"group_by_type": "Count", "group_by_based_on": field, "number_of_groups": 10, "type": "Bar",
			"filters_json": json.dumps(filters), "is_public": 1, "timeseries": 0, "module": "Registry",
		}).insert(ignore_permissions=True)
	for label, filters, dynamic in CARDS:
		if frappe.db.exists("Number Card", label):
			continue
		frappe.get_doc({
			"doctype": "Number Card", "label": label, "type": "Document Type", "document_type": "Correspondence",
			"function": "Count", "filters_json": json.dumps(filters), "dynamic_filters_json": json.dumps(dynamic),
			"is_public": 1, "show_percentage_stats": 0, "module": "Registry",
		}).insert(ignore_permissions=True)


def setup_routing():
	ensure_workflow()
	ensure_notifications()
	ensure_charts()
