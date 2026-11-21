"""SQLite persistence. One connection guarded by a lock; each write is one transaction."""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS plans(
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, start_date TEXT NOT NULL,
        version INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS tasks(
        plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
        task_id TEXT NOT NULL, position INTEGER NOT NULL, title TEXT NOT NULL,
        duration_days INTEGER NOT NULL CHECK(duration_days >= 1),
        PRIMARY KEY(plan_id, task_id))""",
    """CREATE TABLE IF NOT EXISTS edges(
        plan_id INTEGER NOT NULL, task_id TEXT NOT NULL, pred_id TEXT NOT NULL,
        PRIMARY KEY(plan_id, task_id, pred_id), CHECK(task_id <> pred_id),
        FOREIGN KEY(plan_id, task_id) REFERENCES tasks(plan_id, task_id) ON DELETE CASCADE,
        FOREIGN KEY(plan_id, pred_id) REFERENCES tasks(plan_id, task_id) ON DELETE CASCADE)""",
)


class NotFound(Exception):
    pass


class VersionConflict(Exception):
    def __init__(self, current_version):
        super().__init__("version conflict")
        self.current_version = current_version


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Store:
    def __init__(self, db_path):
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
        try:
            self._db.execute("PRAGMA busy_timeout=5000")
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA foreign_keys=ON")
            with self._tx():
                ver = self._db.execute("PRAGMA user_version").fetchone()[0]
                if ver == 0:
                    for stmt in SCHEMA:
                        self._db.execute(stmt)
                    self._db.execute("PRAGMA user_version=1")
                elif ver != 1:
                    raise RuntimeError(f"unsupported database schema version {ver}")
        except BaseException:
            self._db.close()
            raise

    @contextmanager
    def _tx(self):
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
            else:
                self._db.execute("COMMIT")

    def close(self):
        with self._lock:
            self._db.close()

    def list_plans(self):
        with self._lock:
            rows = self._db.execute(
                """SELECT p.id, p.title, p.start_date, p.version,
                          (SELECT COUNT(*) FROM tasks t WHERE t.plan_id = p.id), p.updated_at
                   FROM plans p ORDER BY p.updated_at DESC, p.id DESC"""
            ).fetchall()
        keys = ("id", "title", "start_date", "version", "task_count", "updated_at")
        return [dict(zip(keys, r)) for r in rows]

    def _load(self, plan_id):
        db = self._db
        row = db.execute(
            "SELECT id, title, start_date, version, created_at, updated_at FROM plans WHERE id=?",
            (plan_id,),
        ).fetchone()
        if row is None:
            raise NotFound(plan_id)
        preds = {}
        for tid, pid in db.execute(
            """SELECT e.task_id, e.pred_id FROM edges e
               JOIN tasks p ON p.plan_id = e.plan_id AND p.task_id = e.pred_id
               WHERE e.plan_id=? ORDER BY p.position""",
            (plan_id,),
        ):
            preds.setdefault(tid, []).append(pid)
        tasks = [
            {"id": t, "title": ti, "duration_days": d, "predecessors": preds.get(t, [])}
            for t, ti, d in db.execute(
                "SELECT task_id, title, duration_days FROM tasks WHERE plan_id=? ORDER BY position",
                (plan_id,),
            )
        ]
        keys = ("id", "title", "start_date", "version", "created_at", "updated_at")
        plan = dict(zip(keys, row))
        plan["tasks"] = tasks
        return plan

    def get_plan(self, plan_id):
        with self._lock:
            return self._load(plan_id)

    def create_plan(self, title, start_date):
        now = _now()
        with self._tx() as db:
            cur = db.execute(
                "INSERT INTO plans(title, start_date, version, created_at, updated_at) VALUES(?,?,1,?,?)",
                (title, start_date, now, now),
            )
            return self._load(cur.lastrowid)

    def _locked_version(self, db, plan_id, version):
        row = db.execute("SELECT version FROM plans WHERE id=?", (plan_id,)).fetchone()
        if row is None:
            raise NotFound(plan_id)
        if row[0] != version:
            raise VersionConflict(row[0])

    def replace_plan(self, plan_id, version, title, start_date, tasks):
        with self._tx() as db:
            self._locked_version(db, plan_id, version)
            db.execute(
                "UPDATE plans SET title=?, start_date=?, version=version+1, updated_at=? WHERE id=?",
                (title, start_date, _now(), plan_id),
            )
            db.execute("DELETE FROM tasks WHERE plan_id=?", (plan_id,))  # edges cascade
            db.executemany(
                "INSERT INTO tasks(plan_id, task_id, position, title, duration_days) VALUES(?,?,?,?,?)",
                [(plan_id, t["id"], i, t["title"], t["duration_days"]) for i, t in enumerate(tasks)],
            )
            db.executemany(
                "INSERT INTO edges(plan_id, task_id, pred_id) VALUES(?,?,?)",
                [(plan_id, t["id"], p) for t in tasks for p in t["predecessors"]],
            )
            return self._load(plan_id)

    def delete_plan(self, plan_id, version):
        with self._tx() as db:
            self._locked_version(db, plan_id, version)
            db.execute("DELETE FROM plans WHERE id=?", (plan_id,))
