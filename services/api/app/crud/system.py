from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.future import select
from app.models import System
from fastapi import HTTPException
from uuid import UUID
from typing import List
from schemas.system_schemas import SystemUpdate

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


async def get_all_systems(db: AsyncSession) -> List[System]:
    """Get all systems with optional filters and their parent system ID (if any)."""

    statement = select(System)

    result = await db.execute(statement)
    systems = result.scalars().all()

    if not systems:
        raise HTTPException(status_code=404, detail="No systems were found")

    return systems


async def create_system(db: AsyncSession, system_in) -> System:
    media_links = [str(url) for url in system_in.media_links] if system_in.media_links else None

    """Create a new system in the database."""
    new_system = System(**system_in.model_dump(exclude={'media_links'}), media_links=media_links)
    try:
        db.add(new_system)
        await db.commit()
        await db.refresh(new_system)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating system: {str(e)}")
    
    return new_system

async def update_system(db: AsyncSession, db_system: System, system_in: SystemUpdate) -> System:
    update_data = system_in.model_dump(exclude_unset=True)

    # convert HttpUrl -> str if provided
    if "media_links" in update_data and update_data["media_links"] is not None:
        update_data["media_links"] = [str(u) for u in update_data["media_links"]]

    for key, value in update_data.items():
        setattr(db_system, key, value)

    try:
        await db.commit()
        await db.refresh(db_system)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return db_system



async def delete_system(db: AsyncSession, db_system: System):
    try:
        await db.delete(db_system)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error deleting system: {str(e)}")