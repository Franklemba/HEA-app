import frappe
from frappe.utils import add_days, add_to_date, now_datetime, nowdate, getdate
frappe.init(site="dev.local", sites_path="."); frappe.connect()
frappe.set_user("Administrator")
res = []
def check(n, desc, ok, detail=""):
    res.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {n}. {desc}  {detail}")

real_commit = frappe.db.commit
frappe.db.commit = lambda *a, **k: None
sent = []
import frappe.email.doctype.notification.notification as notif_mod
notif_mod.enqueue_create_notification = lambda users, doc, **k: sent.append(
    (users if isinstance(users, list) else [u.strip() for u in users.split(",")], doc.get("subject")))
def told(user, since=0): return [s for u, s in sent[since:] if user in u]
def logs(user, docname): return frappe.get_all("Notification Log", {"for_user": user, "document_name": docname}, pluck="subject")

FILE, OTHER = "HEA/101/1/3", "HEA/101/1/4"

def run():
    def user(email, role):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0].split(".")[1].title(),
                        "send_welcome_email": 0, "roles": [{"role": role}]}).insert(ignore_permissions=True)
        return email
    reg = user("t.registry@test.local", "Registry Staff")
    u1 = user("t.mwansa@test.local", "General Staff")
    u2 = user("t.phiri@test.local", "General Staff")
    def as_(u): frappe.set_user(u)
    def rf(): return frappe.get_doc("Registry File", FILE)
    def refused(fn):
        try: fn(); return False
        except (frappe.ValidationError, frappe.PermissionError): return True

    # 1. Request and issue
    as_(u1); n = len(sent)
    r1 = frappe.get_doc({"doctype": "File Request", "registry_file": FILE, "purpose": "Board paper for next meeting"}).insert()
    reg_told = told(reg, n)
    as_(reg); n = len(sent)
    r1.reload(); mv1 = r1.issue_file(urgency="Urgent")
    f = rf(); r1.reload()
    check(1, "User requests HEA/101/1/3; Registry is told, issues it; the file shows the user as holder",
          reg_told and r1.status == "Issued" and f.holder == u1 and f.current_movement == mv1
          and f.current_location == "With Mwansa" and getdate(f.due_back) == getdate(add_days(nowdate(), 5))
          and told(u1, n), f"[{mv1}; {f.current_location}; due back {f.due_back}; label Urgent "
          f"{frappe.db.get_value('File Movement', mv1, 'colour')}]")

    # 2. Passed to a colleague through Registry
    as_(u1)
    self_transfer = refused(lambda: rf().transfer_file(u2))
    as_(u2)
    r2 = frappe.get_doc({"doctype": "File Request", "registry_file": FILE, "purpose": "Need the minutes"}).insert()
    as_(u1)
    sees_other = frappe.has_permission("File Request", "read", r2.name)
    as_(reg); r2.reload(); mv2 = r2.issue_file()
    f = rf()
    from hea.registry.movement import movement_history
    hist = movement_history(FILE)
    first = frappe.get_doc("File Movement", mv1)
    check(2, "User passes it to a colleague through Registry; both moves are in the history (users cannot transfer it themselves)",
          self_transfer and not sees_other and f.holder == u2 and len(hist) == 2 and hist[0].name == mv2
          and hist[0].status == "Out" and hist[1].status == "Transferred" and first.transferred_to == mv2
          and first.received_by == reg, f"[{[(h.name, h.issued_to_name, h.status) for h in hist]}]")

    # 3. Kept past 5 days: flagged, holder and Registry told; repeats after 3 days
    frappe.db.set_value("File Movement", mv2, {"issued_on": add_to_date(now_datetime(), days=-6), "due_back": add_days(nowdate(), -1)})
    frappe.db.set_value("Registry File", FILE, "due_back", add_days(nowdate(), -1))
    as_("Administrator")
    from hea.registry.movement import flag_overdue_files
    flagged = flag_overdue_files()
    again = flag_overdue_files()
    frappe.db.set_value("File Movement", mv2, "last_reminded_on", add_days(nowdate(), -3))
    third = flag_overdue_files()
    check(3, "File kept past its due date is flagged; holder and Registry notified; reminded again after 3 days",
          FILE in flagged and FILE not in again and FILE in third and rf().is_overdue
          and len(logs(u2, FILE)) == 2 and len(logs(reg, FILE)) == 2 and not logs(u1, FILE),
          f"[{logs(u2, FILE)[0] if logs(u2, FILE) else None}]")

    # reports while the file is out (step 6, first half)
    from hea.registry.files_out import execute as report
    as_(reg)
    rf2 = frappe.get_doc("Registry File", OTHER)
    mv3 = rf2.issue_file(u1, due_back=nowdate())
    out_rows = report("all")[1]; overdue_rows = report("overdue")[1]; today_rows = report("due_today")[1]
    by_holder = report("all", {"issued_to": u2})[1]
    reports_out = ({(r.registry_file, r.issued_to) for r in out_rows} >= {(FILE, u2), (OTHER, u1)}
                   and [r.registry_file for r in overdue_rows if r.registry_file in (FILE, OTHER)] == [FILE]
                   and [r.registry_file for r in today_rows if r.registry_file in (FILE, OTHER)] == [OTHER]
                   and [r.registry_file for r in by_holder] == [FILE] and overdue_rows[0].days_overdue >= 1)

    # 4. Bring Up today
    as_(u1)
    bu_refused = refused(lambda: rf().set_bring_up(nowdate(), "x"))  # not the holder
    as_(u2); rf().set_bring_up(nowdate(), "Check if the Board approved the paper")
    as_("Administrator"); n = len(sent)
    bu = frappe.get_doc("Notification", "File Bring Up")
    due = bu.get_documents_for_today()
    for d in due: bu.send(d)
    bu_sent = [s for s in sent[n:] if FILE in (s[1] or "")]
    check(4, "Bring Up set for today: the reminder goes to the user and Registry (others cannot set it)",
          bu_refused and FILE in [d.name for d in due] and bu_sent and u2 in bu_sent[0][0] and reg in bu_sent[0][0],
          f"[{bu_sent[0][1] if bu_sent else None}]")

    # 5. Put away, Registry records the return to the shelf
    as_(u1); pa_refused = refused(lambda: rf().mark_put_away())
    as_(u2); n = len(sent); rf().mark_put_away("Done with it")
    pa_told = told(reg, n); f = rf(); pa_flag = f.put_away_requested and f.put_away_by == u2
    as_(u2); u2_return = refused(lambda: rf().return_file())
    as_(reg); rf().return_file("Collected from office")
    f = rf(); last = frappe.get_doc("File Movement", mv2)
    check(5, "User marks it Put Away, Registry is told and records the return; location is back in Registry",
          pa_refused and pa_flag and pa_told and u2_return and not f.holder and not f.current_movement
          and not f.put_away_requested and not f.is_overdue and f.current_location == "Registry"
          and last.status == "Returned" and last.received_by == reg, f"[{f.current_location}]")

    # 6. Reports match steps 1-5
    out_after = {r.registry_file for r in report("all")[1]}
    overdue_after = {r.registry_file for r in report("overdue")[1]}
    check(6, "Files Out, Overdue and Due Today reports match what was done (before and after the return)",
          reports_out and FILE not in out_after and OTHER in out_after and FILE not in overdue_after,
          f"[while out: {len(out_rows)} out, {len(overdue_rows)} overdue, {len(today_rows)} due today; after: {sorted(out_after)}]")

    as_(u1)
    check("6b", "General Staff cannot issue files or create movements directly",
          refused(lambda: frappe.get_doc("Registry File", "HEA/101/1/5").issue_file(u1))
          and not frappe.has_permission("File Movement", "create"))

try:
    run()
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()
    frappe.db.commit = real_commit
print("ALL PASS" if all(res) and len(res) == 7 else f"{res.count(False)} FAILED of {len(res)}")
print("after rollback: movements", frappe.db.count("File Movement"), "requests", frappe.db.count("File Request"),
      "| holder of HEA/101/1/3:", frappe.db.get_value("Registry File", FILE, "holder"),
      "| test user left:", bool(frappe.db.exists("User", "t.mwansa@test.local")))
frappe.destroy()
