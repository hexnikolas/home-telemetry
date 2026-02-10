from fastapi import APIRouter, Depends, status
from schemas.system_schemas import SystemRead
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.crud.crud_system import get_system

router = APIRouter()

@router.get("/", response_model=List[SystemRead], summary="List Systems", description="List systems with optional filtering, pagination, and sorting")
async def read_systems(db: AsyncSession = Depends(get_db)):
    return []



@router.get("/{system_id}", summary="Get System by ID", status_code=status.HTTP_200_OK, response_model=SystemRead)
async def get_a_system_by_id(
    system_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    print(system_id)
    db_system = await get_system(db, system_id=system_id)
    print(db_system)
    
    return SystemRead(**system_data)
