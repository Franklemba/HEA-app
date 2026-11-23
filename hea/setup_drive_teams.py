import frappe

# ---------------- CONFIG ----------------
# Admins (access level 2) on EVERY team. Administrator is added automatically anyway.
GLOBAL_ADMINS = ["Administrator"]   # e.g. add "frank@innovativedynamicsltd.com"

TEAMS = {
    "HEA Team": {
        "departments": "ALL",
        "admins": [],
        "extra_members": [],
    },
    "Corporate Services Team": {
        "departments": ["Corporate Services - HEA"],
        "admins": [],
        "extra_members": [],
    },
    "Director General's Office Team": {
        "departments": ["Director Generals Office - HEA"],
        "admins": [],
        "extra_members": [],
    },
    "Quality Assurance Team": {
        "departments": ["Quality Assurance - HEA"],
        "admins": [],
        "extra_members": [],
    },
}
# -----------------------------------------


def _department_users(departments):
    filters = {"status": "Active", "user_id": ["is", "set"]}
    if departments != "ALL":
        filters["department"] = ["in", departments]
    return frappe.get_all("Employee", filters=filters, pluck="user_id")


def _get_or_create_team(title, dry_run):
    existing = frappe.get_all("Drive Team", filters={"title": title, "personal": 0}, pluck="name")
    if existing:
        return existing[0], False
    if dry_run:
        return None, True
    team = frappe.get_doc({"doctype": "Drive Team", "title": title, "personal": 0})
    team.insert(ignore_permissions=True)  # after_insert creates root folder + disk dirs
    return team.name, True


def execute(dry_run=True):
    frappe.set_user("Administrator")

    for title, cfg in TEAMS.items():
        # user -> access level (1 = member, 2 = admin)
        wanted = {}
        for u in _department_users(cfg["departments"]):
            wanted[u] = 1
        for u in cfg.get("extra_members", []):
            wanted[u] = 1
        for u in GLOBAL_ADMINS + cfg.get("admins", []):
            wanted[u] = 2

        invalid = [u for u in wanted if not frappe.db.exists("User", {"name": u, "enabled": 1})]
        for u in invalid:
            wanted.pop(u)

        name, created = _get_or_create_team(title, dry_run)
        status = "NEW" if created else f"EXISTS ({name})"
        print(f"\n=== {title} - {status} ===")
        if invalid:
            print("  skipped (no such user / disabled):", invalid)

        team, current = None, {}
        if name:
            team = frappe.get_doc("Drive Team", name)
            current = {m.user: m for m in team.users}

        to_add = [u for u in wanted if u not in current]
        to_promote = [u for u in wanted if u in current and wanted[u] > (current[u].access_level or 0)]

        print(f"  wanted: {len(wanted)} | already in: {len(wanted) - len(to_add)} "
              f"| to add: {len(to_add)} | to promote: {len(to_promote)}")
        for u in to_add:
            print(f"    + {u}  (level {wanted[u]})")
        for u in to_promote:
            print(f"    ^ {u}  -> level {wanted[u]}")

        if not dry_run and team and (to_add or to_promote):
            for u in to_add:
                team.append("users", {"user": u, "access_level": wanted[u]})
            for u in to_promote:
                current[u].access_level = wanted[u]
            team.save(ignore_permissions=True)

    if dry_run:
        print("\nDRY RUN - nothing was saved. Run again with dry_run=False to apply.")
    else:
        frappe.db.commit()
        print("\nDone - changes committed.")