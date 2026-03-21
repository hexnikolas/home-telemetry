from fastapi import APIRouter, Depends, status, Query
from schemas.system_schemas import SystemRead, SystemUpdate, SystemStatus
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from app.crud.system import (
    get_all_systems, 
    get_system, 
    create_system, 
    update_system, 
    delete_system,
    get_system_status
)
from app.models import SystemTypes

router = APIRouter()


@router.get("/", response_model=List[SystemRead], summary="List Systems", description="List systems with optional filtering, pagination, and sorting")
async def read_systems(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    system_type: Optional[SystemTypes] = Query(None, description="Filter by system type")
):
    systems_data = await get_all_systems(db, limit=limit, offset=offset, system_type=system_type)
    return [SystemRead(**system.__dict__) for system in systems_data]

@router.get("/{system_id}", summary="Get System by ID", status_code=status.HTTP_200_OK, response_model=SystemRead)
async def get_a_system_by_id(
    system_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    db_system = await get_system(db, system_id=system_id)
    
    return SystemRead(**db_system.__dict__)


@router.post("/", summary="Create System", status_code=status.HTTP_201_CREATED, response_model=SystemRead)
async def create_a_new_system(system_in: SystemRead, db: AsyncSession = Depends(get_db)):
    created_system_db = await create_system(db=db, system_in=system_in)

    return SystemRead(**created_system_db.__dict__)


@router.put("/{system_id}", summary="Update System", status_code=status.HTTP_200_OK, response_model=SystemRead)
async def update_a_system(system_id: UUID, system_in: SystemUpdate, db: AsyncSession = Depends(get_db)):
    db_system_to_update = await get_system(db, system_id=system_id)

    updated_system_db = await update_system(
        db=db, db_system=db_system_to_update, system_in=system_in
    )

    return SystemRead(**updated_system_db.__dict__)


@router.delete("/{system_id}", summary="Delete System", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_system(system_id: UUID, db: AsyncSession = Depends(get_db)):
    db_system_to_delete = await get_system(db, system_id=system_id)
    
    await delete_system(db=db, db_system=db_system_to_delete)

    return None


@router.get("/{system_id}/status", response_model=bool, summary="Get System Status", description="Return online status for systems based on latest observation timestamp.")
async def read_system_status(system_id: UUID, online_within_seconds: int = Query(900, ge=1, le=86400), db: AsyncSession = Depends(get_db)):
    # return true if the latest observation for the system is within the online_within_seconds threshold, otherwise false
    system_status = await get_system_status(db, system_id=system_id, online_within_seconds=online_within_seconds)
    return system_status