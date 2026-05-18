"""CRUD + state transitions for :class:`Task`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, Task, TaskStatus
from mdk_bot.core.schemas import TaskCreate, TaskRead, TaskUpdate
from mdk_bot.core.time import now_utc

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[AuthDep])


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    session: AsyncSession = SessionDep,
    status_filter: TaskStatus | None = None,
) -> list[Task]:
    stmt = select(Task).order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, session: AsyncSession = SessionDep) -> Task:
    task = Task(**payload.model_dump())
    session.add(task)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="task.create",
        entity_type="task",
        entity_id=str(task.id),
        payload={"title": task.title},
    )
    return task


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: UUID, session: AsyncSession = SessionDep) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.put("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID, payload: TaskUpdate, session: AsyncSession = SessionDep
) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(task, key, value)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="task.update",
        entity_type="task",
        entity_id=str(task.id),
        payload={k: (v.value if hasattr(v, "value") else v) for k, v in changes.items()},
    )
    return task


@router.post("/{task_id}/complete", response_model=TaskRead)
async def complete_task(task_id: UUID, session: AsyncSession = SessionDep) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
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
    return task


@router.post("/{task_id}/skip", response_model=TaskRead)
async def skip_task(task_id: UUID, session: AsyncSession = SessionDep) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    task.status = TaskStatus.SKIPPED
    task.completed_at = now_utc()
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="task.skip",
        entity_type="task",
        entity_id=str(task.id),
    )
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, session: AsyncSession = SessionDep) -> None:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    await session.delete(task)
    await record(
        session,
        actor=AuditActor.USER,
        action="task.delete",
        entity_type="task",
        entity_id=str(task_id),
    )
