from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import System
from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from uuid import UUID

async def get_system(db: AsyncSession, system_id: UUID) -> System:
    """Get a single system by its ID, and include its parent system if it has one."""

    statement = (
        select(System)
        .where(System.id == system_id)
    )
    result = await db.execute(statement)
    system = result.scalars().first()

    if not system:
        raise HTTPException(status_code=404, detail=f"System {system_id} not found")

    return system

