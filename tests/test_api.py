"""HTTP-level baseline checks (CHK-B01..CHK-B16) against a real loopback server."""
import http.client
import json
import re
import tempfile
import threading
import unittest
from pathlib import Path

from release_planner.server import make_server

STATIC = Path(__file__).resolve().parent.parent / "release_planner" / "static"


def launch_tasks():
    return [
        {"id": "a", "title": "Freeze branch", "duration_days": 2, "predecessors": []},
        {"id": "b", "title": "Draft notes", "duration_days": 1, "predecessors": []},
        {"id": "c", "title": "Ship build", "duration_days": 2, "predecessors": ["a", "b"]},
    ]


class RunningServer:
    def __init__(self, data_dir):
        self.server = make_server(data_dir, 0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def request(self, method, path, body=None, headers=None, raw=None, origin=True, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Host": host or f"127.0.0.1:{self.port}"}
        if origin is True:
            hdrs["Origin"] = f"http://127.0.0.1:{self.port}"
        elif origin:
            hdrs["Origin"] = origin
        payload = raw
        if body is not None:
            payload = json.dumps(body).encode()
        if payload is not None:
            hdrs["Content-Type"] = "application/json"
        hdrs.update(headers or {})
        try:
            conn.request(method, path, body=payload, headers=hdrs)
            resp = conn.getresponse()
            data = resp.read()
            ctype = resp.getheader("Content-Type", "")
            parsed = json.loads(data) if data and "json" in ctype else data
            return resp.status, parsed, resp
        finally:
            conn.close()


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = self._tmp.name
        self.srv = RunningServer(self.data_dir)
        self.addCleanup(self._stop_if_running)

    def _stop_if_running(self):
        if self.srv is not None:
            self.srv.stop()
            self.srv = None

    def create(self, title="Launch week", start="2026-11-23"):
        status, plan, _ = self.srv.request("POST", "/api/v1/projects", {"title": title, "start_date": start})
        self.assertEqual(status, 201, plan)
        return plan

    def save(self, plan, tasks=None, version=None, title=None):
        body = {
            "version": plan["version"] if version is None else version,
            "title": plan["title"] if title is None else title,
            "start_date": plan["start_date"],
            "tasks": launch_tasks() if tasks is None else tasks,
        }
        return self.srv.request("PUT", f"/api/v1/projects/{plan['id']}", body)

    def codes(self, payload):
        return [d["code"] for d in payload["error"].get("details", [])]


class HealthAndCrud(ApiTestCase):
    def test_health(self):  # CHK-B01
        status, body, _ = self.srv.request("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok", "api_version": 1, "schema_version": 1})

    def test_create_and_get(self):  # CHK-B02
        plan = self.create()
        self.assertEqual((plan["title"], plan["start_date"], plan["version"], plan["tasks"]),
                         ("Launch week", "2026-11-23", 1, []))
        status, got, _ = self.srv.request("GET", f"/api/v1/projects/{plan['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(got, plan)
        status, listing, _ = self.srv.request("GET", "/api/v1/projects")
        self.assertEqual([p["id"] for p in listing["projects"]], [plan["id"]])
        self.assertEqual(listing["projects"][0]["task_count"], 0)

    def test_launch_fixture_saves(self):  # CHK-B03
        plan = self.create()
        status, saved, _ = self.save(plan)
        self.assertEqual(status, 200, saved)
        self.assertEqual(saved["version"], 2)
        self.assertEqual([t["id"] for t in saved["tasks"]], ["a", "b", "c"])
        self.assertEqual(saved["tasks"][2]["predecessors"], ["a", "b"])
        self.assertEqual(saved["tasks"][0]["duration_days"], 2)

    def test_delete(self):  # CHK-B14
        plan = self.create()
        status, _, _ = self.srv.request("DELETE", f"/api/v1/projects/{plan['id']}?version=99")
        self.assertEqual(status, 409)
        status, _, _ = self.srv.request("DELETE", f"/api/v1/projects/{plan['id']}?version=1")
        self.assertEqual(status, 204)
        status, body, _ = self.srv.request("GET", f"/api/v1/projects/{plan['id']}")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["code"], "not_found")

    def test_unknown_path_is_json_404(self):
        status, body, _ = self.srv.request("GET", "/api/v1/nope")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["code"], "not_found")

    def test_bound_to_loopback(self):  # CHK-B16
        self.assertEqual(self.srv.server.server_address[0], "127.0.0.1")


