"""CRUD for :class:`Project`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, Project
from mdk_bot.core.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[AuthDep])


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: AsyncSession = SessionDep, search: str | None = None
) -> list[Project]:
    stmt = select(Project).order_by(Project.created_at.desc())
    if search:
        stmt = stmt.where(Project.name.ilike(f"%{search}%"))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, session: AsyncSession = SessionDep) -> Project:
    project = Project(**payload.model_dump())
    session.add(project)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="project.create",
        entity_type="project",
        entity_id=str(project.id),
        payload={"name": project.name, "status": project.status.value},
    )
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: UUID, session: AsyncSession = SessionDep) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID, payload: ProjectUpdate, session: AsyncSession = SessionDep
) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(project, key, value)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="project.update",
        entity_type="project",
        entity_id=str(project.id),
        payload={k: str(v) if hasattr(v, "value") else v for k, v in changes.items()},
    )
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: UUID, session: AsyncSession = SessionDep) -> None:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    await session.delete(project)
    await record(
        session,
        actor=AuditActor.USER,
        action="project.delete",
        entity_type="project",
        entity_id=str(project_id),
    )
