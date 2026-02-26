from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.future import select
from app.models import Datastream
from fastapi import HTTPException
from uuid import UUID
from typing import List
from schemas.datastream_schemas import DatastreamUpdate

async def get_datastream(db: AsyncSession, datastream_id: UUID) -> Datastream:
    statement = (
        select(Datastream)
        .where(Datastream.id == datastream_id)
    )
    result = await db.execute(statement)
    datastream = result.scalars().first()

    if not datastream:
        raise HTTPException(status_code=404, detail=f"Datastream {datastream_id} not found")

    return datastream


async def get_all_datastreams(db: AsyncSession) -> List[Datastream]:
    statement = select(Datastream)

    result = await db.execute(statement)
    datastreams = result.scalars().all()

    if not datastreams:
        raise HTTPException(status_code=404, detail="No datastreams were found")

    return datastreams


async def create_datastream(db: AsyncSession, datastream_in) -> Datastream:
    new_datastream = Datastream(**datastream_in.model_dump())
    try:
        db.add(new_datastream)
        await db.commit()
        await db.refresh(new_datastream)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating datastream: {str(e)}")

    return new_datastream

async def update_datastream(db: AsyncSession, db_datastream: Datastream, datastream_in: DatastreamUpdate) -> Datastream:
    update_data = datastream_in.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_datastream, key, value)

    try:
        await db.commit()
        await db.refresh(db_datastream)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return db_datastream


async def delete_datastream(db: AsyncSession, db_datastream: Datastream):
    try:
        await db.delete(db_datastream)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error deleting datastream: {str(e)}")