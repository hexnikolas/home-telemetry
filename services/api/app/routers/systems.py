from fastapi import APIRouter, Depends, status, Query
from schemas.system_schemas import SystemRead, SystemUpdate, SystemStatus
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.crud.crud_system import get_all_systems, get_system, create_system, update_system, delete_system

router = APIRouter()

@router.get("/", response_model=List[SystemRead], summary="List Systems", description="List systems with optional filtering, pagination, and sorting")
async def read_systems(db: AsyncSession = Depends(get_db)):
    
    systems_data = await get_all_systems(db)
    
    return [SystemRead(**{k: v for k, v in system.__dict__.items() if not k.startswith("_")}) for system in systems_data]


@router.get("/{system_id}", summary="Get System by ID", status_code=status.HTTP_200_OK, response_model=SystemRead)
async def get_a_system_by_id(
    system_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    db_system = await get_system(db, system_id=system_id)
    
    # Build a clean dictionary of attributes
    system_data = {k: v for k, v in db_system.__dict__.items() if not k.startswith("_")}
    
    return SystemRead(**system_data)


@router.post("/", summary="Create System", status_code=status.HTTP_201_CREATED, response_model=SystemRead)
async def create_a_new_system(system_in: SystemRead, db: AsyncSession = Depends(get_db)):
    created_system_db = await create_system(db=db, system_in=system_in)

    # Build a clean dictionary of attributes
    system_data = {k: v for k, v in created_system_db.__dict__.items() if not k.startswith("_")}

    # Validate and return Pydantic model
    return SystemRead(**system_data)


@router.put("/{system_id}", summary="Update System", status_code=status.HTTP_200_OK, response_model=SystemRead)
async def update_a_system(system_id: UUID, system_in: SystemUpdate, db: AsyncSession = Depends(get_db)):
    db_system_to_update = await get_system(db, system_id=system_id)
    
    updated_system_db = await update_system(
        db=db, db_system=db_system_to_update, system_in=system_in
    )
    
    system_data = {k: v for k, v in updated_system_db.__dict__.items() if not k.startswith("_")}

    # Validate and return Pydantic model
    return SystemRead(**system_data)


@router.delete("/{system_id}", summary="Delete System", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_system(system_id: UUID, db: AsyncSession = Depends(get_db)):
    db_system_to_delete = await get_system(db, system_id=system_id)
    
    await delete_system(db=db, db_system=db_system_to_delete)
    
    return None


@router.get("/status", response_model=List[SystemStatus], summary="Get System Status", description="Return online status for systems based on latest observation timestamp.")
async def read_system_status(system_id: List[UUID] = Query(..., description="System IDs to evaluate"), online_within_seconds: int = Query(900, ge=1, le=86400), db: AsyncSession = Depends(get_db)):
    # stmt = (
    #     select(
    #         DBSystem.id.label("system_id"),
    #         func.max(Observation.result_time).label("last_observation"),
    #     )
    #     .select_from(DBSystem)
    #     .outerjoin(Datastream, Datastream.system_id == DBSystem.id)
    #     .outerjoin(Observation, Observation.datastream_id == Datastream.id)
    #     .where(DBSystem.id.in_(system_id))
    #     .group_by(DBSystem.id)
    # )
    # result = await db.execute(stmt)
    # rows = result.all()

    # now = datetime.now(timezone.utc)
    # threshold = now - timedelta(seconds=online_within_seconds)
    # last_by_id = {row.system_id: row.last_observation for row in rows}

    # statuses: List[SystemStatus] = []
    # for system in system_id:
    #     last_observation = last_by_id.get(system)
    #     if last_observation and last_observation.tzinfo is None:
    #         last_observation = last_observation.replace(tzinfo=timezone.utc)
    #     online = bool(last_observation and last_observation >= threshold)
    #     statuses.append(
    #         SystemStatus(
    #             system_id=system,
    #             last_observation=last_observation,
    #             online=online,
    #         )
    #     )

    # return statuses
    pass