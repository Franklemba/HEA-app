"""Drive guard: a scan that belongs to a declared registry record cannot be trashed, deleted, moved or renamed.

Drive moves files on disk before it saves them, so the checks run first: in the Drive File class (move, rename,
permanent delete) and around Drive's trash endpoint. validate and on_trash are a backstop.
"""

import frappe
from frappe import _
from drive.drive.doctype.drive_file.drive_file import DriveFile


def protecting_record(entity):
	"""The declared Correspondence a Drive file (or anything inside a Drive folder) belongs to, if any."""
	name = entity.name if hasattr(entity, "name") else entity
	direct = frappe.db.get_value("Correspondence", {"drive_file": name, "docstatus": 1}, "name")
	if direct:
		return direct
	info = entity if hasattr(entity, "is_group") else frappe.db.get_value("Drive File", name, ["is_group", "path"], as_dict=True)
	if info and info.is_group and info.path:
		inside = frappe.db.sql(
			"""select c.name from `tabCorrespondence` c join `tabDrive File` d on d.name = c.drive_file
			where c.docstatus = 1 and d.path like %s limit 1""",
			(info.path.rstrip("/") + "/%",),
		)
		return inside[0][0] if inside else None
	return None


def refuse_if_protected(entity, action):
	record = protecting_record(entity)
	if record:
		frappe.throw(
			_("This scan belongs to declared record {0}, so it cannot be {1}.").format(frappe.bold(record), _(action)),
			frappe.PermissionError,
		)


class RegistryDriveFile(DriveFile):
	def move(self, *args, **kwargs):
		refuse_if_protected(self, "moved")
		return super().move(*args, **kwargs)

	def rename(self, *args, **kwargs):
		refuse_if_protected(self, "renamed")
		return super().rename(*args, **kwargs)

	def permanent_delete(self, *args, **kwargs):
		refuse_if_protected(self, "deleted")
		return super().permanent_delete(*args, **kwargs)

	def validate(self):
		if not self.is_new():
			before = self.get_doc_before_save()
			changed = before and any(before.get(f) != self.get(f) for f in ("is_active", "title", "parent_entity", "path"))
			if changed:
				refuse_if_protected(self, "changed")
		return super().validate()

	def on_trash(self):
		refuse_if_protected(self, "deleted")
		return super().on_trash()


@frappe.whitelist()
def remove_or_restore(entity_names, client=None):
	"""Drive's trash, with declared-record scans refused before anything moves on disk."""
	import json

	from drive.api.files import remove_or_restore as drive_remove_or_restore

	names = json.loads(entity_names) if isinstance(entity_names, str) else entity_names
	for name in names or []:
		if frappe.db.get_value("Drive File", name, "is_active") == 1:
			refuse_if_protected(name, "moved to the trash")
	return drive_remove_or_restore(entity_names, client)
