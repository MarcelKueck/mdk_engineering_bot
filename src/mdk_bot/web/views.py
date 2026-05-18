"""Web UI routes — login form + HTMX pages.

Pages use Tailwind via CDN and HTMX for in-place updates. Routes operate
on the same DB session as the API and emit the same audit-log entries.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import SessionDep
from mdk_bot.core.audit import record
from mdk_bot.core.auth import (
    SESSION_COOKIE,
    check_login_token,
    issue_session,
    verify_session,
)
from mdk_bot.core.models import (
    AnchorDate,
    AuditActor,
    AuditLog,
    Obligation,
    ObligationInstance,
    ObligationInstanceStatus,
    Organization,
    Person,
    Project,
    ProjectStatus,
    Task,
    TaskStatus,
)
from mdk_bot.core.time import now_utc, today_local
from mdk_bot.web.assets import TEMPLATE_DIR

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _require_login(request: Request) -> str:
    """Read the session cookie; redirect to /web/login if missing/invalid."""
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="login required",
            headers={"Location": "/web/login"},
        )
    sub = verify_session(cookie)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="invalid session",
            headers={"Location": "/web/login"},
        )
    return sub


@router.get("/web/login", response_class=HTMLResponse)
async def login_form(request: Request) -> Response:
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login(request: Request, token: str = Form(...)) -> Response:
    if not check_login_token(token):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid token."},
            status_code=401,
        )
    response = RedirectResponse(url="/web/", status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        issue_session(),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=60 * 60 * 24 * 14,
    )
    return response


@router.post("/logout")
async def logout() -> Response:
    response = RedirectResponse(url="/web/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ---------- Dashboard


@router.get("/web/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = SessionDep) -> Response:
    _require_login(request)
    counts = {
        "persons": await session.scalar(select(func.count()).select_from(Person)),
        "organizations": await session.scalar(select(func.count()).select_from(Organization)),
        "projects_active": await session.scalar(
            select(func.count()).select_from(Project).where(Project.status == ProjectStatus.ACTIVE)
        ),
        "tasks_open": await session.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]))
        ),
    }
    cutoff = today_local() + timedelta(days=7)
    upcoming_q = await session.execute(
        select(ObligationInstance)
        .where(ObligationInstance.due_date <= cutoff)
        .where(
            ObligationInstance.status.in_(
                [
                    ObligationInstanceStatus.PENDING,
                    ObligationInstanceStatus.NOTIFIED,
                    ObligationInstanceStatus.ESCALATED,
                ]
            )
        )
        .order_by(ObligationInstance.due_date.asc())
        .limit(10)
    )
    upcoming = list(upcoming_q.scalars().all())
    audit_q = await session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10))
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "counts": counts,
            "upcoming": upcoming,
            "audit": list(audit_q.scalars().all()),
        },
    )


# ---------- Persons


@router.get("/web/persons", response_class=HTMLResponse)
async def persons_page(
    request: Request, session: AsyncSession = SessionDep, search: str | None = None
) -> Response:
    _require_login(request)
    stmt = select(Person).order_by(Person.name)
    if search:
        stmt = stmt.where(Person.name.ilike(f"%{search}%"))
    rows = (await session.execute(stmt)).scalars().all()
    return templates.TemplateResponse(
        request, "persons/index.html", {"persons": list(rows), "search": search or ""}
    )


@router.post("/web/persons", response_class=HTMLResponse)
async def persons_create(
    request: Request,
    session: AsyncSession = SessionDep,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
) -> Response:
    _require_login(request)
    person = Person(name=name, email=email or None, phone=phone or None)
    session.add(person)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="person.create",
        entity_type="person",
        entity_id=str(person.id),
        payload={"name": name},
    )
    rows = (await session.execute(select(Person).order_by(Person.name))).scalars().all()
    return templates.TemplateResponse(request, "persons/_list.html", {"persons": list(rows)})


@router.delete("/web/persons/{person_id}", response_class=HTMLResponse)
async def persons_delete(
    person_id: UUID, request: Request, session: AsyncSession = SessionDep
) -> Response:
    _require_login(request)
    person = await session.get(Person, person_id)
    if person is not None:
        await session.delete(person)
        await record(
            session,
            actor=AuditActor.USER,
            action="person.delete",
            entity_type="person",
            entity_id=str(person_id),
        )
    rows = (await session.execute(select(Person).order_by(Person.name))).scalars().all()
    return templates.TemplateResponse(request, "persons/_list.html", {"persons": list(rows)})


# ---------- Organizations


@router.get("/web/organizations", response_class=HTMLResponse)
async def orgs_page(
    request: Request, session: AsyncSession = SessionDep, search: str | None = None
) -> Response:
    _require_login(request)
    stmt = select(Organization).order_by(Organization.name)
    if search:
        stmt = stmt.where(Organization.name.ilike(f"%{search}%"))
    rows = (await session.execute(stmt)).scalars().all()
    return templates.TemplateResponse(
        request,
        "organizations/index.html",
        {"organizations": list(rows), "search": search or ""},
    )


@router.post("/web/organizations", response_class=HTMLResponse)
async def orgs_create(
    request: Request,
    session: AsyncSession = SessionDep,
    name: str = Form(...),
    legal_form: str = Form(""),
    vat_id: str = Form(""),
) -> Response:
    _require_login(request)
    org = Organization(name=name, legal_form=legal_form or None, vat_id=vat_id or None)
    session.add(org)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="organization.create",
        entity_type="organization",
        entity_id=str(org.id),
        payload={"name": name},
    )
    rows = (await session.execute(select(Organization).order_by(Organization.name))).scalars().all()
    return templates.TemplateResponse(
        request, "organizations/_list.html", {"organizations": list(rows)}
    )


@router.delete("/web/organizations/{org_id}", response_class=HTMLResponse)
async def orgs_delete(
    org_id: UUID, request: Request, session: AsyncSession = SessionDep
) -> Response:
    _require_login(request)
    org = await session.get(Organization, org_id)
    if org is not None:
        await session.delete(org)
        await record(
            session,
            actor=AuditActor.USER,
            action="organization.delete",
            entity_type="organization",
            entity_id=str(org_id),
        )
    rows = (await session.execute(select(Organization).order_by(Organization.name))).scalars().all()
    return templates.TemplateResponse(
        request, "organizations/_list.html", {"organizations": list(rows)}
    )


# ---------- Projects


@router.get("/web/projects", response_class=HTMLResponse)
async def projects_page(
    request: Request, session: AsyncSession = SessionDep, search: str | None = None
) -> Response:
    _require_login(request)
    stmt = select(Project).order_by(Project.name)
    if search:
        stmt = stmt.where(Project.name.ilike(f"%{search}%"))
    rows = (await session.execute(stmt)).scalars().all()
    orgs = (await session.execute(select(Organization).order_by(Organization.name))).scalars().all()
    return templates.TemplateResponse(
        request,
        "projects/index.html",
        {
            "projects": list(rows),
            "organizations": list(orgs),
            "statuses": [s.value for s in ProjectStatus],
            "search": search or "",
        },
    )


@router.post("/web/projects", response_class=HTMLResponse)
async def projects_create(
    request: Request,
    session: AsyncSession = SessionDep,
    name: str = Form(...),
    customer_org_id: str = Form(""),
    status_value: str = Form("lead"),
    hourly_rate: str = Form(""),
) -> Response:
    _require_login(request)
    org_uuid: UUID | None = UUID(customer_org_id) if customer_org_id else None
    rate: float | None = float(hourly_rate) if hourly_rate else None
    project = Project(
        name=name,
        customer_org_id=org_uuid,
        status=ProjectStatus(status_value),
        hourly_rate=rate,
    )
    session.add(project)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="project.create",
        entity_type="project",
        entity_id=str(project.id),
        payload={"name": name},
    )
    rows = (await session.execute(select(Project).order_by(Project.name))).scalars().all()
    return templates.TemplateResponse(request, "projects/_list.html", {"projects": list(rows)})


# ---------- Tasks


@router.get("/web/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request, session: AsyncSession = SessionDep) -> Response:
    _require_login(request)
    rows = (
        (
            await session.execute(
                select(Task).order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    projects = (await session.execute(select(Project).order_by(Project.name))).scalars().all()
    return templates.TemplateResponse(
        request,
        "tasks/index.html",
        {"tasks": list(rows), "projects": list(projects)},
    )


@router.post("/web/tasks", response_class=HTMLResponse)
async def tasks_create(
    request: Request,
    session: AsyncSession = SessionDep,
    title: str = Form(...),
    due_date: str = Form(""),
    priority: int = Form(3),
    project_id: str = Form(""),
) -> Response:
    _require_login(request)
    due: date | None = date.fromisoformat(due_date) if due_date else None
    proj_uuid: UUID | None = UUID(project_id) if project_id else None
    task = Task(title=title, due_date=due, priority=priority, project_id=proj_uuid)
    session.add(task)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="task.create",
        entity_type="task",
        entity_id=str(task.id),
        payload={"title": title},
    )
    rows = (
        (
            await session.execute(
                select(Task).order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return templates.TemplateResponse(request, "tasks/_list.html", {"tasks": list(rows)})


@router.post("/web/tasks/{task_id}/complete", response_class=HTMLResponse)
async def tasks_complete(
    task_id: UUID, request: Request, session: AsyncSession = SessionDep
) -> Response:
    _require_login(request)
    task = await session.get(Task, task_id)
    if task is not None:
        task.status = TaskStatus.DONE
        task.completed_at = now_utc()
        await session.flush()
        await record(
            session,
            actor=AuditActor.USER,
            action="task.complete",
            entity_type="task",
            entity_id=str(task.id),
        )
    rows = (
        (
            await session.execute(
                select(Task).order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return templates.TemplateResponse(request, "tasks/_list.html", {"tasks": list(rows)})


# ---------- Obligations


@router.get("/web/obligations", response_class=HTMLResponse)
async def obligations_page(request: Request, session: AsyncSession = SessionDep) -> Response:
    _require_login(request)
    obligations: list[Obligation] = list(
        (await session.execute(select(Obligation).order_by(Obligation.category, Obligation.id)))
        .scalars()
        .all()
    )
    cutoff = today_local() + timedelta(days=90)
    upcoming = list(
        (
            await session.execute(
                select(ObligationInstance)
                .where(ObligationInstance.due_date <= cutoff)
                .order_by(ObligationInstance.due_date.asc())
            )
        )
        .scalars()
        .all()
    )
    return templates.TemplateResponse(
        request,
        "obligations/index.html",
        {"obligations": obligations, "upcoming": upcoming},
    )


# ---------- Anchors


@router.get("/web/anchors", response_class=HTMLResponse)
async def anchors_page(request: Request, session: AsyncSession = SessionDep) -> Response:
    _require_login(request)
    rows = (
        (await session.execute(select(AnchorDate).order_by(AnchorDate.field_name))).scalars().all()
    )
    return templates.TemplateResponse(request, "anchors/index.html", {"anchors": list(rows)})


@router.post("/web/anchors", response_class=HTMLResponse)
async def anchors_set(
    request: Request,
    session: AsyncSession = SessionDep,
    field_name: str = Form(...),
    date_value: str = Form(...),
) -> Response:
    _require_login(request)
    parsed = date.fromisoformat(date_value)
    anchor: Any = await session.get(AnchorDate, field_name)
    if anchor is None:
        anchor = AnchorDate(field_name=field_name, date_value=parsed)
        session.add(anchor)
    else:
        anchor.date_value = parsed
        anchor.set_at = now_utc()
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="anchor.set",
        entity_type="anchor_date",
        entity_id=field_name,
        payload={"date_value": parsed.isoformat()},
    )
    rows = (
        (await session.execute(select(AnchorDate).order_by(AnchorDate.field_name))).scalars().all()
    )
    return templates.TemplateResponse(request, "anchors/_list.html", {"anchors": list(rows)})