class Persistence(ApiTestCase):
    def test_restart_keeps_plan(self):  # CHK-B04
        plan = self.create()
        _, saved, _ = self.save(plan)
        self.srv.stop()
        self.srv = RunningServer(self.data_dir)
        status, again, _ = self.srv.request("GET", f"/api/v1/projects/{plan['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(again, saved)
        self.assertTrue((Path(self.data_dir) / "release_planner.sqlite3").exists())


class Validation(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.plan = self.create()
        _, self.saved, _ = self.save(self.plan)

    def assert_unchanged(self):
        _, now, _ = self.srv.request("GET", f"/api/v1/projects/{self.plan['id']}")
        self.assertEqual(now, self.saved)

    def test_self_dependency(self):  # CHK-B05
        tasks = launch_tasks()
        tasks[0]["predecessors"] = ["a"]
        status, body, _ = self.save(self.saved, tasks)
        self.assertEqual(status, 422)
        self.assertIn("self_dependency", self.codes(body))
        self.assert_unchanged()

    def test_unknown_predecessor(self):  # CHK-B06
        tasks = launch_tasks()
        tasks[1]["predecessors"] = ["zzz"]
        status, body, _ = self.save(self.saved, tasks)
        self.assertEqual(status, 422)
        self.assertIn("unknown_predecessor", self.codes(body))
        self.assert_unchanged()

    def test_cycles_and_reverse_dependency(self):  # CHK-B07
        reverse = launch_tasks()
        reverse[0]["predecessors"] = ["c"]  # c already waits on a
        two_node = launch_tasks()
        two_node[0]["predecessors"] = ["b"]
        two_node[1]["predecessors"] = ["a"]
        chain = [
            {"id": "a", "title": "A", "duration_days": 1, "predecessors": ["c"]},
            {"id": "b", "title": "B", "duration_days": 1, "predecessors": ["a"]},
            {"id": "c", "title": "C", "duration_days": 1, "predecessors": ["b"]},
        ]
        for tasks in (reverse, two_node, chain):
            with self.subTest(tasks=[t["predecessors"] for t in tasks]):
                status, body, _ = self.save(self.saved, tasks)
                self.assertEqual(status, 422)
                self.assertIn("cycle", self.codes(body))
                self.assert_unchanged()

    def test_duplicate_ids_and_predecessors(self):
        tasks = launch_tasks()
        tasks[1]["id"] = "a"
        status, body, _ = self.save(self.saved, tasks)
        self.assertEqual(status, 422)
        self.assertIn("duplicate_task_id", self.codes(body))
        tasks = launch_tasks()
        tasks[2]["predecessors"] = ["a", "a"]
        status, body, _ = self.save(self.saved, tasks)
        self.assertEqual(status, 422)
        self.assertIn("duplicate_predecessor", self.codes(body))
        self.assert_unchanged()

    def test_duration_rules(self):  # CHK-B08
        for bad in (0, -1, 1.5, "2", True, None, 366):
            with self.subTest(duration=bad):
                tasks = launch_tasks()
                tasks[0]["duration_days"] = bad
                status, _, _ = self.save(self.saved, tasks)
                self.assertEqual(status, 422)
        for good in (1, 365):
            with self.subTest(duration=good):
                tasks = launch_tasks()
                tasks[0]["duration_days"] = good
                status, saved, _ = self.save(self.saved, tasks)
                self.assertEqual(status, 200, saved)
                self.saved = saved
        self.assert_unchanged()

    def test_title_and_date_rules(self):
        for title in ("", "   ", "x" * 121, "bad\x07title"):
            with self.subTest(title=title):
                status, _, _ = self.save(self.saved, title=title)
                self.assertEqual(status, 422)
        status, body, _ = self.srv.request("POST", "/api/v1/projects", {"title": "T", "start_date": "2026-02-30"})
        self.assertEqual(status, 422)
        self.assertIn("invalid_date", self.codes(body))
        self.assert_unchanged()

    def test_unknown_field_rejected(self):
        status, body, _ = self.srv.request(
            "PUT", f"/api/v1/projects/{self.plan['id']}",
            {"version": 2, "title": "T", "start_date": "2026-11-23", "tasks": [], "extra": 1})
        self.assertEqual(status, 422)
        self.assertIn("unknown_field", self.codes(body))

    def test_stale_version(self):  # CHK-B09
        status, body, _ = self.save(self.saved, version=1)
        self.assertEqual(status, 409)
        self.assertEqual(body["error"]["code"], "version_conflict")
        self.assertEqual(body["error"]["current_version"], 2)
        self.assert_unchanged()

    def test_titles_are_stored_verbatim(self):  # CHK-B13
        markup = '<img src=x onerror=alert(1)> & "quotes"'
        tasks = launch_tasks()
        tasks[0]["title"] = markup
        status, saved, _ = self.save(self.saved, tasks)
        self.assertEqual(status, 200, saved)
        self.assertEqual(saved["tasks"][0]["title"], markup)


class Guards(ApiTestCase):
    def test_host_validation(self):  # CHK-B10
        for host in ("evil.example", "127.0.0.1", f"127.0.0.1:{self.srv.port + 1}"):
            with self.subTest(host=host):
                status, body, _ = self.srv.request("GET", "/api/v1/health", host=host)
                self.assertEqual(status, 403)
                self.assertEqual(body["error"]["code"], "forbidden_host")
        status, _, _ = self.srv.request("GET", "/api/v1/health", host=f"localhost:{self.srv.port}")
        self.assertEqual(status, 200)

    def test_origin_validation(self):  # CHK-B11
        for origin in (False, "http://evil.example", "null"):
            with self.subTest(origin=origin):
                status, body, _ = self.srv.request("POST", "/api/v1/projects", {"title": "T"}, origin=origin)
                self.assertEqual(status, 403)
                self.assertEqual(body["error"]["code"], "forbidden_origin")
        status, _, _ = self.srv.request("GET", "/api/v1/projects", origin=False)
        self.assertEqual(status, 200)
        # nothing was created by the rejected writes
        _, listing, _ = self.srv.request("GET", "/api/v1/projects")
        self.assertEqual(listing["projects"], [])

    def test_body_limits_and_types(self):  # CHK-B12
        # Declare an oversized length but send a tiny body: the cap is enforced from the header,
        # so the client never has to push 300 KB into a connection the server is closing.
        status, body, _ = self.srv.request(
            "POST", "/api/v1/projects", raw=b'{"title":"T"}', headers={"Content-Length": "300000"})
        self.assertEqual(status, 413)
        self.assertEqual(body["error"]["code"], "payload_too_large")
        status, body, _ = self.srv.request("POST", "/api/v1/projects", raw=b"{not json")
        self.assertEqual((status, body["error"]["code"]), (400, "bad_json"))
        status, body, _ = self.srv.request("POST", "/api/v1/projects", raw=b"[1]")
        self.assertEqual((status, body["error"]["code"]), (400, "bad_json"))
        status, body, _ = self.srv.request(
            "POST", "/api/v1/projects", raw=b'{"title":"T"}', headers={"Content-Type": "text/plain"})
        self.assertEqual((status, body["error"]["code"]), (415, "unsupported_media_type"))

    def test_method_not_allowed(self):
        status, body, resp = self.srv.request("PUT", "/api/v1/health", {"x": 1})
        self.assertEqual(status, 405)
        self.assertTrue(resp.getheader("Allow"))


class StaticAssets(ApiTestCase):
    def test_static_served_with_security_headers(self):  # CHK-B13, CHK-B15
        for path, ctype in (("/", "text/html"), ("/static/tokens.css", "text/css"), ("/static/app.css", "text/css"), ("/static/app.js", "javascript")):
            with self.subTest(path=path):
                status, _, resp = self.srv.request("GET", path)
                self.assertEqual(status, 200)
                self.assertIn(ctype, resp.getheader("Content-Type"))
                self.assertIn("default-src 'self'", resp.getheader("Content-Security-Policy"))
                self.assertEqual(resp.getheader("X-Content-Type-Options"), "nosniff")
                self.assertEqual(resp.getheader("Cache-Control"), "no-store")

    def test_static_traversal_blocked(self):
        status, _, _ = self.srv.request("GET", "/static/../server.py")
        self.assertEqual(status, 404)
        status, _, _ = self.srv.request("GET", "/static/%2e%2e/server.py")
        self.assertEqual(status, 404)


class StaticSource(unittest.TestCase):
    """Source-level checks on the shipped UI files."""

    def read(self, name):
        return (STATIC / name).read_text(encoding="utf-8")

    def test_labels_present(self):  # CHK-B15
        combined = self.read("index.html") + self.read("app.js")
        for label in ("Plan title", "Start date", "Task title", "Duration (working days)",
                      "Predecessors", "Save plan", "Add task", "New plan", "Saved plans"):
            self.assertIn(label, combined)

    def test_no_unsafe_rendering_or_external_urls(self):  # CHK-B13
        js = self.read("app.js")
        self.assertNotRegex(js, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(")
        for name in ("index.html", "tokens.css", "app.css", "app.js"):
            text = self.read(name)
            self.assertIsNone(re.search(r"(?:src|href|url\()\s*=?\s*[\"']?https?://", text), name)
            self.assertNotIn("<script>", text.replace('<script src', ''), name)


if __name__ == "__main__":
    unittest.main()
