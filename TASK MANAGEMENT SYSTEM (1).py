#!/usr/bin/env python3
"""TASK MANAGEMENT SYSTEM (console) v6 - no imports
Every menu is fully functional. Enter 0 in any menu to go back.

TASKS     Add / View / Task details / Edit / Duplicate / Delete
PROGRESS  Update status / Today's agenda / Weekly planner / Calendar / Reschedule overdue
TOOLS     Search / Statistics / Export / Backup & restore / Settings / Help

Files (in the folder you run the script from):
  tasks.txt, settings.txt, tasks_backup.txt, report.txt, tasks.csv
Because nothing is imported, the script asks for today's date when it starts."""

DATA_FILE = "tasks.txt"
SETTINGS_FILE = "settings.txt"
BACKUP_FILE = "tasks_backup.txt"
REPORT_FILE = "report.txt"
CSV_FILE = "tasks.csv"
WIDTH = 64

DEFAULT_SORT = 0          # index into SORTERS
DEFAULT_PRIORITY = "Medium"
SHOW_REMINDERS = True

PRIORITIES = ["High", "Medium", "Low"]
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
BASE_CATEGORIES = ["General", "Work", "Personal", "Study", "Shopping"]
CATEGORIES = list(BASE_CATEGORIES)   # base + custom ones saved in settings
STATUSES = ["To Do", "In Progress", "Done"]
STATUS_MARK = {"To Do": "[ ]", "In Progress": "[~]", "Done": "[x]"}
REPEATS = ["Daily", "Weekly", "Monthly"]

TODAY = "2000-01-01"  # replaced at start-up by ask_today()

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

FIELD_LABELS = {
    "subject": "Subject / course",
    "time": "Time",
    "location": "Location",
    "people": "With / participants",
}

TASK_TYPES = {
    "Assignment": {"category": "Study", "title": "Assignment title: ",
                   "fields": ["subject"], "checklist": True},
    "Activity": {"category": "Personal", "title": "Activity name: ",
                 "fields": ["time", "location"], "checklist": False},
    "Exam / Quiz": {"category": "Study", "title": "Exam / quiz title: ",
                    "fields": ["subject", "time", "location"], "checklist": True},
    "Project": {"category": "Work", "title": "Project name: ",
                "fields": ["people"], "checklist": True},
    "Meeting": {"category": "Work", "title": "Meeting topic: ",
                "fields": ["time", "location", "people"], "checklist": False},
    "Event": {"category": "Personal", "title": "Event name: ",
              "fields": ["time", "location"], "checklist": False},
    "Other": {"category": "General", "title": "Title: ",
              "fields": [], "checklist": False},
}


# ---------- Date helpers (no datetime module) ----------
def days_in_month(y, m):
    if m == 2:
        return 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    return 30 if m in (4, 6, 9, 11) else 31


def valid_date(s):
    parts = s.split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return False
    if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
        return False
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    return 1 <= m <= 12 and 1 <= d <= days_in_month(y, m)


def to_ordinal(s):
    y, m, d = (int(p) for p in s.split("-"))
    y -= m <= 2
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe


def from_ordinal(n):
    era = n // 146097
    doe = n - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    y += m <= 2
    return f"{y:04d}-{m:02d}-{d:02d}"


def add_days(s, n):
    return from_ordinal(to_ordinal(s) + n)


def add_month(s):
    y, m, d = (int(p) for p in s.split("-"))
    y += m == 12
    m = m % 12 + 1
    return f"{y:04d}-{m:02d}-{min(d, days_in_month(y, m)):02d}"


def valid_time(s):
    parts = s.split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return False
    return len(parts[0]) in (1, 2) and len(parts[1]) == 2 and int(parts[0]) < 24 and int(parts[1]) < 60


def weekday(s):
    """0 = Sunday ... 6 = Saturday."""
    return (to_ordinal(s) + 3) % 7


def ask_today():
    global TODAY
    while True:
        raw = input("Today's date (YYYY-MM-DD): ").strip()
        if valid_date(raw):
            TODAY = raw
            return
        print("Invalid date. Use the format YYYY-MM-DD.")


# ---------- Screen helpers ----------
def rule(char="-"):
    return "+" + char * (WIDTH - 2) + "+"


def row(text="", align="left"):
    inner = WIDTH - 4
    text = text[:inner]
    text = text.center(inner) if align == "center" else text.ljust(inner)
    return "| " + text + " |"


def heading(title):
    print("\n" + f"== {title} ".ljust(WIDTH, "="))


