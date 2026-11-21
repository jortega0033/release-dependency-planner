"""Payload validation. Pure functions; no I/O."""
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone

MAX_TASKS = 200
MAX_PREDS = 50
MAX_TITLE = 120
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class ValidationError(Exception):
    def __init__(self, details):
        super().__init__("validation failed")
        self.details = details


@dataclass
class ValidationResult:
    title: str
    start_date: str
    tasks: list
    version: int | None = None


def _add(errs, field, code, message):
    errs.append({"field": field, "code": code, "message": message})


def _title(errs, field, val):
    if not isinstance(val, str):
        _add(errs, field, "type", "must be a string")
        return None
    s = val.strip()
    if not s:
        _add(errs, field, "too_short", "must not be empty")
    elif len(s) > MAX_TITLE:
        _add(errs, field, "too_long", f"must be at most {MAX_TITLE} characters")
    elif any(unicodedata.category(c) == "Cc" for c in s):
        _add(errs, field, "type", "must not contain control characters")
    else:
        return s
    return None


def _date(errs, field, val):
    if not isinstance(val, str):
        _add(errs, field, "type", "must be a string")
        return None
    if DATE_RE.match(val):
        try:
            date.fromisoformat(val)
            return val
        except ValueError:
            pass
    _add(errs, field, "invalid_date", "must be a real date in YYYY-MM-DD format")
    return None


def _unknown(errs, obj, allowed, prefix=""):
    for k in obj:
        if k not in allowed:
            _add(errs, prefix + str(k)[:64], "unknown_field", "unknown field")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_create_payload(obj):
    """Returns (title, start_date) or raises ValidationError."""
    errs = []
    if not isinstance(obj, dict):
        raise ValidationError([{"field": "", "code": "type", "message": "body must be an object"}])
    _unknown(errs, obj, {"title", "start_date"})
    title = start = None
    if "title" not in obj:
        _add(errs, "title", "required", "is required")
    else:
        title = _title(errs, "title", obj["title"])
    if obj.get("start_date") is None:
        start = datetime.now(timezone.utc).date().isoformat()
    else:
        start = _date(errs, "start_date", obj["start_date"])
    if errs:
        raise ValidationError(errs)
    return title, start


def _has_cycle(ids, edges):
    """Kahn topological sort; edges are (pred, task) pairs."""
    indeg = {i: 0 for i in ids}
    out = {i: [] for i in ids}
    for p, t in edges:
        out[p].append(t)
        indeg[t] += 1
    queue = [i for i in ids if indeg[i] == 0]
    seen = 0
    while queue:
        n = queue.pop()
        seen += 1
        for m in out[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    return seen != len(ids)


def validate_plan_payload(obj):
    """Validate a full PUT body. Returns ValidationResult or raises ValidationError."""
    if not isinstance(obj, dict):
        raise ValidationError([{"field": "", "code": "type", "message": "body must be an object"}])
    errs = []
    _unknown(errs, obj, {"version", "title", "start_date", "tasks"})

    version = obj.get("version")
    if "version" not in obj:
        _add(errs, "version", "required", "is required")
    elif not _is_int(version) or version < 1:
        _add(errs, "version", "type", "must be a positive integer")
        version = None

    title = start = None
    if "title" not in obj:
        _add(errs, "title", "required", "is required")
    else:
        title = _title(errs, "title", obj["title"])
    if "start_date" not in obj:
        _add(errs, "start_date", "required", "is required")
    else:
        start = _date(errs, "start_date", obj["start_date"])

    tasks_out = []
    raw = obj.get("tasks")
    if "tasks" not in obj:
        _add(errs, "tasks", "required", "is required")
    elif not isinstance(raw, list):
        _add(errs, "tasks", "type", "must be an array")
    elif len(raw) > MAX_TASKS:
        _add(errs, "tasks", "too_many_tasks", f"at most {MAX_TASKS} tasks allowed")
    else:
        _check_tasks(errs, raw, tasks_out)

    if errs:
        raise ValidationError(errs)
    return ValidationResult(title, start, tasks_out, version)


def _check_tasks(errs, raw, out):
    ids_seen = set()
    for i, t in enumerate(raw):
        f = f"tasks[{i}]"
        if not isinstance(t, dict):
            _add(errs, f, "type", "must be an object")
            out.append({"id": None, "title": None, "duration_days": None, "predecessors": []})
            continue
        _unknown(errs, t, {"id", "title", "duration_days", "predecessors"}, f + ".")
        tid = t.get("id")
        if "id" not in t:
            _add(errs, f + ".id", "required", "is required")
            tid = None
        elif not isinstance(tid, str) or not ID_RE.match(tid):
            _add(errs, f + ".id", "invalid_id", "must match [A-Za-z0-9_-]{1,32}")
            tid = None
        elif tid in ids_seen:
            _add(errs, f + ".id", "duplicate_task_id", "duplicate task id")
        else:
            ids_seen.add(tid)
        if "title" not in t:
            _add(errs, f + ".title", "required", "is required")
            ttl = None
        else:
            ttl = _title(errs, f + ".title", t["title"])
        d = t.get("duration_days")
        if "duration_days" not in t:
            _add(errs, f + ".duration_days", "required", "is required")
        elif not _is_int(d):
            _add(errs, f + ".duration_days", "type", "must be an integer")
        elif not 1 <= d <= 365:
            _add(errs, f + ".duration_days", "out_of_range", "must be between 1 and 365")
        preds = t.get("predecessors", [])
        if not isinstance(preds, list):
            _add(errs, f + ".predecessors", "type", "must be an array")
            preds = []
        elif len(preds) > MAX_PREDS:
            _add(errs, f + ".predecessors", "too_many_tasks", f"at most {MAX_PREDS} predecessors allowed")
            preds = []
        out.append({"id": tid, "title": ttl, "duration_days": d, "predecessors": preds})

    # Graph checks, after every task has been seen.
    edges = []
    for i, t in enumerate(out):
        seen = set()
        for j, p in enumerate(t["predecessors"]):
            f = f"tasks[{i}].predecessors[{j}]"
            if not isinstance(p, str):
                _add(errs, f, "type", "must be a string")
            elif p == t["id"]:
                _add(errs, f, "self_dependency", "a task cannot depend on itself")
            elif p in seen:
                _add(errs, f, "duplicate_predecessor", "duplicate predecessor")
            elif p not in ids_seen:
                _add(errs, f, "unknown_predecessor", "predecessor is not a task in this plan")
            else:
                if t["id"] is not None:
                    edges.append((p, t["id"]))
            if isinstance(p, str):
                seen.add(p)
    if edges and _has_cycle(sorted(ids_seen), edges):
        _add(errs, "tasks", "cycle", "Dependencies form a cycle")
