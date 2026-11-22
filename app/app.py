"""ticket-api - Helpdesk Ticketing service (Track B: EC2 + Docker + ECR).

A small Flask REST API that stores tickets in SQLite. The database file lives
on a Docker volume (/data), so tickets survive container restarts and image
updates.

Endpoints
---------
GET    /health                    service + database check
POST   /tickets                   create a ticket            -> 201
GET    /tickets                   list (?status=OPEN&limit=20)
GET    /tickets/<ticket_id>       read one ticket            -> 200 / 404
PUT    /tickets/<ticket_id>       update (partial)           -> 200 / 404
DELETE /tickets/<ticket_id>       delete                     -> 204 / 404
"""

import os
import re
import socket
import sqlite3
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request

VERSION = os.environ.get("APP_VERSION", "dev")
DB_PATH = os.environ.get("DB_PATH", "/data/tickets.db")

CATEGORIES = {"HARDWARE", "SOFTWARE", "NETWORK", "ACCOUNT", "OTHER"}
PRIORITIES = {"LOW", "MEDIUM", "HIGH", "URGENT"}
STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}
UPDATABLE = ("title", "description", "category", "priority", "status")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id       TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    requester_email TEXT NOT NULL,
    category        TEXT NOT NULL,
    priority        TEXT NOT NULL DEFAULT 'MEDIUM',
    status          TEXT NOT NULL DEFAULT 'OPEN',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
"""

# API field name  <->  database column
FIELDS = {
    "ticketId": "ticket_id",
    "title": "title",
    "description": "description",
    "requesterEmail": "requester_email",
    "category": "category",
    "priority": "priority",
    "status": "status",
    "createdAt": "created_at",
    "updatedAt": "updated_at",
}


class ApiError(Exception):
    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status, self.message, self.details = status, message, details


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_api(row):
    return {api: row[col] for api, col in FIELDS.items()}


def validate(data, partial=False):
    """Check ticket fields; partial=True is used for PUT (update)."""
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    errors, clean = {}, {}

    def text(field, lo, hi, required):
        if field not in data:
            if required:
                errors[field] = "is required"
            return
        v = data[field]
        if not isinstance(v, str) or not lo <= len(v.strip()) <= hi:
            errors[field] = f"must be a string of {lo}-{hi} characters"
        else:
            clean[field] = v.strip()

    def enum(field, allowed, required):
        if field not in data:
            if required:
                errors[field] = "is required"
            return
        v = data[field]
        if not isinstance(v, str) or v.upper() not in allowed:
            errors[field] = f"must be one of {sorted(allowed)}"
        else:
            clean[field] = v.upper()

    text("title", 3, 120, required=not partial)
    text("description", 0, 2000, required=False)
    enum("category", CATEGORIES, required=not partial)
    enum("priority", PRIORITIES, required=False)

    if partial:
        enum("status", STATUSES, required=False)
        unknown = set(data) - set(UPDATABLE)
        if unknown:
            errors["_unknown"] = f"fields cannot be updated: {sorted(unknown)}"
    else:
        email = data.get("requesterEmail")
        if not isinstance(email, str) or not EMAIL_RE.match(email.strip()):
            errors["requesterEmail"] = "must be a valid email address"
        else:
            clean["requesterEmail"] = email.strip().lower()

    if errors:
        raise ApiError(400, "Validation failed", errors)
    return clean


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DB_PATH

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    with app.app_context():
        os.makedirs(os.path.dirname(os.path.abspath(app.config["DB_PATH"])), exist_ok=True)
        db().executescript(SCHEMA)
        db().commit()

    def check_id(ticket_id):
        if not UUID_RE.match(ticket_id):
            raise ApiError(400, "ticketId must be a valid UUID")

    def fetch(ticket_id):
        row = db().execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        if row is None:
            raise ApiError(404, f"Ticket {ticket_id} not found")
        return row

    def body():
        data = request.get_json(silent=True)
        if data is None:
            raise ApiError(400, "Request body must be valid JSON")
        return data

    # ------------------------------------------------------------------ routes
    @app.get("/health")
    def health():
        count = db().execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        return jsonify(status="ok", service="ticket-api", version=VERSION,
                       host=socket.gethostname(), database="sqlite", tickets=count)

    @app.post("/tickets")
    def create_ticket():
        f = validate(body())
        ts = now_iso()
        ticket = {
            "ticketId": str(uuid.uuid4()),
            "title": f["title"],
            "description": f.get("description", ""),
            "requesterEmail": f["requesterEmail"],
            "category": f["category"],
            "priority": f.get("priority", "MEDIUM"),
            "status": "OPEN",
            "createdAt": ts,
            "updatedAt": ts,
        }
        cols = ", ".join(FIELDS.values())
        marks = ", ".join("?" for _ in FIELDS)
        db().execute(f"INSERT INTO tickets ({cols}) VALUES ({marks})",
                     [ticket[k] for k in FIELDS])
        db().commit()
        return jsonify(ticket), 201

    @app.get("/tickets")
    def list_tickets():
        try:
            limit = max(1, min(int(request.args.get("limit", 50)), 100))
        except ValueError:
            raise ApiError(400, "limit must be an integer")
        sql, params = "SELECT * FROM tickets", []
        status = request.args.get("status")
        if status:
            if status.upper() not in STATUSES:
                raise ApiError(400, f"status must be one of {sorted(STATUSES)}")
            sql += " WHERE status = ?"
            params.append(status.upper())
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        items = [to_api(r) for r in db().execute(sql, params).fetchall()]
        return jsonify(count=len(items), items=items)

    @app.get("/tickets/<ticket_id>")
    def get_ticket(ticket_id):
        check_id(ticket_id)
        return jsonify(to_api(fetch(ticket_id)))

    @app.put("/tickets/<ticket_id>")
    def update_ticket(ticket_id):
        check_id(ticket_id)
        f = validate(body(), partial=True)
        if not f:
            raise ApiError(400, f"Provide at least one of {list(UPDATABLE)}")
        fetch(ticket_id)  # 404 if missing
        f["updatedAt"] = now_iso()
        assignments = ", ".join(f"{FIELDS[k]} = ?" for k in f)
        db().execute(f"UPDATE tickets SET {assignments} WHERE ticket_id = ?",
                     [*f.values(), ticket_id])
        db().commit()
        return jsonify(to_api(fetch(ticket_id)))

    @app.delete("/tickets/<ticket_id>")
    def delete_ticket(ticket_id):
        check_id(ticket_id)
        cur = db().execute("DELETE FROM tickets WHERE ticket_id = ?", (ticket_id,))
        db().commit()
        if cur.rowcount == 0:
            raise ApiError(404, f"Ticket {ticket_id} not found")
        return "", 204

    # ------------------------------------------------------------------ errors
    @app.errorhandler(ApiError)
    def api_error(err):
        payload = {"error": err.message}
        if err.details:
            payload["details"] = err.details
        return jsonify(payload), err.status

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify(error="Route not found"), 404

    @app.errorhandler(405)
    def not_allowed(_err):
        return jsonify(error="Method not allowed"), 405

    return app


app = create_app()
