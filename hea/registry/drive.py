"""File correspondence scans in Frappe Drive, one folder per registry file.

The scan is attached to the Correspondence as usual, then moved into Drive: the Drive copy is the only one
kept, and the Correspondence's Scan field points at it. Registry users must be members of the Drive team set in
Registry Settings to open the scans.
"""

import mimetypes
import os
from pathlib import Path

import frappe
from frappe import _

DRIVE_URL_PREFIX = "/api/method/drive.api.files.get_file_content?entity_name="


def drive_url(entity):
	return f"{DRIVE_URL_PREFIX}{entity}"


def safe_title(title):
	# Drive stores files on disk under their titles, so a / would make sub-folders.
	return title.replace("/", "-").strip()


def file_scan_in_drive(doc):
	settings = frappe.get_cached_doc("Registry Settings")
	if not settings.drive_team or "drive" not in frappe.get_installed_apps():
		return
	from hea.registry.confidentiality import is_restricted
	if is_restricted(doc.confidentiality_level):
		return  # need to know: the scan stays a private attachment, seen only by those who may open the item

	from drive.api.files import get_unused_title, get_upload_path
	from drive.utils import create_drive_file, get_home_folder, update_file_size
	from drive.utils.files import FileManager

	file_name = frappe.db.get_value("File", {"file_url": doc.scan}, "name", order_by="creation desc")
	if not file_name:
		return
	file_doc = frappe.get_doc("File", file_name)
	content = file_doc.get_content()
	if isinstance(content, str):
		content = content.encode()

	team = settings.drive_team
	home = get_home_folder(team)
	manager = FileManager()
	folder = ensure_file_folder(doc.registry_file, team, home, manager, settings.drive_root_folder)

	ext = os.path.splitext(file_doc.file_name or "")[1]
	label = f"Folio {doc.folio_number} - {doc.name}" if doc.folio_number else doc.name
	title = get_unused_title(safe_title(label) + ext, folder)
	mime_type = mimetypes.guess_type(title)[0] or "application/octet-stream"

	temp_path = get_upload_path(home["path"], f"{frappe.generate_hash(length=10)}_{title}")
	temp_path.write_bytes(content)
	drive_file = create_drive_file(
		team, title, folder, mime_type, lambda entity: manager.get_disk_path(entity, home), len(content))
	manager.upload_file(temp_path, drive_file)
	update_file_size(folder, len(content))

	# If this save is rolled back, don't leave the copy on disk.
	disk_path = manager.resolve(drive_file.path)
	frappe.db.after_rollback.add(lambda: disk_path.unlink(missing_ok=True))

	# Keep the scan once: drop Frappe's copy once the Drive copy is committed.
	old_path = Path(file_doc.get_full_path())
	shared = frappe.db.exists("File", {"file_url": file_doc.file_url, "name": ["!=", file_doc.name]})
	frappe.db.delete("File", file_doc.name)
	if not shared:  # Frappe reuses one copy on disk for identical uploads
		frappe.db.after_commit.add(lambda: old_path.unlink(missing_ok=True))

	doc.db_set({"drive_file": drive_file.name, "scan": drive_url(drive_file.name)}, update_modified=False)
	doc.add_comment("Info", _("Scan filed in Drive as {0}.").format(title))


def ensure_file_folder(registry_file, team, home, manager, root_title=None):
	"""The registry file's Drive folder, created under the Registry Files folder the first time it is needed."""
	current = frappe.db.get_value("Registry File", registry_file, "drive_folder")
	if current and frappe.db.get_value("Drive File", current, "is_active") == 1:
		return current
	root = find_or_create_folder(team, safe_title(root_title or "Registry Files"), home["name"], home, manager)
	folder = find_or_create_folder(team, safe_title(registry_file), root, home, manager)
	frappe.db.set_value("Registry File", registry_file, "drive_folder", folder, update_modified=False)
	return folder


def find_or_create_folder(team, title, parent, home, manager):
	from drive.utils import create_drive_file

	existing = frappe.db.get_value(
		"Drive File", {"title": title, "is_group": 1, "is_active": 1, "team": team, "parent_entity": parent}, "name")
	if existing:
		return existing
	parent_path = frappe.db.get_value("Drive File", parent, "path") or ""
	path = manager.create_folder(
		frappe._dict(title=title, team=team, parent_path=Path(parent_path)), home)
	return create_drive_file(team, title, parent, "folder", lambda _: path, is_group=True).name
