from io import BytesIO
from pathlib import Path
import frappe
frappe.init(site="dev.local", sites_path="."); frappe.connect()
frappe.set_user("Administrator")
res = []
def check(n, desc, ok, detail=""):
    res.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {n}. {desc}  {detail}")

real_commit = frappe.db.commit
frappe.db.commit = lambda *a, **k: None
import frappe.email.doctype.notification.notification as notif_mod
notif_mod.enqueue_create_notification = lambda *a, **k: None
from frappe.model.workflow import apply_workflow
QA, FILE, TEAM = "Quality Assurance - HEA", "HEA/101/1/2", "lsblg32uos"
cleanup = []

def run():
    def user(email, role):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0,
                        "roles": [{"role": role}]}).insert(ignore_permissions=True)
        return email
    U = {r: user(e, r) for e, r in [
        ("t.sysadmin@test.local", "System Manager"), ("t.officer@test.local", "Documentation and Registry Officer"),
        ("t.registry@test.local", "Registry Staff"), ("t.qahead@test.local", "Departmental Head"),
        ("t.general@test.local", "General Staff"), ("t.mgmt@test.local", "Management and Authorised Auditors")]}
    reg, off, head, gen, mgmt, sysm = (U["Registry Staff"], U["Documentation and Registry Officer"], U["Departmental Head"],
        U["General Staff"], U["Management and Authorised Auditors"], U["System Manager"])
    other_head = user("t.legalhead@test.local", "Departmental Head")
    st = frappe.get_single("Registry Settings"); st.drive_team = TEAM
    st.append("department_heads", {"department": QA, "head": head}); st.save()
    frappe.clear_document_cache("Registry Settings", "Registry Settings")
    team = frappe.get_doc("Drive Team", TEAM); team.append("users", {"user": reg, "access_level": 1}); team.save(ignore_permissions=True)

    def as_(u): frappe.set_user(u)
    def refused(fn):
        try: fn(); return False
        except (frappe.ValidationError, frappe.PermissionError): return True
    def upload(name):
        from pypdf import PdfWriter
        w = PdfWriter(); w.add_blank_page(595, 842); b = BytesIO(); w.write(b)
        f = frappe.get_doc({"doctype": "File", "file_name": name, "content": b.getvalue(), "is_private": 1}).insert(ignore_permissions=True)
        cleanup.append(Path(f.get_full_path())); return f.file_url
    def new(**kw):
        as_(reg)
        return frappe.get_doc({"doctype": "Correspondence", "direction": "Incoming", "sender": "University of Zambia",
            "subject": "Accreditation of new programmes", "department": QA, "urgency": "Routine", "registry_file": FILE, **kw}).insert()
    def declare(doc):
        steps = [(reg, "Assign to Department", {}), (head, "Assign to Officer", {"assigned_officer": gen}),
                 (gen, "Record Action", {"action_taken": "Replied"}), (head, "Start Review", {}), (head, "Approve", {}),
                 (reg, "File", {}), (reg, "Close", {})]
        for u, action, prep in steps:
            as_(u); d = frappe.get_doc("Correspondence", doc.name)
            if prep: d.prepare_action(action, prep)
            apply_workflow(d, action)
        return frappe.get_doc("Correspondence", doc.name)

    # 1. Declared records cannot be edited by anyone; corrections refer to the old item
    a = declare(new(scan=upload("declared-scan.pdf")))
    for p in frappe.get_all("Drive File", {"team": TEAM, "creation": [">=", a.creation]}, pluck="path"):
        if p and not p.endswith("/"): cleanup.append(Path(frappe.get_site_path("private/files", p)))
    edits = {}
    for role, u in list(U.items()) + [("Administrator", "Administrator")]:
        as_(u)
        def edit():
            d = frappe.get_doc("Correspondence", a.name); d.subject = "Changed after declaration"; d.save()
        edits[role] = refused(edit)
    cancels = {r: refused(lambda: (as_(u), frappe.get_doc("Correspondence", a.name).cancel())) for r, u in [("Officer", off), ("System Manager", sysm), ("Administrator", "Administrator")]}
    as_(reg)
    from hea.registry.records import correction_defaults
    corr = frappe.get_doc({"doctype": "Correspondence", **correction_defaults(a.name)}).insert()
    check(1, "Declared record (Closed) cannot be edited or cancelled by any role, Administrator included; a correction refers to it",
          a.docstatus == 1 and all(edits.values()) and all(cancels.values()) and corr.corrects_item == a.name
          and frappe.db.get_value("Correspondence", a.name, "subject") == "Accreditation of new programmes",
          f"[edits refused: {sum(edits.values())}/{len(edits)}; cancels refused: {sum(cancels.values())}/3; correction {corr.name}]")

    # 2. Only the Officer deletes, with a reason, logged
    b = declare(new(subject="Duplicate registration of UNZA letter"))
    from hea.registry.records import delete_record
    tries = {}
    for role, u in U.items():
        if role == "Documentation and Registry Officer": continue
        as_(u)
        tries[role] = refused(lambda: delete_record("Correspondence", b.name, "Not needed")) and \
                      refused(lambda: frappe.delete_doc("Correspondence", b.name))
    as_("Administrator"); tries["Administrator"] = refused(lambda: frappe.delete_doc("Registry File", "HEA/101/1/9"))
    as_(off)
    plain_delete = refused(lambda: frappe.delete_doc("Correspondence", b.name))
    no_reason = refused(lambda: delete_record("Correspondence", b.name, ""))
    log = delete_record("Correspondence", b.name, "Registered twice: duplicate of an earlier item")
    logged = frappe.get_doc("Registry Deletion Log", log)
    check(2, "Every other role (and Administrator) is refused; the Officer must give a reason, and the deletion is logged",
          all(tries.values()) and plain_delete and no_reason and not frappe.db.exists("Correspondence", b.name)
          and logged.reason.startswith("Registered twice") and logged.deleted_by == off and logged.was_declared
          and b.name in (logged.data or ""), f"[{log}; refused: {sorted(r for r, v in tries.items() if v)}]")

    # 3. The Drive scan of a declared record cannot be trashed, deleted, moved or renamed
    as_(reg)
    df = frappe.get_doc("Drive File", a.drive_file)
    folder = df.parent_entity
    from hea.overrides.drive_file import remove_or_restore
    guard = {
        "trash": refused(lambda: remove_or_restore([df.name])),
        "trash folder": refused(lambda: remove_or_restore([folder])),
        "delete": refused(lambda: frappe.get_doc("Drive File", df.name).permanent_delete()),
        "rename": refused(lambda: frappe.get_doc("Drive File", df.name).rename("renamed.pdf")),
        "move": refused(lambda: frappe.get_doc("Drive File", df.name).move(frappe.db.get_value("Drive File", folder, "parent_entity"))),
    }
    as_("Administrator"); guard["admin delete_doc"] = refused(lambda: frappe.delete_doc("Drive File", df.name, ignore_permissions=True))
    still = frappe.db.get_value("Drive File", df.name, ["is_active", "title", "parent_entity"], as_dict=True)
    on_disk = Path(frappe.get_site_path("private/files", df.path)).exists()
    check(3, "Trashing, deleting, moving or renaming the declared record's Drive scan (or its folder) is refused",
          all(guard.values()) and still.is_active == 1 and still.title == df.title and still.parent_entity == folder and on_disk,
          f"{guard}")

    # 4. Need to know
    c = new(subject="Confidential: complaint against an institution", confidentiality_level="Confidential", scan=upload("confidential.pdf"))
    as_(reg); c = frappe.get_doc("Correspondence", c.name)
    scan_private = not c.drive_file and c.scan.startswith("/private/files/")
    as_(reg); apply_workflow(frappe.get_doc("Correspondence", c.name), "Assign to Department")
    from frappe.desk.search import search_link
    from frappe.desk.form.load import getdoc
    as_(gen)
    gen_list = c.name in frappe.get_list("Correspondence", pluck="name", limit_page_length=0)
    gen_open = frappe.has_permission("Correspondence", "read", c.name)
    gen_search = c.name in [r.get("value") for r in (search_link("Correspondence", "complaint against", page_length=50) or [])]
    gen_report = c.name in [r["name"] for r in __import__("hea.registry.mail_register", fromlist=["x"]).execute("Incoming", {})[1]]
    scan_file = frappe.db.get_value("File", {"file_url": c.scan}, "name")
    gen_scan = frappe.has_permission("File", "read", scan_file)
    as_(other_head); other_open = frappe.has_permission("Correspondence", "read", c.name)
    as_(head)
    head_open = frappe.has_permission("Correspondence", "read", c.name)
    getdoc("Correspondence", c.name)
    viewed = frappe.get_all("Confidential View Log", {"viewed_name": c.name, "viewed_by": head}, ["confidentiality_level", "viewed_on"])
    as_(mgmt); mgmt_open = frappe.has_permission("Correspondence", "read", c.name)
    # a confidential file hides its paper-file records too, and its new items inherit the level
    as_(reg); fdoc = frappe.get_doc("Registry File", "HEA/101/1/7"); fdoc.confidentiality_level = "Confidential"
    staff_locked_out = refused(fdoc.save)  # Registry Staff may not classify a file above what they may see
    as_(off); fdoc = frappe.get_doc("Registry File", "HEA/101/1/7"); fdoc.confidentiality_level = "Confidential"; fdoc.save()
    as_(off); inherited = frappe.get_doc({"doctype": "Correspondence", "direction": "Incoming", "sender": "X", "department": QA,
        "subject": "Letter on a confidential file", "registry_file": "HEA/101/1/7"}).insert().confidentiality_level
    as_(gen); gen_file = frappe.has_permission("Registry File", "read", "HEA/101/1/7")
    check(4, "General Staff cannot see, list, search or report a Confidential item or open its scan; the item's head can, and the view is logged",
          scan_private and not gen_list and not gen_open and not gen_search and not gen_report and not gen_scan
          and not other_open and head_open and viewed and viewed[0].confidentiality_level == "Confidential" and mgmt_open
          and inherited == "Confidential" and not gen_file and staff_locked_out,
          f"[scan kept out of Drive: {scan_private}; view logged at {viewed[0].viewed_on if viewed else None}]")

    # 5. Each role against the permission matrix
    from hea.registry.report.registry_permission_matrix.registry_permission_matrix import execute as matrix
    rows = matrix()[1]
    mismatches = []
    for r in rows:
        u = U.get(r["role"])
        if not u: continue
        as_(u)
        own_only = r["only_own"] == "✓"
        if own_only:  # rights apply to the user's own records only
            mine = frappe.get_doc({"doctype": r["doctype"], "registry_file": "HEA/101/1/5", "purpose": "matrix test"}).insert()
            as_(reg); theirs = frappe.get_doc({"doctype": r["doctype"], "registry_file": "HEA/101/1/6", "purpose": "matrix test"}).insert()
            as_(u)
        for right in ("read", "write", "create", "delete", "submit"):
            expected = r[right] == "✓"
            if own_only and right in ("read", "write"):
                actual = bool(frappe.has_permission(r["doctype"], right, mine.name))
                if expected and frappe.has_permission(r["doctype"], right, theirs.name):
                    mismatches.append((r["doctype"], r["role"], right, "own only", "others too"))
            else:
                actual = bool(frappe.has_permission(r["doctype"], right))
            if expected != actual: mismatches.append((r["doctype"], r["role"], right, expected, actual))
    as_("Administrator")
    off_delete = frappe.has_permission("Correspondence", "delete", user=off)
    others_delete = [rl for rl, u in U.items() if rl != "Documentation and Registry Officer"
                     and any(frappe.has_permission(dt, "delete", user=u) for dt in ("Correspondence", "Registry File", "File Subject", "File Movement", "File Request"))]
    check(5, "Each of the six roles gets exactly the rights in the permission matrix; only the Officer has delete",
          not mismatches and off_delete and not others_delete, f"[{len(rows)} matrix rows checked; mismatches {mismatches[:5]}]")

try:
    run()
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()
    frappe.db.commit = real_commit
    drive_root = Path(frappe.get_site_path("private/files", "Administrator (Administrator)", "Registry Files"))
    for p in cleanup: p.unlink(missing_ok=True)
    for d in sorted(drive_root.glob("**/*"), reverse=True) + [drive_root]:
        if d.is_dir() and not any(d.iterdir()): d.rmdir()
print("ALL PASS" if all(res) and len(res) == 5 else f"{res.count(False)} FAILED of {len(res)}")
print("after rollback: correspondence", frappe.db.count("Correspondence"), "| deletion logs", frappe.db.count("Registry Deletion Log"),
      "| view logs", frappe.db.count("Confidential View Log"), "| HEA/101/1/7 level:", frappe.db.get_value("Registry File", "HEA/101/1/7", "confidentiality_level"),
      "| leftovers:", [str(p) for p in cleanup if p.exists()] + ([str(drive_root)] if drive_root.exists() else []))
frappe.destroy()
