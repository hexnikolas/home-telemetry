from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.future import select
from app.models import Observation
from app.filters import apply_filters, apply_time_range
from fastapi import HTTPException
from uuid import UUID
from typing import List, Optional, Any
from datetime import datetime
from schemas.observation_schemas import ObservationUpdate

# Redis
import json
import redis.asyncio as aioredis
from typing import Optional
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_client: Optional[aioredis.Redis] = None

async def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


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


async def get_all_observations(db: AsyncSession, limit: int = 50, offset: int = 0, filters: dict[str, Any] | None = None, time_start: datetime | None = None, time_end: datetime | None = None) -> List[Observation]:
    statement = select(Observation)
    if filters:
        statement = apply_filters(statement, Observation, filters)
    if time_start is not None:
        statement = apply_time_range(statement, Observation.result_time, time_start, time_end)
    statement = statement.limit(limit).offset(offset)
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

    # Publish to Redis (separate from DB transaction)
    try:
        redis = await get_redis_client()
        channel = f"datastream:{str(new_observation.datastream_id)}"
        data = json.dumps({"id": str(new_observation.id), "datastream_id": str(new_observation.datastream_id), "result_time": new_observation.result_time.isoformat(), "result_complex": new_observation.result_complex, "result_numeric": new_observation.result_numeric, "result_text": new_observation.result_text, "result_boolean": new_observation.result_boolean, "parameters": new_observation.parameters})
        print(f"[DEBUG] Publishing to Redis channel: {channel}\nData: {data}")
        result = await redis.publish(channel, data)
        print(f"[DEBUG] Redis publish result: {result}")
    except Exception as e:
        print(f"Warning: Failed to publish observation to Redis: {str(e)}")
        # Don't raise - observation is already created in DB

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

    # Publish all to Redis (separate from DB transaction)
    try:
        redis = await get_redis_client()
        for obs in new_observations:
            channel = f"datastream:{str(obs.datastream_id)}"
            data = json.dumps({"id": str(obs.id), "datastream_id": str(obs.datastream_id), "result_time": obs.result_time.isoformat(), "result_complex": obs.result_complex, "result_numeric": obs.result_numeric, "result_text": obs.result_text, "result_boolean": obs.result_boolean, "parameters": obs.parameters})
            print(f"[DEBUG] Publishing to Redis channel: {channel}\nData: {data}")
            result = await redis.publish(channel, data)
            print(f"[DEBUG] Redis publish result: {result}")
    except Exception as e:
        print(f"Warning: Failed to publish observations to Redis: {str(e)}")
        # Don't raise - observations are already created in DB

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
