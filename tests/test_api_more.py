"""Extra coverage: update/delete paths on every router, anchor + pause API."""

from __future__ import annotations

from datetime import UTC, timedelta

from httpx import AsyncClient

from mdk_bot.core.time import now_utc


async def test_organization_update_and_delete(client: AsyncClient) -> None:
    org = (await client.post("/api/v1/organizations", json={"name": "Acme"})).json()
    resp = await client.put(
        f"/api/v1/organizations/{org['id']}", json={"website": "https://acme.de"}
    )
    assert resp.status_code == 200
    assert resp.json()["website"] == "https://acme.de"

    resp = await client.delete(f"/api/v1/organizations/{org['id']}")
    assert resp.status_code == 204
    resp = await client.get(f"/api/v1/organizations/{org['id']}")
    assert resp.status_code == 404


async def test_project_update_and_delete(client: AsyncClient) -> None:
    project = (await client.post("/api/v1/projects", json={"name": "Mig"})).json()
    resp = await client.put(f"/api/v1/projects/{project['id']}", json={"status": "active"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
    resp = await client.delete(f"/api/v1/projects/{project['id']}")
    assert resp.status_code == 204


async def test_task_update_and_delete_and_list_filter(client: AsyncClient) -> None:
    t = (await client.post("/api/v1/tasks", json={"title": "X"})).json()
    resp = await client.put(f"/api/v1/tasks/{t['id']}", json={"priority": 1})
    assert resp.status_code == 200
    assert resp.json()["priority"] == 1
    resp = await client.get("/api/v1/tasks", params={"status_filter": "todo"})
    assert resp.status_code == 200
    resp = await client.delete(f"/api/v1/tasks/{t['id']}")
    assert resp.status_code == 204


async def test_404_paths(client: AsyncClient) -> None:
    fake = "00000000-0000-0000-0000-000000000000"
    assert (await client.get(f"/api/v1/persons/{fake}")).status_code == 404
    assert (await client.get(f"/api/v1/organizations/{fake}")).status_code == 404
    assert (await client.get(f"/api/v1/projects/{fake}")).status_code == 404
    assert (await client.get(f"/api/v1/tasks/{fake}")).status_code == 404
    assert (await client.get("/api/v1/obligations/nope")).status_code == 404
    assert (await client.post(f"/api/v1/obligation-instances/{fake}/done")).status_code == 404
    assert (await client.post(f"/api/v1/obligation-instances/{fake}/skip")).status_code == 404
    assert (await client.delete(f"/api/v1/persons/{fake}")).status_code == 404


async def test_pause_get_set_clear(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/pause")
    assert resp.status_code == 200
    assert resp.json()["paused_until"] is None
    until = (now_utc().astimezone(UTC) + timedelta(hours=2)).isoformat()
    resp = await client.put("/api/v1/pause", json={"paused_until": until})
    assert resp.status_code == 200
    resp = await client.put("/api/v1/pause", json={"paused_until": None})
    assert resp.status_code == 200
    assert resp.json()["paused_until"] is None


async def test_adhoc_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/obligations/adhoc")
    assert resp.status_code == 200
    assert resp.json() == []
