from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import desc
from app.models import System, SystemTypes, Observation
from app.filters import filter_by_keywords
from fastapi import HTTPException
from uuid import UUID
from typing import List, Optional
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



async def get_all_systems(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    system_type: Optional[SystemTypes] = None,
    q: Optional[str] = None
) -> List[System]:
    """Get all systems with pagination, optional system_type filter, and keyword search."""
    statement = select(System)

    if system_type is not None:
        statement = statement.where(System.system_type == system_type)

    if q is not None:
        statement = filter_by_keywords(statement, System, q)

    statement = statement.limit(limit).offset(offset)
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

async def get_system_status(db: AsyncSession, system_id: UUID, online_within_seconds: int) -> bool:
    # check if system exists and eagerly load datastreams
    statement = (
        select(System)
        .where(System.id == system_id)
        .options(selectinload(System.datastreams))
    )
    result = await db.execute(statement)
    system = result.scalars().first()
    
    if not system:
        raise HTTPException(status_code=404, detail=f"System {system_id} not found")

    # get the datastreams of the system
    datastreams = system.datastreams
    if not datastreams:
        raise HTTPException(status_code=404, detail=f"No datastreams found for system {system_id}")
    
    # get the latest observation for these datastreams
    datastream_ids = [ds.id for ds in datastreams]
    
    # Query for the latest observation across all datastreams
    statement = (
        select(Observation)
        .where(Observation.datastream_id.in_(datastream_ids))
        .order_by(desc(Observation.result_time))
        .limit(1)
    )
    result = await db.execute(statement)
    latest_observation = result.scalars().first()
    
    if not latest_observation:
        raise HTTPException(status_code=404, detail=f"No observations found for datastreams of system {system_id}")
    
    # find how much time has passed since the latest observation
    from datetime import datetime, timezone
    latest_observation_time = latest_observation.result_time
    now = datetime.now(timezone.utc)
    time_diff = (now - latest_observation_time).total_seconds()
    # logger.info(f"Latest observation time: {latest_observation_time}, now: {now}, time_diff_seconds: {time_diff}")
    # if the time difference is less than the online_within_seconds threshold, return true, otherwise false
    return time_diff <= online_within_seconds