app_name = "hea"
app_title = "HEA"
app_publisher = "Higher Education Authority"
app_description = "Higher Education Authority customisations: HR, disciplinary and related modules"
app_email = "mirriamnampemba@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["frappe", "erpnext", "hrms"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "hea",
# 		"logo": "/assets/hea/logo.png",
# 		"title": "HEA",
# 		"route": "/hea",
# 		"has_permission": "hea.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/hea/css/hea.css"
# app_include_js = "/assets/hea/js/hea.js"

# include js, css files in header of web template
# web_include_css = "/assets/hea/css/hea.css"
# web_include_js = "/assets/hea/js/hea.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "hea/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "hea/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": ["hea.hea_disciplinary.utils.get_employee_user_email"],
}

# Installation
# ------------

# workflow and permission fixtures link to these roles, so they must exist before fixtures sync
before_install = ["hea.hea_disciplinary.utils.ensure_roles", "hea.registry.setup.ensure_roles"]
before_migrate = ["hea.hea_disciplinary.utils.ensure_roles", "hea.registry.setup.before_migrate"]
after_migrate = ["hea.registry.setup.after_migrate"]
after_install = ["hea.registry.setup.after_migrate"]
# after_install = "hea.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "hea.uninstall.before_uninstall"
# after_uninstall = "hea.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "hea.utils.before_app_install"
# after_app_install = "hea.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "hea.utils.before_app_uninstall"
# after_app_uninstall = "hea.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hea.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["hea.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

REGISTRY_RECORDS = ("Correspondence", "Registry File", "File Subject", "File Movement", "File Request")

doc_events = {
    "Drive Permission": {
        "validate": "hea.overrides.drive_permission.validate",
    },
    "Confidentiality Level": {
        "on_update": "hea.registry.confidentiality.clear_cache",
        "on_trash": "hea.registry.confidentiality.clear_cache",
    },
    **{dt: {"on_trash": "hea.registry.records.check_delete"} for dt in REGISTRY_RECORDS},
}

# Records control (Phase 5): need to know, declared Drive scans, deletion with a reason
permission_query_conditions = {
    "Correspondence": "hea.registry.confidentiality.correspondence_query",
    "Registry File": "hea.registry.confidentiality.registry_file_query",
    "File Movement": "hea.registry.confidentiality.file_movement_query",
    "File Request": "hea.registry.confidentiality.file_request_query",
}
has_permission = {
    "Correspondence": "hea.registry.confidentiality.correspondence_permission",
    "Registry File": "hea.registry.confidentiality.registry_file_permission",
    "File Movement": "hea.registry.confidentiality.file_movement_permission",
    "File Request": "hea.registry.confidentiality.file_request_permission",
}
override_doctype_class = {"Drive File": "hea.overrides.drive_file.RegistryDriveFile"}
override_whitelisted_methods = {"drive.api.files.remove_or_restore": "hea.overrides.drive_file.remove_or_restore"}
doctype_js = {dt: "public/js/registry_record.js" for dt in REGISTRY_RECORDS}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": ["hea.registry.escalation.escalate_overdue", "hea.registry.movement.flag_overdue_files"],
}

# scheduler_events = {
# 	"all": [
# 		"hea.tasks.all"
# 	],
# 	"daily": [
# 		"hea.tasks.daily"
# 	],
# 	"hourly": [
# 		"hea.tasks.hourly"
# 	],
# 	"weekly": [
# 		"hea.tasks.weekly"
# 	],
# 	"monthly": [
# 		"hea.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "hea.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "hea.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "hea.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["hea.utils.before_request"]
# after_request = ["hea.utils.after_request"]

