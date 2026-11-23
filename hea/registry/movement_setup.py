"""Phase 4 setup: file movement notifications and urgency colour labels.

Created once, the way the desk creates them; HEA edits them in the desk afterwards.
"""

import frappe

# Notification templates can use frappe.db.get_value but not frappe.utils.get_fullname.
LINK = '<p><a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">Open</a></p>'
REGISTRY_ROLES = [{"receiver_by_role": "Registry Staff"}, {"receiver_by_role": "Documentation and Registry Officer"}]

NOTIFICATIONS = (
	{
		"name": "File Requested", "document_type": "File Request", "event": "New",
		"recipients": REGISTRY_ROLES,
		"subject": "File requested: {{ doc.registry_file }} by {{ frappe.db.get_value('User', doc.requested_by, 'full_name') }}",
		"message": "<p>{{ frappe.db.get_value('User', doc.requested_by, 'full_name') }} asks for file <b>{{ doc.registry_file }}</b> "
			"{{ doc.file_title }}{% if doc.needed_by %}, needed by {{ frappe.format(doc.needed_by, {'fieldtype': 'Date'}) }}{% endif %}.</p>"
			"<p>{{ doc.purpose }}</p>" + LINK,
	},
	{
		"name": "File Request Answered", "document_type": "File Request", "event": "Value Change",
		"value_changed": "status", "condition": 'doc.status in ("Issued", "Refused")',
		"recipients": [{"receiver_by_document_field": "requested_by"}],
		"subject": "File {{ doc.registry_file }}: request {{ doc.status|lower }}",
		"message": "<p>Your request for file <b>{{ doc.registry_file }}</b> was {{ doc.status|lower }}."
			"{% if doc.refusal_reason %} {{ doc.refusal_reason }}{% endif %}</p>" + LINK,
	},
	{
		"name": "File Issued to You", "document_type": "File Movement", "event": "New",
		"recipients": [{"receiver_by_document_field": "issued_to"}],
		"subject": "Paper file {{ doc.registry_file }} is now with you",
		"message": "<p>Registry has given you file <b>{{ doc.registry_file }}</b> {{ doc.file_title }}"
			"{% if doc.urgency %} ({{ doc.urgency }} label){% endif %}. Please return it by "
			"{{ frappe.format(doc.due_back, {'fieldtype': 'Date'}) }}, or pass it on through Registry.</p>" + LINK,
	},
	{
		"name": "File Marked Put Away", "document_type": "Registry File", "event": "Value Change",
		"value_changed": "put_away_requested", "condition": "doc.put_away_requested",
		"recipients": REGISTRY_ROLES,
		"subject": "Put Away: collect file {{ doc.name }} from {{ frappe.db.get_value('User', doc.put_away_by, 'full_name') }}",
		"message": "<p>{{ frappe.db.get_value('User', doc.put_away_by, 'full_name') }} has marked file <b>{{ doc.name }}</b> "
			"{{ doc.file_title }} Put Away (PA). Collect it and record its return.</p>" + LINK,
	},
	{
		"name": "File Bring Up", "document_type": "Registry File", "event": "Days Before",
		"date_changed": "bring_up_date", "days_in_advance": 0,
		"recipients": [{"receiver_by_document_field": "bring_up_by"}] + REGISTRY_ROLES,
		"subject": "Bring Up today: file {{ doc.name }} {{ doc.file_title }}",
		"message": "<p>File <b>{{ doc.name }}</b> {{ doc.file_title }} is brought up today"
			"{% if doc.bring_up_by %} for {{ frappe.db.get_value('User', doc.bring_up_by, 'full_name') }}{% endif %}.</p>"
			"{% if doc.bring_up_note %}<p>{{ doc.bring_up_note }}</p>{% endif %}"
			"<p>It is {{ doc.current_location }}.</p>" + LINK,
	},
)

# Assumed until HEA confirms its colour labels (Phase 0 walk-through).
URGENCY_COLOURS = {"Immediate": "#E03636", "Urgent": "#ECAD4B", "Routine": "#30A66D"}


def ensure_notifications():
	if not frappe.db.exists("DocType", "File Movement"):
		return
	for n in NOTIFICATIONS:
		if frappe.db.exists("Notification", n["name"]):
			continue
		doc = frappe.new_doc("Notification")
		doc.update({**n, "channel": "System Notification", "enabled": 1, "message_type": "HTML"})
		doc.insert(ignore_permissions=True, set_name=n["name"])


def ensure_urgency_colours():
	if not frappe.get_meta("Correspondence Urgency").has_field("colour"):
		return
	for urgency, colour in URGENCY_COLOURS.items():
		if frappe.db.exists("Correspondence Urgency", urgency) and not frappe.db.get_value("Correspondence Urgency", urgency, "colour"):
			frappe.db.set_value("Correspondence Urgency", urgency, "colour", colour)


def setup_movement():
	ensure_urgency_colours()
	ensure_notifications()
