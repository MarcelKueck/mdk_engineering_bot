"""API CRUD smoke tests for every entity router + audit-log emission."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mdk_bot.core.models import AuditLog


async def test_healthz_unauthenticated(client: AsyncClient) -> None:
    # Drop the internal token so we exercise the unauthenticated path.
    resp = await client.get("/healthz", headers={"X-Internal-Token": ""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["db"] == "ok"


async def test_api_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/persons", headers={"X-Internal-Token": ""})
    assert resp.status_code == 401


async def test_persons_crud_and_audit(
    client: AsyncClient, sessionmaker_: async_sessionmaker[AsyncSession]
) -> None:
    resp = await client.post(
        "/api/v1/persons", json={"name": "Marcel Kück", "email": "marcel@example.com"}
    )
    assert resp.status_code == 201, resp.text
    person = resp.json()
    person_id = person["id"]

    resp = await client.get("/api/v1/persons")
    assert resp.status_code == 200
    assert any(p["id"] == person_id for p in resp.json())

    resp = await client.put(f"/api/v1/persons/{person_id}", json={"phone": "+49 89 …"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+49 89 …"

    resp = await client.delete(f"/api/v1/persons/{person_id}")
    assert resp.status_code == 204

    async with sessionmaker_() as s:
        rows = (await s.execute(select(AuditLog))).scalars().all()
        actions = {r.action for r in rows}
    assert {"person.create", "person.update", "person.delete"} <= actions


async def test_organizations_crud(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/organizations",
        json={"name": "Acme GmbH", "legal_form": "GmbH", "vat_id": "DE123"},
    )
    assert resp.status_code == 201
    org = resp.json()
    resp = await client.get(f"/api/v1/organizations/{org['id']}")
    assert resp.status_code == 200


async def test_projects_crud_with_status_badge(client: AsyncClient) -> None:
    org = (await client.post("/api/v1/organizations", json={"name": "Acme"})).json()
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Migration",
            "customer_org_id": org["id"],
            "status": "active",
            "hourly_rate": 120.0,
        },
    )
    assert resp.status_code == 201
    project = resp.json()
    assert project["status"] == "active"


async def test_tasks_crud_and_transitions(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/tasks", json={"title": "Write tests", "priority": 2})
    assert resp.status_code == 201
    task = resp.json()

    resp = await client.post(f"/api/v1/tasks/{task['id']}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"

    skip_task = (await client.post("/api/v1/tasks", json={"title": "Skip me"})).json()
    resp = await client.post(f"/api/v1/tasks/{skip_task['id']}/skip")
    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"


async def test_anchor_set_and_list(client: AsyncClient) -> None:
    resp = await client.put(
        "/api/v1/anchors/vertragsablauf_berufshaftpflicht",
        json={"date_value": "2027-01-15"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["date_value"] == "2027-01-15"

    resp = await client.get("/api/v1/anchors")
    assert resp.status_code == 200
    assert any(a["field_name"] == "vertragsablauf_berufshaftpflicht" for a in resp.json())


async def test_audit_log_endpoint(client: AsyncClient) -> None:
    await client.post("/api/v1/persons", json={"name": "Audit Probe"})
    resp = await client.get("/api/v1/audit")
    assert resp.status_code == 200
    rows = resp.json()
    assert any(r["action"] == "person.create" for r in rows)


async def test_login_sets_cookie(client: AsyncClient) -> None:
    resp = await client.post(
        "/login",
        data={"token": "test-web-token"},
        follow_redirects=False,
        headers={"X-Internal-Token": ""},
    )
    assert resp.status_code == 302
    assert any("mdk_session=" in v for k, v in resp.headers.items() if k.lower() == "set-cookie")


async def test_login_rejects_bad_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/login",
        data={"token": "wrong"},
        follow_redirects=False,
        headers={"X-Internal-Token": ""},
    )
    assert resp.status_code == 401