def progress_bar(done, total, width=20):
    filled = (width * done // total) if total else 0
    pct = (done * 100 // total) if total else 0
    return f"[{'#' * filled}{'-' * (width - filled)}] {pct:>3}%"


def pause():
    input("\nPress Enter to continue...")


# ---------- Settings (saved to settings.txt) ----------
def load_settings():
    global DEFAULT_SORT, DEFAULT_PRIORITY, SHOW_REMINDERS
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError:
        return
    for line in lines:
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key == "sort" and val.isdigit():
            DEFAULT_SORT = min(int(val), len(SORTERS) - 1)
        elif key == "priority" and val in PRIORITIES:
            DEFAULT_PRIORITY = val
        elif key == "reminders":
            SHOW_REMINDERS = val == "1"
        elif key == "cats":
            for c in val.split(","):
                c = c.strip()
                if c and c not in CATEGORIES:
                    CATEGORIES.append(c)


def save_settings():
    custom = [c for c in CATEGORIES if c not in BASE_CATEGORIES]
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.write(f"sort={DEFAULT_SORT}\n")
        f.write(f"priority={DEFAULT_PRIORITY}\n")
        f.write(f"reminders={'1' if SHOW_REMINDERS else '0'}\n")
        f.write(f"cats={','.join(custom)}\n")


# ---------- Storage (plain text, no json) ----------
TEXT_KEYS = ["type", "title", "subject", "time", "location", "people", "notes",
             "priority", "category", "due", "repeat", "status", "created"]
NULLABLE = ("time", "due", "repeat")


def esc(s):
    return s.replace("\\", "\\\\").replace("\n", "\\n")


def unesc(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append("\n" if s[i + 1] == "n" else s[i + 1])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def blank_task():
    return {"id": 0, "type": "Other", "title": "", "subject": "", "time": None,
            "location": "", "people": "", "notes": "", "priority": "Medium",
            "category": "General", "due": None, "repeat": None, "status": "To Do",
            "done": False, "subtasks": [], "created": ""}


def load_tasks(path=DATA_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError:
        return None
    tasks, cur = [], None
    for line in lines:
        if line == "---":
            if cur:
                tasks.append(cur)
            cur = blank_task()
            continue
        if cur is None or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key == "id":
            cur["id"] = int(val) if val.isdigit() else 0
        elif key == "sub":
            cur["subtasks"].append({"text": unesc(val[2:]), "done": val[:1] == "1"})
        elif key == "next_created":
            cur["next_created"] = True
        elif key in TEXT_KEYS:
            val = unesc(val)
            cur[key] = (val or None) if key in NULLABLE else val
    if cur:
        tasks.append(cur)
    for t in tasks:
        t["done"] = t["status"] == "Done"
        if t["category"] not in CATEGORIES:
            CATEGORIES.append(t["category"])
    if not ids_are_clean(tasks):   # missing or duplicate IDs in the file
        renumber(tasks)
    return tasks


def save_tasks(tasks, path=DATA_FILE):
    out = []
    for t in tasks:
        out.append("---")
        out.append(f"id={t['id']}")
        for k in TEXT_KEYS:
            out.append(f"{k}={esc(t.get(k) or '')}")
        if t.get("next_created"):
            out.append("next_created=1")
        for s in t["subtasks"]:
            out.append(f"sub={'1' if s['done'] else '0'}|{esc(s['text'])}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def next_id(tasks):
    return max((t["id"] for t in tasks), default=0) + 1


def renumber(tasks):
    """Give every task a clean ID: 1, 2, 3, ... in list order.
    Returns True if any ID changed."""
    changed = False
    for i, t in enumerate(tasks, 1):
        if t["id"] != i:
            t["id"] = i
            changed = True
    return changed


def ids_are_clean(tasks):
    ids = [t["id"] for t in tasks]
    return len(set(ids)) == len(ids) and 0 not in ids


def parse_id(raw):
    """'3', '#3', 'id 3' -> '3' (digits only), else ''."""
    raw = raw.strip().lstrip("#").strip()
    if raw.lower().startswith("id"):
        raw = raw[2:].strip().lstrip("#").strip()
    return raw


# ---------- Generic menu helpers ----------
def choose(title, options, back_label="Back"):
    """Numbered menu. Returns the 0-based index of the choice, or None for 'back'."""
    heading(title)
    for i, label in enumerate(options, 1):
        print(f"  {i:>2})  {label}")
    print(f"  {'0':>2})  <- {back_label}")
    print("-" * WIDTH)
    while True:
        raw = input("Choice: ").strip()
        if raw == "0":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"Please enter a number from 0 to {len(options)}.")


def confirm(question):
    return input(f"{question} (y/N): ").strip().lower() == "y"


# ---------- Input helpers ----------
def ask_priority(default="Medium"):
    idx = choose(f"Priority (current/default: {default})", PRIORITIES,
                 back_label=f"Keep {default}")
    return default if idx is None else PRIORITIES[idx]


def ask_category(default="General"):
    cats = CATEGORIES + ["Custom..."]
    idx = choose(f"Category (current/default: {default})", cats, back_label=f"Keep {default}")
    if idx is None:
        return default
    if cats[idx] == "Custom...":
        name = input("Category name: ").strip().title()
        if not name:
            return default
        if name not in CATEGORIES:
            CATEGORIES.append(name)
            save_settings()
        return name
    return cats[idx]


def ask_type(default="Other"):
    names = list(TASK_TYPES) + ["Custom..."]
    idx = choose(f"Type (current: {default})", names, back_label=f"Keep {default}")
    if idx is None:
        return default
    if names[idx] == "Custom...":
        name = input("Type name: ").strip()
        return name.title() if name else default
    return names[idx]


def ask_due_date(current=None):
    options = ["Today", "Tomorrow", "In 1 week", "Pick a date (YYYY-MM-DD)", "No due date"]
    idx = choose(f"Due date (current: {current or 'none'})", options,
                 back_label="Keep current" if current else "No due date")
    if idx is None:
        return current
    if idx == 0:
        return TODAY
    if idx == 1:
        return add_days(TODAY, 1)
    if idx == 2:
        return add_days(TODAY, 7)
    if idx == 4:
        return None
    return ask_date_text(current)


def ask_date_text(current=None):
    while True:
        raw = input("Date (YYYY-MM-DD, Enter = cancel): ").strip()
        if not raw:
            return current
        if valid_date(raw):
            return raw
        print("Invalid date. Use the format YYYY-MM-DD.")


def ask_time(current=None):
    hint = f" (current: {current}, '-' = clear)" if current else ""
    while True:
        raw = input(f"Time HH:MM, 24-hour{hint} (Enter = skip/keep): ").strip()
        if not raw:
            return current
        if raw == "-":
            return None
        if valid_time(raw):
            h, m = raw.split(":")
            return f"{int(h):02d}:{m}"
        print("Invalid time. Use HH:MM, for example 14:30.")


def ask_repeat(current=None):
    idx = choose(f"Repeat (current: {current or 'none'})", REPEATS,
                 back_label=f"Keep {current}" if current else "No repeat")
    return current if idx is None else REPEATS[idx]


def ask_checklist():
    items = []
    print("Add checklist / subtasks (press Enter on an empty line to finish).")
    while True:
        text = input(f"  Subtask {len(items) + 1}: ").strip()
        if not text:
            return items
        items.append({"text": text, "done": False})


def ask_task(tasks, prompt="Task ID: "):
    raw = parse_id(input(prompt))
    if not raw.isdigit():
        print("Please enter a valid task ID number (see the ID column).")
        return None
    task = next((t for t in tasks if t["id"] == int(raw)), None)
    if task is None:
        print(f"No task with ID {raw}.")
    return task


def ask_task_ids(tasks):
    """Accepts '3', '1,4,7' or '2-5'. Returns the matching tasks."""
    raw = input("Task ID(s) (e.g. 3 or 1,4,7 or 2-5): ").strip().replace("#", "")
    ids = set()
    try:
        for part in raw.replace(" ", "").split(","):
            if "-" in part:
                a, b = (int(x) for x in part.split("-"))
                ids.update(range(min(a, b), max(a, b) + 1))
            elif part:
                ids.add(int(part))
    except ValueError:
        print("Invalid format. Use IDs like 3, 1,4,7 or 2-5.")
        return []
    found = [t for t in tasks if t["id"] in ids]
    missing = ids - {t["id"] for t in found}
    if missing:
        print(f"Not found: {sorted(missing)}")
    return found


# ---------- Dates / status logic ----------
def next_due(due, repeat):
    if repeat == "Daily":
        return add_days(due, 1)
    if repeat == "Weekly":
        return add_days(due, 7)
    return add_month(due)


def set_status(tasks, task, status):
    """Change a task's status. Completing a repeating task creates the next one."""
    task["status"] = status
    task["done"] = status == "Done"
    print(f"Task #{task['id']} -> {status}.")
    if status == "Done" and task.get("repeat") and task.get("due") and not task.get("next_created"):
        new = dict(task)
        new.update({
            "id": next_id(tasks),
            "status": "To Do",
            "done": False,
            "due": next_due(task["due"], task["repeat"]),
            "subtasks": [{"text": s["text"], "done": False} for s in task["subtasks"]],
            "created": TODAY,
        })
        new.pop("next_created", None)
        tasks.append(new)
        task["next_created"] = True
        print(f"  Repeats {task['repeat'].lower()}: created #{new['id']} due {new['due']}.")


def is_overdue(t):
    return not t["done"] and bool(t["due"]) and t["due"] < TODAY


def due_status(task):
    if not task["due"] or task["done"]:
        return ""
    days = to_ordinal(task["due"]) - to_ordinal(TODAY)
    if days < 0:
        return f"OVERDUE by {-days}d"
    if days == 0:
        return "due TODAY"
    return f"in {days}d"


# ---------- Display ----------
def subtask_progress(t):
    subs = t["subtasks"]
    return f"{sum(s['done'] for s in subs)}/{len(subs)}" if subs else ""


def print_tasks(tasks, title="Tasks"):
    heading(f"{title} ({len(tasks)})")
    if not tasks:
        print("  Nothing to show.")
        return
    print(f"{'ID':<5}{'Status':<15} {'Type':<12} {'Priority':<9} {'Category':<10} "
          f"{'Due':<11} {'Deadline':<16} Title")
    print("-" * 105)
    for t in tasks:
        status = f"{STATUS_MARK.get(t['status'], '[ ]')} {t['status']}"
        print(f"{t['id']:<5}{status:<15} {t['type'][:11]:<12} {t['priority']:<9} "
              f"{t['category'][:9]:<10} {(t['due'] or '-'):<11} {due_status(t):<16} {t['title']}")
        details = []
        if t["subject"]:
            details.append(f"subject: {t['subject']}")
        if t["time"]:
            details.append(f"time: {t['time']}")
        if t["location"]:
            details.append(f"at: {t['location']}")
        if t["people"]:
            details.append(f"with: {t['people']}")
        if t["repeat"]:
            details.append(f"repeats {t['repeat'].lower()}")
        if t["subtasks"]:
            details.append(f"checklist {subtask_progress(t)}")
        if t["notes"]:
            details.append(f"notes: {t['notes']}")
        if details:
            print(f"{'':<4} " + " | ".join(details))
        for s in t["subtasks"]:
            print(f"{'':<7}{'[x]' if s['done'] else '[ ]'} {s['text']}")


SORTERS = {
    "Priority, then due date": lambda t: (t["done"], PRIORITY_ORDER.get(t["priority"], 1), t["due"] or "9999"),
    "Due date": lambda t: (t["done"], t["due"] or "9999", PRIORITY_ORDER.get(t["priority"], 1)),
    "Title (A-Z)": lambda t: t["title"].lower(),
    "Newest first": lambda t: (t.get("created", ""), t["id"]),
}


def sort_choice(tasks):
    names = list(SORTERS)
    idx = choose("Sort by", names, back_label=f"Default ({names[DEFAULT_SORT]})")
    name = names[DEFAULT_SORT] if idx is None else names[idx]
    return sorted(tasks, key=SORTERS[name], reverse=(name == "Newest first"))


# ---------- 1. Add ----------
def build_task(tasks, task_type, spec):
    title = input(spec["title"]).strip()
    if not title:
        print("Title cannot be empty.")
        return None
    task = blank_task()
    task.update({"id": next_id(tasks), "type": task_type, "title": title,
                 "category": spec["category"], "created": TODAY})
    for field in spec["fields"]:
        if field == "time":
            task["time"] = ask_time()
        else:
            task[field] = input(f"{FIELD_LABELS[field]} (Enter = skip): ").strip()
    task["notes"] = input("Notes (Enter = skip): ").strip()
    task["priority"] = ask_priority(DEFAULT_PRIORITY)
    task["category"] = ask_category(spec["category"])
    task["due"] = ask_due_date()
    if task["due"]:
        task["repeat"] = ask_repeat()
    if spec["checklist"]:
        task["subtasks"] = ask_checklist()
    return task


def add_menu(tasks):
    while True:
        names = list(TASK_TYPES) + ["Custom..."]
        idx = choose("What do you want to add?", names)
        if idx is None:
            return
        if names[idx] == "Custom...":
            task_type = input("Type name (e.g. Homework, Workout): ").strip().title()
            if not task_type:
                continue
            spec = {"category": "General", "title": "Title: ",
                    "fields": ["time", "location"], "checklist": True}
        else:
            task_type = names[idx]
            spec = TASK_TYPES[task_type]
        task = build_task(tasks, task_type, spec)
        if task is None:
            continue
        tasks.append(task)
        save_tasks(tasks)
        print(f"Added {task_type.lower()} #{task['id']}: {task['title']}")
        if not confirm("Add another?"):
            return


# ---------- 2. View ----------
def view_menu(tasks):
    week_end = add_days(TODAY, 7)
    views = [
        ("All", lambda t: True),
        ("Pending (To Do + In Progress)", lambda t: not t["done"]),
        ("To Do", lambda t: t["status"] == "To Do"),
        ("In Progress", lambda t: t["status"] == "In Progress"),
        ("Completed", lambda t: t["done"]),
        ("Overdue", is_overdue),
        ("Due today", lambda t: not t["done"] and t["due"] == TODAY),
        ("Due in the next 7 days",
         lambda t: not t["done"] and bool(t["due"]) and TODAY <= t["due"] <= week_end),
        ("Repeating tasks", lambda t: bool(t["repeat"])),
        ("No due date", lambda t: not t["due"]),
    ]
    groups = ["priority", "category", "type"]
    options = [v[0] for v in views] + [f"By {g}" for g in groups]
    idx = choose("View tasks", options)
    if idx is None:
        return
    if idx < len(views):
        title, test = views[idx]
        data = [t for t in tasks if test(t)]
    else:
        key = groups[idx - len(views)]
        values = sorted({t[key] for t in tasks},
                        key=lambda v: PRIORITY_ORDER.get(v, 9) if key == "priority" else v.lower())
        if not values:
            print("No tasks yet.")
            return
        c = choose(f"Which {key}?", values)
        if c is None:
            return
        data, title = [t for t in tasks if t[key] == values[c]], f"{key.title()}: {values[c]}"
    print_tasks(sort_choice(data), title)
    pause()


# ---------- 3. Task details ----------
def details_menu(tasks):
    task = ask_task(tasks)
    if not task:
        return
    while True:
        heading(f"Task #{task['id']}")
        print(f"  Title      : {task['title']}")
        print(f"  Type       : {task['type']}")
        print(f"  Status     : {STATUS_MARK.get(task['status'], '[ ]')} {task['status']}")
        print(f"  Priority   : {task['priority']}")
        print(f"  Category   : {task['category']}")
        print(f"  Due        : {task['due'] or '-'} {due_status(task)}".rstrip())
        print(f"  Repeat     : {task['repeat'] or '-'}")
        for key in ("subject", "time", "location", "people"):
            if task[key]:
                print(f"  {FIELD_LABELS[key]:<11}: {task[key]}")
        if task["notes"]:
            print(f"  Notes      : {task['notes']}")
        print(f"  Created    : {task['created'] or '-'}")
        if task["subtasks"]:
            print(f"  Checklist  : {subtask_progress(task)}")
            for s in task["subtasks"]:
                print(f"     {'[x]' if s['done'] else '[ ]'} {s['text']}")
        idx = choose("Quick actions", ["Change status", "Manage checklist", "Edit this task"],
                     back_label="Back")
        if idx is None:
            return
        if idx == 0:
            s = choose(f"Status (current: {task['status']})", STATUSES, back_label="Keep current")
            if s is not None:
                set_status(tasks, task, STATUSES[s])
        elif idx == 1:
            checklist_menu(tasks, task)
        else:
            edit_task(tasks, task)
        save_tasks(tasks)


# ---------- 4. Edit ----------
def checklist_menu(tasks, task):
    while True:
        print(f"\nChecklist for #{task['id']} {task['title']} {subtask_progress(task)}")
        if not task["subtasks"]:
            print("  (empty)")
        for i, s in enumerate(task["subtasks"], 1):
            print(f"  {i}. [{'x' if s['done'] else ' '}] {s['text']}")
        idx = choose("Checklist", ["Add subtask", "Tick / untick subtask", "Remove subtask",
                                   "Tick ALL", "Clear ticks"])
        if idx is None:
            return
        if idx == 0:
            text = input("Subtask: ").strip()
            if text:
                task["subtasks"].append({"text": text, "done": False})
        elif idx in (3, 4):
            for s in task["subtasks"]:
                s["done"] = idx == 3
        else:
            if not task["subtasks"]:
                print("No subtasks yet.")
                continue
            raw = input("Subtask number: ").strip()
            if not (raw.isdigit() and 1 <= int(raw) <= len(task["subtasks"])):
                print("Invalid number.")
                continue
            n = int(raw) - 1
            if idx == 1:
                task["subtasks"][n]["done"] = not task["subtasks"][n]["done"]
            else:
                task["subtasks"].pop(n)
        save_tasks(tasks)


def edit_task(tasks, task):
    while True:
        print(f"\nEditing #{task['id']}: {task['title']}")
        fields = [
            ("title", f"Title      [{task['title']}]"),
            ("type", f"Type       [{task['type']}]"),
            ("subject", f"Subject    [{task['subject'] or '-'}]"),
            ("time", f"Time       [{task['time'] or '-'}]"),
            ("location", f"Location   [{task['location'] or '-'}]"),
            ("people", f"With       [{task['people'] or '-'}]"),
            ("notes", f"Notes      [{task['notes'] or '-'}]"),
            ("priority", f"Priority   [{task['priority']}]"),
            ("category", f"Category   [{task['category']}]"),
            ("due", f"Due date   [{task['due'] or '-'}]"),
            ("repeat", f"Repeat     [{task['repeat'] or '-'}]"),
            ("status", f"Status     [{task['status']}]"),
            ("checklist", f"Checklist  [{subtask_progress(task) or '-'}]"),
        ]
        idx = choose("What do you want to edit?", [label for _, label in fields],
                     back_label="Done editing")
        if idx is None:
            break
        key = fields[idx][0]
        if key == "title":
            new = input("New title: ").strip()
            if new:
                task["title"] = new
        elif key == "type":
            task["type"] = ask_type(task["type"])
        elif key in ("subject", "location", "people", "notes"):
            task[key] = input(f"New {key} (blank = clear): ").strip()
        elif key == "time":
            task["time"] = ask_time(task["time"])
        elif key == "priority":
            task["priority"] = ask_priority(task["priority"])
        elif key == "category":
            task["category"] = ask_category(task["category"])
        elif key == "due":
            task["due"] = ask_due_date(task["due"])
            if not task["due"]:
                task["repeat"] = None
        elif key == "repeat":
            if not task["due"]:
                print("Set a due date first - repeating tasks need one.")
            else:
                task["repeat"] = ask_repeat(task["repeat"])
        elif key == "status":
            s = choose(f"Status (current: {task['status']})", STATUSES, back_label="Keep current")
            if s is not None:
                set_status(tasks, task, STATUSES[s])
        else:
            checklist_menu(tasks, task)
        save_tasks(tasks)
        print("Saved.")


def edit_menu(tasks):
    task = ask_task(tasks)
    if task:
        edit_task(tasks, task)


# ---------- 5. Duplicate ----------
def duplicate_menu(tasks):
    targets = ask_task_ids(tasks)
    if not targets:
        return
    idx = choose("Due date for the copies", ["Keep the same due date", "Today", "Tomorrow",
                                              "In 1 week", "Pick a date", "No due date"],
                 back_label="Cancel")
    if idx is None:
        return
    new_due = None
    if idx == 4:
        new_due = ask_date_text(None)
        if new_due is None:
            return
    for t in targets:
        new = dict(t)
        new.update({
            "id": next_id(tasks),
            "title": t["title"] + " (copy)",
            "status": "To Do",
            "done": False,
            "created": TODAY,
            "subtasks": [{"text": s["text"], "done": False} for s in t["subtasks"]],
        })
        new.pop("next_created", None)
        if idx == 1:
            new["due"] = TODAY
        elif idx == 2:
            new["due"] = add_days(TODAY, 1)
        elif idx == 3:
            new["due"] = add_days(TODAY, 7)
        elif idx == 4:
            new["due"] = new_due
        elif idx == 5:
            new["due"] = None
        if not new["due"]:
            new["repeat"] = None
        tasks.append(new)
        print(f"Copied #{t['id']} -> #{new['id']} (due {new['due'] or '-'}).")
    save_tasks(tasks)


# ---------- 6. Delete ----------
def delete_menu(tasks):
    idx = choose("Delete", [
        "Delete one or more tasks (by ID)",
        "Delete all completed tasks",
        "Delete all overdue tasks",
        "Delete ALL tasks",
    ])
    if idx is None:
        return
    if idx == 0:
        targets = ask_task_ids(tasks)
    elif idx == 1:
        targets = [t for t in tasks if t["done"]]
    elif idx == 2:
        targets = [t for t in tasks if is_overdue(t)]
    else:
        targets = list(tasks)
    if not targets:
        print("Nothing to delete.")
        return
    if idx == 3 and input("Type DELETE to confirm: ").strip() != "DELETE":
        print("Cancelled.")
        return
    if idx != 3 and not confirm(f"Delete {len(targets)} task(s)?"):
        return
    ids = {t["id"] for t in targets}
    tasks[:] = [t for t in tasks if t["id"] not in ids]
    if renumber(tasks):
        print("Remaining tasks were renumbered 1, 2, 3, ... (check the ID column).")
    save_tasks(tasks)
    print(f"Deleted {len(ids)} task(s).")


# ---------- 7. Update status ----------
def status_menu(tasks):
    idx = choose("Update status", [
        "Mark as Done (by ID)",
        "Mark as In Progress (by ID)",
        "Reopen / set to To Do (by ID)",
        "Mark ALL pending as Done",
        "Reopen ALL completed",
        "Mark all tasks due today as Done",
    ])
    if idx is None:
        return
    if idx <= 2:
        targets = ask_task_ids(tasks)
        new_status = ["Done", "In Progress", "To Do"][idx]
    elif idx == 3:
        targets = [t for t in tasks if not t["done"]]
        new_status = "Done"
        if not targets or not confirm(f"Mark {len(targets)} task(s) as Done?"):
            return
    elif idx == 4:
        targets = [t for t in tasks if t["done"]]
        new_status = "To Do"
        if not targets or not confirm(f"Reopen {len(targets)} task(s)?"):
            return
    else:
        targets = [t for t in tasks if not t["done"] and t["due"] == TODAY]
        new_status = "Done"
        if not targets or not confirm(f"Mark {len(targets)} task(s) due today as Done?"):
            return
    for t in list(targets):
        set_status(tasks, t, new_status)
    if targets:
        save_tasks(tasks)
    else:
        print("Nothing changed.")


# ---------- 8. Today's agenda ----------
def agenda_line(t):
    extra = []
    if t["time"]:
        extra.append(t["time"])
    if t["location"]:
        extra.append(f"@ {t['location']}")
    if t["due"] and not t["done"]:
        extra.append(due_status(t))
    tail = f"  ({', '.join(extra)})" if extra else ""
    return f"  #{t['id']:<3} {STATUS_MARK.get(t['status'], '[ ]')} [{t['priority'][:1]}] {t['title']}{tail}"


def agenda_menu(tasks):
    pending = [t for t in tasks if not t["done"]]
    week_end = add_days(TODAY, 7)
    overdue = [t for t in pending if t["due"] and t["due"] < TODAY]
    today = [t for t in pending if t["due"] == TODAY]
    active = [t for t in pending if t["status"] == "In Progress"
              and t not in overdue and t not in today]
    soon = [t for t in pending if t["due"] and TODAY < t["due"] <= week_end and t not in active]
    heading(f"Agenda - {WEEKDAYS[weekday(TODAY)]}, {TODAY}")
    shown = False
    for name, items in [("OVERDUE", overdue), ("DUE TODAY", today),
                        ("IN PROGRESS", active), ("COMING UP (next 7 days)", soon)]:
        if not items:
            continue
        shown = True
        print(f"\n {name} ({len(items)})")
        for t in sorted(items, key=lambda t: (t["due"] or "9999", t["time"] or "99:99",
                                              PRIORITY_ORDER.get(t["priority"], 1))):
            print(agenda_line(t))
    if not shown:
        print("\n  You're all caught up. Nothing is due.")
    pause()


# ---------- 9. Weekly planner ----------
def week_menu(tasks):
    start = add_days(TODAY, -weekday(TODAY))   # Sunday of this week
    while True:
        heading(f"Week: {start} to {add_days(start, 6)}")
        total = 0
        for i in range(7):
            d = add_days(start, i)
            items = sorted([t for t in tasks if t["due"] == d],
                           key=lambda t: (t["done"], t["time"] or "99:99",
                                          PRIORITY_ORDER.get(t["priority"], 1)))
            total += len(items)
            mark = "   <-- today" if d == TODAY else ""
            print(f"\n {WEEKDAYS[i]:<9} {d}  ({len(items)}){mark}")
            for t in items:
                print(agenda_line(t))
        print(f"\n  {total} task(s) this week.")
        cmd = input("\n[n] next week  [p] previous  [t] this week  [0] back: ").strip().lower()
        if cmd == "0":
            return
        if cmd == "n":
            start = add_days(start, 7)
        elif cmd == "p":
            start = add_days(start, -7)
        elif cmd == "t":
            start = add_days(TODAY, -weekday(TODAY))
        else:
            print("Please enter n, p, t or 0.")


# ---------- 10. Calendar ----------
def calendar_menu(tasks):
    y, m = int(TODAY[:4]), int(TODAY[5:7])
    while True:
        prefix = f"{y:04d}-{m:02d}-"
        pending, done = set(), set()
        month_tasks = [t for t in tasks if t["due"] and t["due"].startswith(prefix)]
        for t in month_tasks:
            (done if t["done"] else pending).add(int(t["due"][8:]))
        heading(f"{MONTHS[m - 1]} {y}")
        print("  " + "".join(f"{d:^6}" for d in ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]))
        cells = [0] * weekday(prefix + "01") + list(range(1, days_in_month(y, m) + 1))
        for i in range(0, len(cells), 7):
            line = ""
            for d in cells[i:i + 7]:
                if d == 0:
                    line += " " * 6
                    continue
                body = f"[{d:>2}]" if prefix + f"{d:02d}" == TODAY else f" {d:>2} "
                mark = "*" if d in pending else ("." if d in done else " ")
                line += f"{body}{mark} "
            print("  " + line.rstrip())
        print("\n  [ ] today   * has pending tasks   . completed tasks only")
        if month_tasks:
            print("\n Due this month:")
            for t in sorted(month_tasks, key=lambda t: (t["due"], t["time"] or "99:99")):
                print(f"  {t['due'][8:]} {WEEKDAYS[weekday(t['due'])][:3]}"
                      f"{agenda_line(t)[1:]}")
        cmd = input("\n[n] next  [p] previous  [t] today  [g] go to YYYY-MM  [0] back: ").strip().lower()
        if cmd == "0":
            return
        if cmd == "n":
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        elif cmd == "p":
            y, m = (y - 1, 12) if m == 1 else (y, m - 1)
            y = max(y, 1)
        elif cmd == "t":
            y, m = int(TODAY[:4]), int(TODAY[5:7])
        elif cmd == "g":
            raw = input("Month (YYYY-MM): ").strip()
            if valid_date(raw + "-01"):
                y, m = int(raw[:4]), int(raw[5:7])
            else:
                print("Invalid month.")
        else:
            print("Please enter n, p, t, g or 0.")


# ---------- 11. Reschedule overdue ----------
def reschedule_menu(tasks):
    overdue = [t for t in tasks if is_overdue(t)]
    if not overdue:
        print("\nNo overdue tasks. Nice!")
        pause()
        return
    print_tasks(sorted(overdue, key=lambda t: t["due"]), "Overdue tasks")
    idx = choose("Move overdue tasks to", ["Today", "Tomorrow", "In 1 week", "Pick a date"],
                 back_label="Cancel")
    if idx is None:
        return
    if idx == 3:
        new_due = ask_date_text(None)
        if not new_due:
            return
    else:
        new_due = [TODAY, add_days(TODAY, 1), add_days(TODAY, 7)][idx]
    scope = choose("Which tasks?", ["ALL overdue tasks", "Only some (by ID)"], back_label="Cancel")
    if scope is None:
        return
    targets = overdue if scope == 0 else [t for t in ask_task_ids(overdue)]
    if not targets:
        print("Nothing changed.")
        return
    for t in targets:
        t["due"] = new_due
    save_tasks(tasks)
    print(f"Moved {len(targets)} task(s) to {new_due}.")


# ---------- 12. Search ----------
def search_menu(tasks):
    scopes = [
        ("Title", ["title"]),
        ("Notes", ["notes"]),
        ("Subject / course", ["subject"]),
        ("Location / people", ["location", "people"]),
        ("Category / type", ["category", "type"]),
        ("Checklist items", ["__subtasks__"]),
        ("Everything", ["title", "notes", "subject", "location", "people", "category", "type",
                        "__subtasks__"]),
    ]
    idx = choose("Search in", [s[0] for s in scopes])
    if idx is None:
        return
    term = input("Search for: ").strip().lower()
    if not term:
        return
    fields = scopes[idx][1]

    def matches(t):
        for f in fields:
            if f == "__subtasks__":
                if any(term in s["text"].lower() for s in t["subtasks"]):
                    return True
            elif term in str(t.get(f) or "").lower():
                return True
        return False

    found = [t for t in tasks if matches(t)]
    print_tasks(sort_choice(found), f"Results for '{term}'")
    pause()


# ---------- 13. Statistics ----------
def stats_menu(tasks):
    idx = choose("Statistics", ["Overview", "Breakdown by priority", "Breakdown by category",
                                "Breakdown by type", "Checklist progress per task",
                                "Next deadlines"])
    if idx is None:
        return
    total = len(tasks)
    done = sum(t["done"] for t in tasks)
    if idx == 0:
        heading("Overview")
        print(f"  Completion   {progress_bar(done, total, 30)}   ({done} of {total})\n")
        for s in STATUSES:
            n = sum(t["status"] == s for t in tasks)
            print(f"  {s:<12} {n:>3}   {progress_bar(n, total, 20)}")
        subs = [s for t in tasks for s in t["subtasks"]]
        week_end = add_days(TODAY, 7)
        print(f"\n  Overdue            : {sum(is_overdue(t) for t in tasks)}")
        print(f"  Due today          : {sum(1 for t in tasks if not t['done'] and t['due'] == TODAY)}")
        print(f"  Due in next 7 days : "
              f"{sum(1 for t in tasks if not t['done'] and t['due'] and TODAY < t['due'] <= week_end)}")
        print(f"  Repeating tasks    : {sum(1 for t in tasks if t['repeat'])}")
        print(f"  Checklist items    : {sum(s['done'] for s in subs)}/{len(subs)} ticked")
        pause()
        return
    if idx == 4:
        heading("Checklist progress")
        with_subs = [t for t in tasks if t["subtasks"]]
        if not with_subs:
            print("  No tasks with checklists yet.")
        for t in with_subs:
            d = sum(s["done"] for s in t["subtasks"])
            print(f"  #{t['id']:<3} {progress_bar(d, len(t['subtasks']), 14)}  {t['title'][:30]}")
        pause()
        return
    if idx == 5:
        heading("Next deadlines")
        upcoming = sorted([t for t in tasks if not t["done"] and t["due"]],
                          key=lambda t: (t["due"], t["time"] or "99:99"))[:10]
        if not upcoming:
            print("  No pending tasks with a due date.")
        for t in upcoming:
            print(f"  {t['due']}  {due_status(t):<16} #{t['id']:<3} {t['title']}")
        pause()
        return
    key = ["priority", "category", "type"][idx - 1]
    groups = {}
    for t in tasks:
        g = groups.setdefault(t[key], [0, 0])
        g[0] += 1
        g[1] += t["done"]
    heading(f"Breakdown by {key}")
    print(f"  {key.title():<14}{'Total':>6}{'Done':>6}{'Open':>6}   Progress")
    print("  " + "-" * (WIDTH - 4))
    order = (lambda kv: PRIORITY_ORDER.get(kv[0], 9)) if key == "priority" else (lambda kv: kv[0].lower())
    for name, (n, d) in sorted(groups.items(), key=order):
        print(f"  {name[:13]:<14}{n:>6}{d:>6}{n - d:>6}   {progress_bar(d, n, 14)}")
    if not groups:
        print("  No tasks yet.")
    pause()


# ---------- 14. Export ----------
def report_text(tasks):
    total = len(tasks)
    done = sum(t["done"] for t in tasks)
    lines = ["TASK REPORT", f"Date: {WEEKDAYS[weekday(TODAY)]}, {TODAY}", "=" * 60,
             f"Progress : {progress_bar(done, total, 30)} ({done}/{total})",
             f"Overdue  : {sum(is_overdue(t) for t in tasks)}",
             f"Due today: {sum(1 for t in tasks if not t['done'] and t['due'] == TODAY)}", ""]
    for s in STATUSES:
        items = sorted([t for t in tasks if t["status"] == s], key=SORTERS["Due date"])
        lines.append(f"{s.upper()} ({len(items)})")
        lines.append("-" * 60)
        for t in items:
            extra = [t["type"], t["priority"], t["category"]]
            if t["due"]:
                extra.append(f"due {t['due']}")
            lines.append(f"  #{t['id']} {STATUS_MARK[s]} {t['title']}  ({', '.join(extra)})")
            if t["notes"]:
                lines.append(f"        notes: {t['notes']}")
            for sub in t["subtasks"]:
                lines.append(f"        {'[x]' if sub['done'] else '[ ]'} {sub['text']}")
        if not items:
            lines.append("  (none)")
        lines.append("")
    return "\n".join(lines)


def csv_cell(v):
    return '"' + str(v if v is not None else "").replace('"', '""').replace("\n", " ") + '"'


def export_menu(tasks):
    idx = choose("Export", [f"Text report ({REPORT_FILE})",
                            f"Spreadsheet CSV ({CSV_FILE})",
                            "Print report on screen"])
    if idx is None:
        return
    if idx == 0:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report_text(tasks) + "\n")
        print(f"Saved report to {REPORT_FILE}.")
    elif idx == 1:
        cols = ["id", "type", "title", "status", "priority", "category", "due", "time",
                "repeat", "subject", "location", "people", "notes", "created"]
        with open(CSV_FILE, "w", encoding="utf-8") as f:
            f.write(",".join(cols) + ",checklist\n")
            for t in tasks:
                f.write(",".join(csv_cell(t.get(c)) for c in cols)
                        + "," + csv_cell(subtask_progress(t)) + "\n")
        print(f"Saved {len(tasks)} task(s) to {CSV_FILE}.")
    else:
        print("\n" + report_text(tasks))
        pause()


# ---------- 15. Backup / restore ----------
def backup_menu(tasks):
    idx = choose("Backup & restore", [f"Create backup ({BACKUP_FILE})",
                                      "Restore from backup",
                                      "Show backup info"])
    if idx is None:
        return
    if idx == 0:
        save_tasks(tasks, BACKUP_FILE)
        print(f"Backed up {len(tasks)} task(s) to {BACKUP_FILE}.")
        return
    backup = load_tasks(BACKUP_FILE)
    if backup is None:
        print(f"No backup file found ({BACKUP_FILE}). Create one first.")
        return
    if idx == 2:
        print(f"Backup has {len(backup)} task(s); current list has {len(tasks)}.")
        return
    print(f"Backup has {len(backup)} task(s); current list has {len(tasks)}.")
    if confirm("Replace the current tasks with the backup?"):
        tasks[:] = backup
        renumber(tasks)
        save_tasks(tasks)
        print("Restored.")


# ---------- 16. Settings ----------
def categories_menu():
    while True:
        custom = [c for c in CATEGORIES if c not in BASE_CATEGORIES]
        print("\nBuilt-in : " + ", ".join(BASE_CATEGORIES))
        print("Custom   : " + (", ".join(custom) if custom else "(none)"))
        idx = choose("Categories", ["Add custom category", "Remove custom category"])
        if idx is None:
            return
        if idx == 0:
            name = input("New category: ").strip().title()
            if name and name not in CATEGORIES:
                CATEGORIES.append(name)
                save_settings()
                print(f"Added '{name}'.")
            else:
                print("Empty or already exists.")
        else:
            if not custom:
                print("No custom categories to remove.")
                continue
            c = choose("Remove which?", custom)
            if c is not None:
                CATEGORIES.remove(custom[c])
                save_settings()
                print(f"Removed '{custom[c]}' (tasks keep their category).")


def settings_menu(tasks):
    global DEFAULT_SORT, DEFAULT_PRIORITY, SHOW_REMINDERS
    while True:
        names = list(SORTERS)
        idx = choose("Settings", [
            f"Change today's date (now {TODAY})",
            f"Default sort order (now {names[DEFAULT_SORT]})",
            f"Default priority (now {DEFAULT_PRIORITY})",
            f"Start-up reminders (now {'ON' if SHOW_REMINDERS else 'OFF'})",
            "Manage categories",
            "Reset settings to default",
            "Renumber task IDs (1, 2, 3, ...)",
            "About / data files",
        ])
        if idx is None:
            return
        if idx == 0:
            ask_today()
            print(f"Today is now {WEEKDAYS[weekday(TODAY)]}, {TODAY}.")
        elif idx == 1:
            s = choose("Default sort order", names, back_label="Keep current")
            if s is not None:
                DEFAULT_SORT = s
                save_settings()
                print(f"Default sort: {names[s]}.")
        elif idx == 2:
            p = choose("Default priority", PRIORITIES, back_label="Keep current")
            if p is not None:
                DEFAULT_PRIORITY = PRIORITIES[p]
                save_settings()
                print(f"Default priority: {DEFAULT_PRIORITY}.")
        elif idx == 3:
            SHOW_REMINDERS = not SHOW_REMINDERS
            save_settings()
            print(f"Start-up reminders {'ON' if SHOW_REMINDERS else 'OFF'}.")
        elif idx == 4:
            categories_menu()
        elif idx == 5:
            if confirm("Reset sort, priority, reminders and custom categories?"):
                DEFAULT_SORT, DEFAULT_PRIORITY, SHOW_REMINDERS = 0, "Medium", True
                CATEGORIES[:] = list(BASE_CATEGORIES)
                for t in tasks:
                    if t["category"] not in CATEGORIES:
                        CATEGORIES.append(t["category"])
                save_settings()
                print("Settings reset.")
        elif idx == 6:
            if renumber(tasks):
                save_tasks(tasks)
                print(f"Renumbered {len(tasks)} task(s): IDs are now 1 to {len(tasks)}.")
            else:
                print("IDs are already in order (1, 2, 3, ...).")
        else:
            heading("About")
            print(f"  Tasks file     : {DATA_FILE} ({len(tasks)} tasks)")
            print(f"  Settings file  : {SETTINGS_FILE}")
            print(f"  Backup file    : {BACKUP_FILE}")
            print(f"  Exports        : {REPORT_FILE}, {CSV_FILE}")
            print("  Version        : 6 (no imports)")
            pause()


# ---------- 17. Help ----------
def help_menu(tasks):
    heading("Help")
    print("""  Navigation
    - Type the number of an option and press Enter.
    - Type 0 in any menu to go back.

  Tasks
    - Add: choose a type (Assignment, Exam, Meeting, ...). Each type asks
      only for the details that matter for it.
    - Details: full card for one task with quick status / checklist actions.
    - Duplicate: copy tasks (checklists are reset) with a new due date.
    - Status flow: [ ] To Do -> [~] In Progress -> [x] Done.
    - Task IDs accept lists and ranges, for example 3, 1,4,7 or 2-5.
    - Repeating tasks create the next one automatically when marked Done.

  Progress
    - Agenda: overdue, due today, in progress and the next 7 days.
    - Weekly planner: Sunday-Saturday view, [n]/[p] to change week.
    - Calendar: month grid  * pending  . done  [ ] today, [g] jump to month.
    - Reschedule: move overdue tasks to a new date in one go.

  Tools
    - Search titles, notes, checklist items and more.
    - Statistics, Export (report.txt / tasks.csv), Backup & restore.
    - Settings: default sort / priority, reminders, categories, reset.

  Priority tags in lists:  [H] High   [M] Medium   [L] Low""")
    pause()


# ---------- Main loop ----------
MENU_GROUPS = [
    ("TASKS", [("Add task", add_menu), ("View tasks", view_menu),
               ("Task details", details_menu), ("Edit task", edit_menu),
               ("Duplicate task(s)", duplicate_menu), ("Delete task(s)", delete_menu)]),
    ("PROGRESS", [("Update status", status_menu), ("Today's agenda", agenda_menu),
                  ("Weekly planner", week_menu), ("Calendar", calendar_menu),
                  ("Reschedule overdue", reschedule_menu)]),
    ("TOOLS", [("Search", search_menu), ("Statistics", stats_menu),
               ("Export", export_menu), ("Backup & restore", backup_menu),
               ("Settings", settings_menu), ("Help", help_menu)]),
]
MAIN_MENU = [item for _, items in MENU_GROUPS for item in items]


def dashboard(tasks):
    total = len(tasks)
    done = sum(t["done"] for t in tasks)
    todo = sum(t["status"] == "To Do" for t in tasks)
    prog = sum(t["status"] == "In Progress" for t in tasks)
    overdue = sum(is_overdue(t) for t in tasks)
    due_today = sum(1 for t in tasks if not t["done"] and t["due"] == TODAY)
    print("\n" + rule("="))
    print(row("TASK MANAGEMENT SYSTEM", "center"))
    print(rule("="))
    print(row(f"{WEEKDAYS[weekday(TODAY)]}, {MONTHS[int(TODAY[5:7]) - 1]} "
              f"{int(TODAY[8:])}, {TODAY[:4]}"))
    print(row(f"Progress {progress_bar(done, total, 24)}  {done}/{total} done"))
    print(row(f"To Do: {todo}   In Progress: {prog}   Overdue: {overdue}   Today: {due_today}"))
    print(rule())
    n = 1
    for group, items in MENU_GROUPS:
        print(row(group))
        for label, _ in items:
            print(row(f"   {n:>2}.  {label}"))
            n += 1
        print(row())
    print(row(f"   {0:>2}.  Exit"))
    print(rule("="))


def show_reminders(tasks):
    if not SHOW_REMINDERS:
        return
    overdue = [t for t in tasks if is_overdue(t)]
    due_today = [t for t in tasks if not t["done"] and t["due"] == TODAY]
    if not (overdue or due_today):
        return
    print("\n" + rule())
    print(row(f"REMINDER: {len(overdue)} overdue, {len(due_today)} due today"))
    for t in (overdue + due_today)[:5]:
        print(row(f"  #{t['id']} {t['title']} ({due_status(t)})"))
    print(rule())


def main():
    print("\n" + rule("="))
    print(row("TASK MANAGEMENT SYSTEM", "center"))
    print(rule("="))
    ask_today()
    load_settings()
    tasks = load_tasks() or []
    show_reminders(tasks)
    while True:
        dashboard(tasks)
        choice = input("Select an option: ").strip()
        if choice == "0":
            save_tasks(tasks)
            print(f"\nSaved {len(tasks)} task(s) to {DATA_FILE}. Goodbye!")
            break
        if choice.isdigit() and 1 <= int(choice) <= len(MAIN_MENU):
            MAIN_MENU[int(choice) - 1][1](tasks)
        else:
            print("Invalid option, please try again.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
