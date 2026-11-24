import frappe, random, re
frappe.init(site="dev.local", sites_path="."); frappe.connect()
frappe.set_user("Administrator")
raw=re.sub(r'\s+',' ',open('/tmp/hea_index.txt').read().upper())
res=[]
def check(n,desc,ok,detail=""):
    res.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {n}. {desc}  {detail}")
subj=frappe.db.count("File Subject",{"is_group":0}); files=frappe.db.count("Registry File")
check(1,"Subjects and files in the system equal the index (87, 1205)", subj==87 and files==1205, f"[{subj}, {files}]")
random.seed(11)
sample=random.sample(frappe.get_all("Registry File",filters={"needs_review":0},fields=["name","file_title"]),20)
miss=[s.name for s in sample if s.name.upper() not in raw or s.file_title.upper() not in raw]
check("1b","20 random files: number and title found exactly in the Word index", not miss, f"misses={miss}")
def user(email,role):
    u=frappe.get_doc({"doctype":"User","email":email,"first_name":role,"send_welcome_email":0,"roles":[{"role":role}]})
    u.insert(ignore_permissions=True); return email
staff=user("t.registry@test.local","Registry Staff"); gen=user("t.general@test.local","General Staff"); off=user("t.officer@test.local","Documentation and Registry Officer")
frappe.set_user(staff)
last=frappe.db.sql("select max(file_sequence) from `tabRegistry File` where file_subject='101/4'")[0][0]
f=frappe.get_doc({"doctype":"Registry File","file_subject":"101/4","file_title":"TEST CIRCULAR ON RECORDS DIGITISATION"}).insert()
check(2,"Registry Staff open a file under 101/4 and get the next number", f.name==f"HEA/101/4/{last+1}", f"[{f.name}; highest before: HEA/101/4/{last}]")
s=frappe.get_doc({"doctype":"File Subject","subject_name":"TEST DIGITAL RECORDS","subject_type":"Domestic"}).insert()
f2=frappe.get_doc({"doctype":"Registry File","file_subject":s.name,"file_title":"TEST DIGITAL RECORDS POLICY"}).insert()
check(3,"Registry Staff add a domestic subject: next code, first file opens under it", s.name=="101/24" and f2.name=="HEA/101/24/1", f"[{s.name} '{s.subject_name}' under {s.parent_file_subject}; {f2.name}]")
refused=[]
for t in ["Miscellaneous","General Correspondence 2026"]:
    try: frappe.get_doc({"doctype":"Registry File","file_subject":"101/4","file_title":t}).insert(); refused.append(False)
    except frappe.ValidationError: refused.append(True)
check(4,"Vague titles ('Miscellaneous', 'General Correspondence 2026') are refused", all(refused))
f.close_file("Test closure"); f.reload(); closed=f.status=="Closed" and f.closed_on and f.closed_by==staff
frappe.set_user(gen)
try: frappe.get_doc("Registry File",f2.name).close_file("x"); denied=False
except frappe.PermissionError: denied=True
gen_read=frappe.has_permission("Registry File","read"); gen_create=frappe.has_permission("Registry File","create")
frappe.set_user(staff); f.reopen_file("Test reopen"); f.reload()
check(5,"Registry close and reopen a file; General Staff can read, cannot open or close", closed and f.status=="Open" and denied and gen_read and not gen_create)
check("5b","Delete: Registry Officer allowed, Registry Staff refused", frappe.has_permission("Registry File","delete",user=off) and not frappe.has_permission("Registry File","delete",user=staff))
from hea.registry.report.file_index.file_index import execute
_,rows=execute({}); nums=[r["number"] for r in rows]
check(6,"File Index report lists the new subject and its file", "101/24" in nums and "HEA/101/24/1" in nums and f.name in nums, f"[{len(rows)} rows = 88 subjects + 1207 files]" if len(rows)==1295 else f"[{len(rows)} rows]")
frappe.db.rollback()
print("ALL PASS" if all(res) else f"{res.count(False)} FAILED")
print("after rollback: files", frappe.db.count("Registry File"), "test user left:", bool(frappe.db.exists("User","t.registry@test.local")))
frappe.destroy()
