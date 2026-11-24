import frappe
from frappe.utils import add_days, getdate, nowdate
frappe.init(site="dev.local", sites_path="."); frappe.connect()
frappe.set_user("Administrator")
res = []
def check(n, desc, ok, detail=""):
    res.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {n}. {desc}  {detail}")

# Keep everything inside one transaction that is rolled back at the end.
real_commit = frappe.db.commit
frappe.db.commit = lambda *a, **k: None
sent = []  # (users, subject) for every in-system notification
import frappe.email.doctype.notification.notification as notif_mod
notif_mod.enqueue_create_notification = lambda users, doc, **k: sent.append((users if isinstance(users, list) else [u.strip() for u in users.split(",")], doc.get("subject")))
def told(user, since):
    return [s for u, s in sent[since:] if user in u]

from frappe.model.workflow import apply_workflow
QA, LEGAL, FILE = "Quality Assurance - HEA", "Legal - HEA", "HEA/101/1/2"

def run():
    def user(email, role):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0,
                        "roles": [{"role": role}]}).insert(ignore_permissions=True)
        return email
    reg = user("t.registry@test.local", "Registry Staff")
    head = user("t.qahead@test.local", "Departmental Head")
    off = user("t.officer@test.local", "General Staff")
    mgmt = user("t.mgmt@test.local", "Management and Authorised Auditors")
    other_head = user("t.legalhead@test.local", "Departmental Head")
    other = user("t.other@test.local", "General Staff")
    st = frappe.get_single("Registry Settings")
    st.append("department_heads", {"department": QA, "head": head})
    st.append("department_heads", {"department": LEGAL, "head": other_head})
    st.append("escalation_contacts", {"user": mgmt})
    st.save()

    def act(u, doc, action, **prep):
        frappe.set_user(u)
        d = frappe.get_doc("Correspondence", doc.name if hasattr(doc, "name") else doc)
        if prep: d.prepare_action(action, prep)
        apply_workflow(d, action)
        return frappe.get_doc("Correspondence", d.name)

    def refused(fn):
        try: fn(); return False
        except (frappe.ValidationError, frappe.PermissionError): return True

    def new(direction="Incoming", **kw):
        frappe.set_user(reg)
        return frappe.get_doc({"doctype": "Correspondence", "direction": direction, "sender": "University of Zambia",
            "subject": "Request for accreditation visit", "department": QA, "urgency": "Urgent",
            "registry_file": FILE, **kw}).insert()

    # 1. Full chain with four users
    a = new()
    due_ok = getdate(a.due_date) == getdate(add_days(nowdate(), 3)) and a.workflow_state == "Registered"
    stages, notified = [], []
    n = len(sent); a = act(reg, a, "Assign to Department"); stages.append(a.workflow_state); notified.append(bool(told(head, n)))
    n = len(sent); a = act(head, a, "Assign to Officer", assigned_officer=off); stages.append(a.workflow_state); notified.append(bool(told(off, n)))
    n = len(sent); a = act(off, a, "Record Action", action_taken="Visit scheduled for next month; letter drafted."); stages.append(a.workflow_state); notified.append(bool(told(head, n)))
    a = act(head, a, "Start Review"); stages.append(a.workflow_state)
    n = len(sent); a = act(head, a, "Approve"); stages.append(a.workflow_state); notified.append(bool(told(reg, n)))
    a = act(reg, a, "File"); stages.append(a.workflow_state)
    a = act(reg, a, "Close"); stages.append(a.workflow_state)
    check(1, "Incoming letter goes through every stage; head, officer, head, Registry each notified at their step",
          due_ok and stages == ["Assigned to Department", "Assigned to Officer", "Action Taken", "Under Review", "Approved", "Filed", "Closed"]
          and all(notified), f"[due {a.due_date} (Urgent = 3 days); notified {notified}]")

    # 2. Nobody moves a stage that is not theirs
    b = act(reg, new(), "Assign to Department")
    r = [refused(lambda: act(other_head, b, "Assign to Officer", assigned_officer=other)),  # head of another department
         refused(lambda: act(off, b, "Assign to Officer", assigned_officer=off))]            # an officer
    b = act(head, b, "Assign to Officer", assigned_officer=off)
    r += [refused(lambda: act(other, b, "Record Action", action_taken="x")),                  # staff not assigned
          refused(lambda: act(head, b, "Approve"))]                                           # skipping stages
    frappe.set_user(off); d = frappe.get_doc("Correspondence", b.name); d.subject = "Changed by officer"
    r.append(refused(d.save))                                                                 # officer editing the registration
    frappe.set_user(head); d = frappe.get_doc("Correspondence", b.name); d.sender = "Someone else"
    r.append(refused(d.save))
    check(2, "Other department's head, officers, unassigned staff and skipped stages are refused; heads and officers cannot edit the registration", all(r), f"{r}")

    # 3. Send back with a comment, officer resubmits
    b = act(off, b, "Record Action", action_taken="First draft reply")
    b = act(head, b, "Start Review")
    no_reason = refused(lambda: act(head, b, "Send Back"))
    n = len(sent)
    b = act(head, b, "Send Back", reason="Add the visit dates and copy the Registrar.")
    officer_told = told(off, n)
    frappe.set_user(off); seen = frappe.get_doc("Correspondence", b.name).send_back_reason
    comment = frappe.db.exists("Comment", {"reference_name": b.name, "comment_type": "Comment", "content": ["like", "%visit dates%"]})
    b = act(off, b, "Record Action", action_taken="Reply updated with dates; Registrar copied")
    b = act(head, b, "Start Review"); b = act(head, b, "Approve")
    check(3, "Send Back needs a reason; officer is notified, sees the comment and resubmits; head approves",
          no_reason and officer_told and seen == "Add the visit dates and copy the Registrar." and comment and b.workflow_state == "Approved")

    # 4. Internal memo follows the same chain
    c = new("Internal", sender="Director, Corporate Services", recipient="Director, Quality Assurance",
            sender_department="Corporate Services - HEA", subject="Memo: staff for accreditation visit")
    for u, action, prep in [(reg, "Assign to Department", {}), (head, "Assign to Officer", {"assigned_officer": off}),
                            (off, "Record Action", {"action_taken": "Two officers nominated"}), (head, "Start Review", {}),
                            (head, "Approve", {}), (reg, "File", {})]:
        c = act(u, c, action, **prep)
    out = new("Outgoing", recipient="Copperbelt University", subject="Visit dates")
    out_refused = refused(lambda: act(reg, out, "Assign to Department"))
    out = act(reg, out, "File")
    check(4, "Internal memo follows the same chain to Filed; outgoing letter goes straight to Filed",
          c.workflow_state == "Filed" and out_refused and out.workflow_state == "Filed", f"[{c.name}]")

    # 5. Overdue item escalates to the head, then Management, and shows in the overdue report
    e = act(reg, new(subject="Complaint about programme accreditation"), "Assign to Department")
    e = act(head, e, "Assign to Officer", assigned_officer=off)
    frappe.set_user(head); frappe.get_doc("Correspondence", e.name).change_due_date(add_days(nowdate(), -5), "test")
    frappe.set_user("Administrator")
    from hea.registry.escalation import escalate_overdue
    first = escalate_overdue()
    lvl1 = frappe.db.get_value("Correspondence", e.name, "escalation_level")
    head_log = frappe.db.exists("Notification Log", {"for_user": head, "document_name": e.name})
    again = escalate_overdue()  # same day: nothing more
    frappe.db.set_value("Correspondence", e.name, "escalated_on", add_days(nowdate(), -3))
    escalate_overdue()
    lvl2 = frappe.db.get_value("Correspondence", e.name, "escalation_level")
    mgmt_log = frappe.db.exists("Notification Log", {"for_user": mgmt, "document_name": e.name})
    from hea.registry.report.pending_correspondence.pending_correspondence import execute
    _c, rows, _m, _ch, summary = execute({"overdue_only": 1})
    row = next((x for x in rows if x["name"] == e.name), None)
    frappe.set_user(head)
    d = frappe.get_doc("Correspondence", e.name); d.due_date = add_days(nowdate(), 1); d.escalation_level = None; d.save()
    frappe.set_user("Administrator")
    reminder = e.name in [x.name for x in frappe.get_doc("Notification", "Correspondence Due Soon").get_documents_for_today()]
    check(5, "Overdue item: head told, then Management after 3 days; in overdue report; due-tomorrow reminder picks it up",
          e.name in first and lvl1 == "Departmental Head" and head_log and e.name not in again and lvl2 == "Management"
          and mgmt_log and row and row["days_overdue"] == 5 and row["with"] == off and reminder,
          f"[{lvl1} -> {lvl2}; {row and row['days_overdue']} days overdue; summary {[(s['label'], s['value']) for s in summary]}]")

    # 6. History: every stage change with user and time
    versions = frappe.get_all("Version", {"ref_doctype": "Correspondence", "docname": a.name}, ["owner", "creation", "data"], order_by="creation")
    import json
    moves = []
    for v in versions:
        for field, old, new_ in json.loads(v.data).get("changed", []):
            if field == "workflow_state": moves.append((old, new_, v.owner))
    expected = [("Registered", "Assigned to Department", reg), ("Assigned to Department", "Assigned to Officer", head),
                ("Assigned to Officer", "Action Taken", off), ("Action Taken", "Under Review", head),
                ("Under Review", "Approved", head), ("Approved", "Filed", reg), ("Filed", "Closed", reg)]
    check(6, "Every stage change is in the item's history with user and time", moves == expected and all(v.creation for v in versions),
          f"[{len(moves)} stage changes recorded]")

    frappe.set_user("Administrator")
    for dt in ("Dashboard Chart", "Number Card"):
        pass
    from frappe.desk.doctype.number_card.number_card import get_result
    import json as _j
    def card(nm):
        c = frappe.get_doc("Number Card", nm)
        dyn = [[a, b, op, nowdate() if v == "frappe.datetime.get_today()" else v] for a, b, op, v in _j.loads(c.dynamic_filters_json or "[]")]
        return get_result(c, _j.loads(c.filters_json) + dyn)
    cards = {nm: card(nm) for nm in ("Pending Correspondence", "Overdue Correspondence")}
    check("6b", "Number cards: 1 pending, 0 overdue (the overdue item was given a new due date)", cards == {"Pending Correspondence": 1, "Overdue Correspondence": 0}, f"{cards}")

try:
    run()
finally:
    frappe.db.rollback()
    frappe.db.commit = real_commit
print("ALL PASS" if all(res) and len(res) == 7 else f"{res.count(False)} FAILED of {len(res)}")
print("after rollback: correspondence", frappe.db.count("Correspondence"), "| heads in settings:",
      len(frappe.get_single("Registry Settings").department_heads), "| test user left:", bool(frappe.db.exists("User", "t.qahead@test.local")))
frappe.destroy()
