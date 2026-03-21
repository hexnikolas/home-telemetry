from fastapi import APIRouter, Depends, Query, status, Request
from schemas.observation_schemas import ObservationRead, ObservationUpdate
from app.database import get_db
from app.filters import parse_time_param
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID
from app.rate_limit import limiter
from app.models import Observation

from app.crud.observation import (
    get_all_observations,
    get_observation,
    create_observation,
    create_observations_bulk,
    update_observation,
    delete_observation,
)

router = APIRouter()



@router.get("/", response_model=List[ObservationRead], summary="List Observations", description="List all observations")
@limiter.limit("60/minute")
async def read_observations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    datastream_ids: Optional[List[UUID]] = Query(None, description="Filter observations by datastream IDs"),
    time: Optional[str] = Query(None, description="Filter by time: 'latest', 'timestamp', 'now', or 'timestamp1/timestamp2'. Timestamps in ISO format (2026-02-28T17:01:05)."),
):
    filters = {"datastream_id": datastream_ids}
    
    if time:
        time_start, time_end = parse_time_param(time)
        
        # If "latest" is requested
        if time_start == "latest":
            from sqlalchemy.future import select
            from sqlalchemy import in_
            stmt = select(Observation)
            if filters.get("datastream_id"):
                datastream_ids_list = filters["datastream_id"]
                if isinstance(datastream_ids_list, list):
                    stmt = stmt.where(Observation.datastream_id.in_(datastream_ids_list))
                else:
                    stmt = stmt.where(Observation.datastream_id == datastream_ids_list)
            stmt = stmt.order_by(desc(Observation.result_time)).limit(1)
            result = await db.execute(stmt)
            observations = result.scalars().all()
            if not observations:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="No observations were found")
            return [ObservationRead(**obs.__dict__) for obs in observations]
        else:
            observations_data = await get_all_observations(db, limit=limit, offset=offset, filters=filters, time_start=time_start, time_end=time_end)
    else:
        observations_data = await get_all_observations(db, limit=limit, offset=offset, filters=filters, time_start=None, time_end=None)
    
    return [ObservationRead(**obs.__dict__) for obs in observations_data]


@router.get("/{observation_id}", summary="Get Observation by ID", status_code=status.HTTP_200_OK, response_model=ObservationRead)
@limiter.limit("60/minute")
async def get_an_observation_by_id(
    request: Request,
    observation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    db_observation = await get_observation(db, observation_id=observation_id)

    return ObservationRead(**db_observation.__dict__)


@router.post("/", summary="Create Observation", status_code=status.HTTP_201_CREATED, response_model=ObservationRead)
async def create_a_new_observation(observation_in: ObservationRead, db: AsyncSession = Depends(get_db)):
    created_observation_db = await create_observation(db=db, observation_in=observation_in)

    return ObservationRead(**created_observation_db.__dict__)


@router.post("/bulk", summary="Create Observations in Bulk", status_code=status.HTTP_201_CREATED, response_model=List[ObservationRead])
async def create_observations_in_bulk(observations_in: List[ObservationRead], db: AsyncSession = Depends(get_db)):
    created_observations_db = await create_observations_bulk(db=db, observations_in=observations_in)

    return [ObservationRead(**obs.__dict__) for obs in created_observations_db]


@router.put("/{observation_id}", summary="Update Observation", status_code=status.HTTP_200_OK, response_model=ObservationRead)
async def update_an_observation(observation_id: UUID, observation_in: ObservationUpdate, db: AsyncSession = Depends(get_db)):
    db_observation_to_update = await get_observation(db, observation_id=observation_id)

    updated_observation_db = await update_observation(
        db=db, db_observation=db_observation_to_update, observation_in=observation_in
    )

    return ObservationRead(**updated_observation_db.__dict__)


@router.delete("/{observation_id}", summary="Delete Observation", status_code=status.HTTP_204_NO_CONTENT)
async def delete_an_observation(observation_id: UUID, db: AsyncSession = Depends(get_db)):
    db_observation_to_delete = await get_observation(db, observation_id=observation_id)

    await delete_observation(db=db, db_observation=db_observation_to_delete)

    return None
