"""HTTP server: loopback only, JSON API plus three allowlisted static files."""
import json
import re
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import store as store_mod
from . import validation

MAX_BODY = 262144
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC = {  # URL path -> (file name, content type)
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/tokens.css": ("tokens.css", "text/css; charset=utf-8"),
    "/static/app.css": ("app.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
SECURITY_HEADERS = (
    ("Cache-Control", "no-store"),
    ("X-Content-Type-Options", "nosniff"),
    (
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'",
    ),
    ("Referrer-Policy", "no-referrer"),
)
PROJECT_RE = re.compile(r"^/api/v1/projects/([0-9]{1,18})$")
METHODS = ("GET", "POST", "PUT", "DELETE")
STATUS_CODES = {400: "bad_json", 403: "forbidden", 404: "not_found", 405: "method_not_allowed",
                411: "length_required", 413: "payload_too_large", 414: "bad_request",
                431: "bad_request", 501: "method_not_allowed"}


class ApiError(Exception):
    def __init__(self, status, code, message, details=None, extra=None, headers=()):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
        self.details, self.extra, self.headers = details, extra or {}, headers


class Handler(BaseHTTPRequestHandler):
    server_version = "ReleasePlanner"
    sys_version = ""
    timeout = 15

    # --- plumbing -------------------------------------------------------
    def _send(self, status, body=b"", ctype=None, headers=()):
        self.send_response(status)
        for k, v in SECURITY_HEADERS:
            self.send_header(k, v)
        for k, v in headers:
            self.send_header(k, v)
        if status != 204:
            if ctype:
                self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()
        if status != 204 and self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status, obj, headers=()):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8", headers)

    def _error(self, e):
        err = {"code": e.code, "message": e.message, **e.extra}
        if e.details:
            err["details"] = e.details
        self._json(e.status, {"error": err}, e.headers)

    def send_error(self, code, message=None, explain=None):
        # Used by the stdlib for malformed requests; keep the JSON envelope.
        self.command = self.command or "GET"
        try:
            name = HTTPStatus(code).phrase
        except ValueError:
            name = "Error"
        self._error(ApiError(code, STATUS_CODES.get(code, "bad_request"), name))

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _body(self):
        if "Transfer-Encoding" in self.headers:
            raise ApiError(411, "length_required", "Content-Length is required; chunked bodies are not supported")
        cl = self.headers.get("Content-Length")
        if cl is None or not re.fullmatch(r"[0-9]{1,12}", cl.strip()):
            raise ApiError(411, "length_required", "A valid Content-Length header is required")
        n = int(cl)
        if n > MAX_BODY:
            raise ApiError(413, "payload_too_large", f"Body must be at most {MAX_BODY} bytes")
        ctype = self.headers.get("Content-Type", "")
        parts = [p.strip() for p in ctype.split(";")]
        ok = parts[0].lower() == "application/json"
        for p in parts[1:]:
            k, _, v = p.partition("=")
            if k.strip().lower() == "charset" and v.strip().strip('"').lower() not in ("utf-8", "utf8"):
                ok = False
        if not ok:
            raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")
        raw = self.rfile.read(n)
        self._body_consumed = True
        if len(raw) != n:
            raise ApiError(400, "bad_json", "Incomplete request body")
        try:
            obj = json.loads(raw.decode("utf-8"))
        except (ValueError, RecursionError):
            raise ApiError(400, "bad_json", "Body is not valid JSON") from None
        if not isinstance(obj, dict):
            raise ApiError(400, "bad_json", "Body must be a JSON object")
        return obj

    # --- routing --------------------------------------------------------
    def _route(self, path):
        """Returns (allowed methods, {method: callable})."""
        if path in STATIC:
            return ("GET",), {"GET": lambda: self._static(path)}
        if path == "/api/v1/health":
            return ("GET",), {"GET": self._health}
        if path == "/api/v1/projects":
            return ("GET", "POST"), {"GET": self._list, "POST": self._create}
        m = PROJECT_RE.match(path)
        if m:
            pid = int(m.group(1))
            return ("GET", "PUT", "DELETE"), {
                "GET": lambda: self._get(pid),
                "PUT": lambda: self._put(pid),
                "DELETE": lambda: self._delete(pid),
            }
        raise ApiError(404, "not_found", "Not found")

    def _drain_unread_body(self):
        """Closing a socket with unread request bytes can reset the connection and lose
        the error response, so discard a bounded amount of any unread body first."""
        cl = (self.headers.get("Content-Length") or "").strip()
        if self._body_consumed or not cl.isdigit():
            return
        remaining = min(int(cl), 65536)
        try:
            self.request.settimeout(0.5)
            while remaining > 0:
                chunk = self.rfile.read1(remaining)
                if not chunk:
                    break
                remaining -= len(chunk)
        except (OSError, ValueError):
            pass

    def _dispatch(self):
        self._body_consumed = False
        try:
            port = self.server.port
            host = self.headers.get("Host", "")
            if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                raise ApiError(403, "forbidden_host", "Host not allowed")
            self.query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
            allowed, handlers = self._route(urlsplit(self.path).path)
            if self.command not in handlers:
                raise ApiError(405, "method_not_allowed", "Method not allowed",
                               headers=(("Allow", ", ".join(allowed)),))
            if self.command != "GET" and self.headers.get("Origin") != f"http://{host}":
                raise ApiError(403, "forbidden_origin", "Origin not allowed")
            handlers[self.command]()
        except ApiError as e:
            self._drain_unread_body()
            self._error(e)
        except (BrokenPipeError, ConnectionError, TimeoutError):
            self.close_connection = True
        except Exception as e:  # never leak details to the client
            self.log_error("internal error: %s", type(e).__name__)
            try:
                self._error(ApiError(500, "internal_error", "Internal server error"))
            except OSError:
                pass

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = do_OPTIONS = do_PATCH = _dispatch

    # --- handlers -------------------------------------------------------
    def _static(self, path):
        name, ctype = STATIC[path]
        try:
            data = (STATIC_DIR / name).read_bytes()
        except OSError:
            raise ApiError(404, "not_found", "Not found") from None
        self._send(200, data, ctype)

    def _health(self):
        self._json(200, {"status": "ok", "api_version": 1, "schema_version": 1})

    def _list(self):
        self._json(200, {"projects": self.server.store.list_plans()})

    def _fail_validation(self, e):
        details = e.details
        code422 = ApiError(422, "validation_failed", "Request validation failed", details)
        return code422

    def _create(self):
        body = self._body()
        try:
            title, start = validation.validate_create_payload(body)
        except validation.ValidationError as e:
            raise self._fail_validation(e) from None
        plan = self.server.store.create_plan(title, start)
        self._json(201, plan, (("Location", f"/api/v1/projects/{plan['id']}"),))

    def _get(self, pid):
        try:
            self._json(200, self.server.store.get_plan(pid))
        except store_mod.NotFound:
            raise ApiError(404, "not_found", "Project not found") from None

    def _put(self, pid):
        body = self._body()
        try:
            r = validation.validate_plan_payload(body)
        except validation.ValidationError as e:
            raise self._fail_validation(e) from None
        try:
            plan = self.server.store.replace_plan(pid, r.version, r.title, r.start_date, r.tasks)
        except store_mod.NotFound:
            raise ApiError(404, "not_found", "Project not found") from None
        except store_mod.VersionConflict as e:
            raise self._conflict(e) from None
        self._json(200, plan)

    def _conflict(self, e):
        return ApiError(409, "version_conflict", "This plan changed elsewhere",
                        extra={"current_version": e.current_version})

    def _delete(self, pid):
        vals = self.query.get("version", [])
        if len(vals) != 1 or not re.fullmatch(r"[0-9]{1,12}", vals[0]):
            raise ApiError(422, "validation_failed", "Request validation failed", [
                {"field": "version", "code": "required" if not vals else "type",
                 "message": "version query parameter must be a single integer"}])
        try:
            self.server.store.delete_plan(pid, int(vals[0]))
        except store_mod.NotFound:
            raise ApiError(404, "not_found", "Project not found") from None
        except store_mod.VersionConflict as e:
            raise self._conflict(e) from None
        self._send(204)


class PlannerServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False  # on Windows reuse would permit port hijacking

    def server_close(self):
        super().server_close()
        st = getattr(self, "store", None)
        if st is not None:
            st.close()
            self.store = None


def make_server(data_dir, port=0):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    srv = PlannerServer(("127.0.0.1", port), Handler)
    try:
        srv.port = srv.server_address[1]
        srv.store = store_mod.Store(data_dir / "release_planner.sqlite3")
    except BaseException:
        srv.server_close()
        raise
    return srv
