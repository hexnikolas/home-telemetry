from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.future import select
from app.models import Observation
from fastapi import HTTPException
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from schemas.observation_schemas import ObservationUpdate


async def get_observation(db: AsyncSession, observation_id: UUID) -> Observation:
    statement = (
        select(Observation)
        .where(Observation.id == observation_id)
    )
    result = await db.execute(statement)
    observation = result.scalars().first()

    if not observation:
        raise HTTPException(status_code=404, detail=f"Observation {observation_id} not found")

    return observation


async def get_all_observations(db: AsyncSession) -> List[Observation]:
    statement = select(Observation)

    result = await db.execute(statement)
    observations = result.scalars().all()

    if not observations:
        raise HTTPException(status_code=404, detail="No observations were found")

    return observations


async def create_observation(db: AsyncSession, observation_in) -> Observation:
    new_observation = Observation(**observation_in.model_dump())
    try:
        db.add(new_observation)
        await db.commit()
        await db.refresh(new_observation)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating observation: {str(e)}")

    return new_observation


async def create_observations_bulk(db: AsyncSession, observations_in: list) -> List[Observation]:
    new_observations = [Observation(**obs.model_dump()) for obs in observations_in]
    try:
        db.add_all(new_observations)
        await db.commit()
        for obs in new_observations:
            await db.refresh(obs)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating observations: {str(e)}")

    return new_observations


async def update_observation(db: AsyncSession, db_observation: Observation, observation_in: ObservationUpdate) -> Observation:
    update_data = observation_in.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_observation, key, value)

    try:
        await db.commit()
        await db.refresh(db_observation)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return db_observation


async def delete_observation(db: AsyncSession, db_observation: Observation):
    try:
        await db.delete(db_observation)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error deleting observation: {str(e)}")
