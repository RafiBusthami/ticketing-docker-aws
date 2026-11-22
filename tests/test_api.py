"""Unit tests for ticket-api (Flask test client + temporary SQLite file)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app import create_app  # noqa: E402

VALID = {
    "title": "Projector in lab 3 not turning on",
    "description": "No power light after plugging in.",
    "requesterEmail": "Rafi@Example.com",
    "category": "hardware",
    "priority": "high",
}
MISSING = "00000000-0000-4000-8000-000000000000"


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "test.db")).test_client()


def create(client, **overrides):
    resp = client.post("/tickets", json={**VALID, **overrides})
    assert resp.status_code == 201
    return resp.get_json()


def test_health(client):
    data = client.get("/health").get_json()
    assert data["status"] == "ok" and data["tickets"] == 0


def test_create_sets_defaults_and_normalises(client):
    t = create(client)
    assert t["status"] == "OPEN"
    assert t["category"] == "HARDWARE" and t["priority"] == "HIGH"
    assert t["requesterEmail"] == "rafi@example.com"
    assert t["createdAt"] == t["updatedAt"]


def test_create_default_priority(client):
    body = {k: v for k, v in VALID.items() if k != "priority"}
    assert client.post("/tickets", json=body).get_json()["priority"] == "MEDIUM"


def test_create_rejects_invalid_payload(client):
    resp = client.post("/tickets", json={"title": "x", "category": "food"})
    assert resp.status_code == 400
    assert set(resp.get_json()["details"]) >= {"title", "category", "requesterEmail"}


def test_create_rejects_non_json(client):
    resp = client.post("/tickets", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_read_ticket(client):
    t = create(client)
    resp = client.get(f"/tickets/{t['ticketId']}")
    assert resp.status_code == 200 and resp.get_json() == t


def test_read_missing_and_bad_id(client):
    assert client.get(f"/tickets/{MISSING}").status_code == 404
    assert client.get("/tickets/abc").status_code == 400


def test_update_ticket(client):
    t = create(client)
    resp = client.put(f"/tickets/{t['ticketId']}", json={"status": "in_progress", "priority": "urgent"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "IN_PROGRESS" and data["priority"] == "URGENT"
    assert data["title"] == t["title"]


def test_update_rejects_readonly_fields_and_empty_body(client):
    t = create(client)
    assert client.put(f"/tickets/{t['ticketId']}", json={"createdAt": "x"}).status_code == 400
    assert client.put(f"/tickets/{t['ticketId']}", json={}).status_code == 400


def test_update_missing(client):
    assert client.put(f"/tickets/{MISSING}", json={"status": "closed"}).status_code == 404


def test_delete_ticket(client):
    t = create(client)
    assert client.delete(f"/tickets/{t['ticketId']}").status_code == 204
    assert client.get(f"/tickets/{t['ticketId']}").status_code == 404
    assert client.delete(f"/tickets/{t['ticketId']}").status_code == 404


def test_list_with_status_filter(client):
    a, b = create(client), create(client, title="Second ticket")
    client.put(f"/tickets/{b['ticketId']}", json={"status": "resolved"})
    data = client.get("/tickets?status=open").get_json()
    assert [t["ticketId"] for t in data["items"]] == [a["ticketId"]]
    assert client.get("/tickets").get_json()["count"] == 2
    assert client.get("/tickets?status=nope").status_code == 400


def test_data_persists_across_app_instances(tmp_path):
    path = str(tmp_path / "persist.db")
    t = create(create_app(path).test_client())
    again = create_app(path).test_client()
    assert again.get(f"/tickets/{t['ticketId']}").status_code == 200


def test_unknown_route_and_method(client):
    assert client.get("/nope").status_code == 404
    assert client.patch("/tickets").status_code == 405
