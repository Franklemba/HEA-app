import os, re
from pathlib import Path
import frappe
frappe.init(site="dev.local", sites_path="."); frappe.connect()
frappe.set_user("Administrator")
res = []
def check(n, desc, ok, detail=""):
    res.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {n}. {desc}  {detail}")

cleanup = []
TEAM = None
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request
frappe.local.request = Request(EnvironBuilder(path="/").get_environ())
def run():
    global cleanup
    global TEAM
    TEAM = "lsblg32uos"  # Administrator's own Drive team, used only inside this rolled-back test
    frappe.db.set_single_value("Registry Settings", "drive_team", TEAM)
    frappe.clear_document_cache("Registry Settings", "Registry Settings")

    def user(email, role):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": role, "send_welcome_email": 0,
                        "roles": [{"role": role}]}).insert(ignore_permissions=True)
        return email
    staff = user("t.registry@test.local", "Registry Staff")
    gen = user("t.general@test.local", "General Staff")
    team = frappe.get_doc("Drive Team", TEAM); team.append("users", {"user": staff, "access_level": 1}); team.save(ignore_permissions=True)

    def upload(name, data):
        f = frappe.get_doc({"doctype": "File", "file_name": name, "content": data, "is_private": 1}).insert(ignore_permissions=True)
        cleanup.append(Path(f.get_full_path())); return f.file_url

    FILE = "HEA/101/1/2"
    frappe.set_user(staff)
    from io import BytesIO
    from pypdf import PdfWriter
    w = PdfWriter(); w.add_blank_page(595, 842); buf = BytesIO(); w.write(buf); pdf = buf.getvalue()
    a = frappe.get_doc({"doctype": "Correspondence", "direction": "Incoming", "sender": "University of Zambia",
        "their_reference": "UNZA/REG/12", "subject": "Request for accreditation visit", "department": "Quality Assurance - HEA",
        "urgency": "Urgent", "mode_of_delivery": "Hand Delivery", "enclosures": 1,
        "registry_file": FILE, "folio_placement": "Folio Number", "folio_reference": 20,
        "scan": upload("unza-letter.pdf", pdf)}).insert()
    a.reload()
    check(1, "Incoming letter registered on HEA/101/1/2 at folio 20, with a reference number",
          a.folio_number == "20" and re.fullmatch(r"HEA/IN/\d{4}/\d{5}", a.name), f"[{a.name}, folio {a.folio_number}]")
    for p in frappe.get_all("Drive File", {"team": TEAM, "creation": [">=", a.creation]}, pluck="path"):
        if p and not p.endswith("/"): cleanup.append(Path(frappe.get_site_path("private/files", p)))
    df = frappe.get_doc("Drive File", a.drive_file) if a.drive_file else None
    folder = frappe.db.get_value("Registry File", FILE, "drive_folder")
    from drive.api.files import get_file_content
    resp = get_file_content(a.drive_file)
    body = b"".join(resp.response) if hasattr(resp, "response") else resp
    old_file_gone = not frappe.db.exists("File", {"file_url": ["like", "%unza-letter%"]})
    check(2, "Scan opens from the record and sits in the file's Drive folder (kept once)",
          df and df.parent_entity == folder and frappe.db.get_value("Drive File", folder, "title") == "HEA-101-1-2"
          and a.scan.endswith(a.drive_file) and body == pdf and old_file_gone,
          f"[{df.title if df else None} in folder {frappe.db.get_value('Drive File', folder, 'title')}]")
    frappe.set_user(gen)
    try: get_file_content(a.drive_file); gen_blocked = False
    except frappe.PermissionError: gen_blocked = True
    print("      note: General Staff (not in the Drive team) blocked from the scan:", gen_blocked)
    frappe.set_user(staff)

    def item(placement, ref=None, subject="Test item"):
        return frappe.get_doc({"doctype": "Correspondence", "direction": "Incoming", "sender": "Test sender",
            "subject": subject, "registry_file": FILE, "folio_placement": placement, "folio_reference": ref}).insert()
    enc = item("Enclosure", 20, "Enclosure: institution profile")
    nxt = item("Next Folio", None, "Follow-up letter")
    ins = item("Inserted Folio", 20, "Late reply filed after folio 20")
    ins2 = item("Inserted Folio", 20, "Second late item")
    try: item("Folio Number", 21); dup_refused = False
    except frappe.ValidationError: dup_refused = True
    check(3, "Enclosure gets 20/1, next folio 21, inserted item 20A (then 20B); a taken folio is refused",
          [enc.folio_number, nxt.folio_number, ins.folio_number, ins2.folio_number] == ["20/1", "21", "20A", "20B"] and dup_refused,
          f"[{enc.folio_number}, {nxt.folio_number}, {ins.folio_number}, {ins2.folio_number}]")

    b = frappe.get_doc({"doctype": "Correspondence", "direction": "Outgoing", "recipient": "Copperbelt University",
        "sender_department": "Quality Assurance - HEA", "subject": "Accreditation visit schedule",
        "registry_file": FILE, "folio_placement": "Next Folio"}).insert()
    b.record_dispatch(dispatch_mode="Courier", received_by="J. Banda", copies_sent_to="Director General\nUNZA Registrar")
    b.reload()
    check(4, "Outgoing letter registered and its dispatch recorded",
          re.fullmatch(r"HEA/OUT/\d{4}/\d{5}", b.name) and b.dispatched_on and b.dispatched_by == staff
          and b.dispatch_mode == "Courier" and b.received_by == "J. Banda", f"[{b.name}, folio {b.folio_number}]")

    frappe.set_user("Administrator")
    cf = frappe.get_doc({"doctype": "Registry File", "file_subject": "101/4", "file_title": "TEST CLOSED FILE"}).insert()
    cf.close_file("test")
    frappe.set_user(staff)
    try:
        frappe.get_doc({"doctype": "Correspondence", "direction": "Incoming", "sender": "X", "subject": "Late letter",
                        "registry_file": cf.name}).insert(); closed_refused = False
    except frappe.ValidationError as e: closed_refused = "closed" in str(e).lower()
    try:
        nxt.registry_file = cf.name; nxt.save(); moved_refused = False
    except frappe.ValidationError: moved_refused = True
    nxt.reload()
    check(5, "Putting an item on a closed file is refused (new item, and moving one there)", closed_refused and moved_refused)

    c = frappe.get_doc({"doctype": "Correspondence", "direction": "Internal", "sender": "Director, Quality Assurance",
        "sender_department": "Quality Assurance - HEA", "recipient": "Director General", "department": "Director Generals Office - HEA",
        "subject": "Internal memo on accreditation visit", "registry_file": FILE}).insert()
    from hea.registry.mail_register import execute
    regs = {d: [r["name"] for r in execute(d, {"registry_file": FILE})[1]] for d in ("Incoming", "Outgoing", "Internal")}
    qa = [r["name"] for r in execute("Outgoing", {"department": "Quality Assurance - HEA"})[1]]
    check(6, "Each item appears only in its own register; department filter works",
          a.name in regs["Incoming"] and b.name in regs["Outgoing"] and c.name in regs["Internal"]
          and b.name not in regs["Incoming"] and a.name not in regs["Internal"] and b.name in qa
          and re.fullmatch(r"HEA/INT/\d{4}/\d{5}", c.name), f"[{ {k: len(v) for k, v in regs.items()} }]")

    frappe.set_user(gen)
    check("6b", "General Staff can read correspondence, cannot register it",
          frappe.has_permission("Correspondence", "read") and not frappe.has_permission("Correspondence", "create"))
    frappe.set_user("Administrator")


try:
    run()
finally:
    frappe.db.rollback()
    drive_root = Path(frappe.get_site_path("private/files", "Administrator (Administrator)", "Registry Files"))
    for p in cleanup:
        p.unlink(missing_ok=True)
    for d in sorted(drive_root.glob("**/*"), reverse=True) + [drive_root]:
        if d.is_dir() and not any(d.iterdir()): d.rmdir()

for p in cleanup:
    p.unlink(missing_ok=True)
left = [str(p) for p in cleanup if p.exists()] + ([str(drive_root)] if drive_root.exists() else [])
print("ALL PASS" if all(res) else f"{res.count(False)} FAILED")
print("after rollback: correspondence", frappe.db.count("Correspondence"), "| drive_team:",
      frappe.db.get_single_value("Registry Settings", "drive_team"), "| disk leftovers:", left)
frappe.destroy()
