"""CRUD for :class:`Organization`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, Organization
from mdk_bot.core.schemas import OrganizationCreate, OrganizationRead, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["organizations"], dependencies=[AuthDep])


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    session: AsyncSession = SessionDep, search: str | None = None
) -> list[Organization]:
    stmt = select(Organization).order_by(Organization.created_at.desc())
    if search:
        stmt = stmt.where(Organization.name.ilike(f"%{search}%"))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate, session: AsyncSession = SessionDep
) -> Organization:
    org = Organization(**payload.model_dump())
    session.add(org)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="organization.create",
        entity_type="organization",
        entity_id=str(org.id),
        payload={"name": org.name},
    )
    return org


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(org_id: UUID, session: AsyncSession = SessionDep) -> Organization:
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return org


@router.put("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: UUID, payload: OrganizationUpdate, session: AsyncSession = SessionDep
) -> Organization:
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(org, key, value)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="organization.update",
        entity_type="organization",
        entity_id=str(org.id),
        payload=changes,
    )
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(org_id: UUID, session: AsyncSession = SessionDep) -> None:
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    await session.delete(org)
    await record(
        session,
        actor=AuditActor.USER,
        action="organization.delete",
        entity_type="organization",
        entity_id=str(org_id),
    )
