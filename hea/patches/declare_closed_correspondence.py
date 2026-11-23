import frappe


def execute():
	"""Phase 5: the Closed stage declares a record (submits it). Update the workflow created in Phase 3."""
	if not frappe.db.exists("Workflow", "Correspondence Routing"):
		return
	frappe.db.sql("""update `tabWorkflow Document State` set doc_status='1'
		where parenttype='Workflow' and parent='Correspondence Routing' and state='Closed'""")
	# Items already closed before this change become declared records too.
	frappe.db.sql("update `tabCorrespondence` set docstatus=1 where workflow_state='Closed' and docstatus=0")
	frappe.clear_cache(doctype="Correspondence")
