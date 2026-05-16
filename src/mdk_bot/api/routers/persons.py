"""CRUD for :class:`Person`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, Person
from mdk_bot.core.schemas import PersonCreate, PersonRead, PersonUpdate

router = APIRouter(prefix="/persons", tags=["persons"], dependencies=[AuthDep])


@router.get("", response_model=list[PersonRead])
async def list_persons(
    session: AsyncSession = SessionDep, search: str | None = None
) -> list[Person]:
    stmt = select(Person).order_by(Person.created_at.desc())
    if search:
        stmt = stmt.where(Person.name.ilike(f"%{search}%"))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
async def create_person(
    payload: PersonCreate, session: AsyncSession = SessionDep
) -> Person:
    person = Person(**payload.model_dump())
    session.add(person)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="person.create",
        entity_type="person",
        entity_id=str(person.id),
        payload={"name": person.name},
    )
    return person


@router.get("/{person_id}", response_model=PersonRead)
async def get_person(person_id: UUID, session: AsyncSession = SessionDep) -> Person:
    person = await session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="person not found")
    return person


@router.put("/{person_id}", response_model=PersonRead)
async def update_person(
    person_id: UUID, payload: PersonUpdate, session: AsyncSession = SessionDep
) -> Person:
    person = await session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="person not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(person, key, value)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="person.update",
        entity_type="person",
        entity_id=str(person.id),
        payload=changes,
    )
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(person_id: UUID, session: AsyncSession = SessionDep) -> None:
    person = await session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="person not found")
    await session.delete(person)
    await record(
        session,
        actor=AuditActor.USER,
        action="person.delete",
        entity_type="person",
        entity_id=str(person_id),
    )
