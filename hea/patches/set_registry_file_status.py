import frappe


def execute():
	"""Files imported from the 2020 index were saved without a status; they are open files."""
	frappe.db.sql("update `tabRegistry File` set status='Open' where ifnull(status, '')=''")