# Job Events
# ----------
# before_job = ["hea.utils.before_job"]
# after_job = ["hea.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"hea.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# Fixtures
# --------
# HEA Disciplinary configuration, ported from REA Disciplinary

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["name", "in", ["Disciplinary-custom_closed_from_stage", "Disciplinary-custom_closed_on", "Disciplinary-custom_closure_col", "Disciplinary-custom_closure_detail", "Disciplinary-custom_closure_outcome", "Disciplinary-custom_closure_section", "Disciplinary-custom_employee_notify_email", "Disciplinary-custom_offender_grade", "Disciplinary-custom_supervisor_notify_email", "Forced leave-disciplinary_case_no", "HR Settings-custom_disciplinary_section", "HR Settings-custom_verbal_warning_validity_months", "HR Settings-custom_written_warning_validity_months", "Hearing Committee-custom_board_member"]]],
	},
	{
		"dt": "Property Setter",
		"filters": [["name", "in", ["Appeal Verdict-appeal_decision-mandatory_depends_on", "Disciplinary Charges-comments-read_only_depends_on", "Disciplinary Charges-specific_offence-mandatory_depends_on", "Disciplinary Charges-specific_offence-read_only_depends_on", "Disciplinary Charges-warning_expiry_date-read_only", "Disciplinary-appeal_committee_chairperson-read_only_depends_on", "Disciplinary-appeal_committee_section-depends_on", "Disciplinary-appeal_date-placeholder", "Disciplinary-appeal_date-read_only_depends_on", "Disciplinary-appeal_decision-read_only_depends_on", "Disciplinary-appeal_hearing_report-mandatory_depends_on", "Disciplinary-appeal_hearing_report-read_only_depends_on", "Disciplinary-appeal_members-read_only_depends_on", "Disciplinary-appeal_tab-depends_on", "Disciplinary-appeal_time-read_only_depends_on", "Disciplinary-appeal_venue-read_only_depends_on", "Disciplinary-appeal_verdict-read_only_depends_on", "Disciplinary-case_summary-ignore_xss_filter", "Disciplinary-case_summary-options", "Disciplinary-case_summary_tab-depends_on", "Disciplinary-charge_description-allow_in_quick_entry", "Disciplinary-charge_description-description", "Disciplinary-charge_description-mandatory_depends_on", "Disciplinary-charge_description-placeholder", "Disciplinary-charge_description-read_only_depends_on", "Disciplinary-charge_tab-depends_on", "Disciplinary-details_tab-read_only_depends_on", "Disciplinary-employee-in_list_view", "Disciplinary-employee-read_only_depends_on", "Disciplinary-employee_name-in_list_view", "Disciplinary-employee_response-depends_on", "Disciplinary-employee_response-mandatory_depends_on", "Disciplinary-employee_response-read_only_depends_on", "Disciplinary-exculpation_tab-depends_on", "Disciplinary-exculpation_tab-read_only_depends_on", "Disciplinary-grounds_for_appeal-read_only_depends_on", "Disciplinary-hearing-read_only_depends_on", "Disciplinary-hearing_date-in_list_view", "Disciplinary-hearing_date-mandatory_depends_on", "Disciplinary-hearing_date-read_only_depends_on", "Disciplinary-hearing_decision-mandatory_depends_on", "Disciplinary-hearing_decision-read_only_depends_on", "Disciplinary-hearing_outcome-mandatory_depends_on", "Disciplinary-hearing_outcome-read_only_depends_on", "Disciplinary-hearing_outcome_section-depends_on", "Disciplinary-hearing_report-mandatory_depends_on", "Disciplinary-hearing_report-read_only_depends_on", "Disciplinary-hearing_response_deadline-read_only_depends_on", "Disciplinary-hearing_summary-mandatory_depends_on", "Disciplinary-hearing_summary-read_only_depends_on", "Disciplinary-hearing_tab-depends_on", "Disciplinary-hearing_time-read_only_depends_on", "Disciplinary-hearing_venue-default", "Disciplinary-hearing_venue-mandatory_depends_on", "Disciplinary-hearing_venue-placeholder", "Disciplinary-hearing_venue-read_only_depends_on", "Disciplinary-main-field_order", "Disciplinary-reports_and_attachments_section-depends_on", "Disciplinary-response_document-depends_on", "Disciplinary-response_document-read_only_depends_on", "Disciplinary-section_break_ieyi-depends_on", "Disciplinary-section_break_mkzn-depends_on", "Disciplinary-section_break_thtd-depends_on", "Disciplinary-select_outcome-depends_on", "Disciplinary-select_outcome-label", "Disciplinary-select_outcome-mandatory_depends_on", "Disciplinary-select_outcome-options", "Disciplinary-select_outcome-read_only", "Disciplinary-select_outcome-read_only_depends_on", "Disciplinary-set_appeal_date_section-depends_on", "Disciplinary-set_hearing_date_section-depends_on", "Disciplinary-supervisor_satisfactory_reason-depends_on", "Disciplinary-supervisor_satisfactory_reason-mandatory_depends_on", "Disciplinary-warning-depends_on", "Disciplinary-warning-fieldtype", "Disciplinary-warning-mandatory_depends_on", "Disciplinary-warning-read_only_depends_on", "Verdict-verdict-mandatory_depends_on"]]],
	},
	{
		"dt": "Client Script",
		"filters": [["name", "in", ["Action Buttons on Disciplinary", "Custom Html Block", "Disciplinary Committee Grade Filter", "Disciplinary Main", "Filter Supervisor Only report to", "No duplicate committee Entries"]]],
	},
	{
		"dt": "Server Script",
		"filters": [["name", "in", ["Appeal Committe", "Auto-calculate Appeal Response Deadline (Invite Committee)", "Auto-calculate Hearing Response Deadline (Invite Committee)", "Auto-calculate response deadline on Issue Charge", "Daily Scheduler", "Disciplinary Case Closure", "Disciplinary Committee Composition", "Issue Charge → Email to Employee", "No duplicate Committe", "Require charge before leaving Charge stage", "Set Hearing Date → Appeal Email", "Set Hearing Date → Email to Committee Members", "Summary dismisal", "Sync Notification Emails"]]],
	},
	{
		"dt": "Print Format",
		"filters": [["name", "in", ["Disciplinary Report"]]],
	},
	{
		"dt": "Report",
		"filters": [["name", "in", ["Active Employee Warnings", "Disciplinary action", "Employees on Disciplinary Action"]]],
	},
	{
		"dt": "Notification",
		"filters": [["name", "in", ["DISC – Appeal Outcome – Email", "DISC – Appeal Requested – Email", "DISC – Appeal Under Review – Email", "DISC – Awaiting Employee Decision – Email", "DISC – Awaiting Exculpation – Email", "DISC – Case Closed – Email", "DISC – Charge Initiated – Email", "DISC – Disciplinary Committee – Email", "DISC – Exculpation Evaluation – Email", "DISC – Grounds for Appeal – Email", "DISC – Hearing Outcome – Email", "DISC – Issue Charge – Email", "DISC – Issue Warning – Email", "DISC – Pending DG Approval – Email", "DISC – Pending Outcome Approval – Email", "DISC – Recommend Disciplinary Hearing – Email", "DISC – Recommendation of Charge – Email", "DISC – Set Appeal Date – Email", "DISC – Set Hearing Date – Email"]]],
	},
	{
		"dt": "Custom DocPerm",
		"filters": [["name", "in", ["0phvr0mlb7", "14n9qtbcav", "577mps0av9", "578jphsgnu", "7sksds86sd", "8p7hmv6793", "b9h50l6hia", "bepn9ufb8f", "f2l49gn507", "f2l8k12o83", "g2vt75gih1", "rr0ebl8eld", "rr1nv10esm", "thi3ikail5", "tovbq81eau"]]],
	},
	{
		"dt": "Workflow",
		"filters": [["name", "in", ["Disciplinary"]]],
	},
	{
		"dt": "Workflow State",
		"filters": [["name", "in", ["Appeal Outcome", "Appeal Requested", "Appeal Under Review", "Awaiting Employee Decision", "Awaiting Exculpation", "Case Closed", "Charge", "Disciplinary Committee", "Draft", "Exculpation Evaluation", "Grounds for Appeal", "Hearing Outcome", "Issue Charge", "Issue Warning", "Pending DG Approval", "Pending Outcome Approval", "Recommend Disciplinary Hearing", "Recommendation of Charge", "Set Appeal Date", "Set Hearing Date"]]],
	},
	{
		"dt": "Workflow Action Master",
		"filters": [["name", "in", ["Accept Verdict", "Appeal Verdict", "Approve", "Close Case", "Committee Appointed", "Invite Committee", "Issue Charge", "Issue Warning", "Non Satisfactory and Dismissible", "Recommend Charge", "Reject", "Satisfactory and Not Dismissible", "Send", "Submit", "Submit Response"]]],
	},
	{
		"dt": "Number Card",
		"filters": [["name", "in", ["? Pending Disciplinary Cases"]]],
	},
	{
		"dt": "Dashboard Chart",
		"filters": [["name", "in", ["Disciplinary"]]],
	},
	"Offence Category",
	"Offence Master",
	"Offence Sanction Matrix",
]
