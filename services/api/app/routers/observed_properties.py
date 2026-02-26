from fastapi import APIRouter, Depends, status
from schemas.observed_property_schemas import ObservedPropertyRead, ObservedPropertyUpdate
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.crud.observed_property import get_all_observed_properties, get_observed_property, create_observed_property, update_observed_property, delete_observed_property

router = APIRouter()

@router.get("/", response_model=List[ObservedPropertyRead], summary="List Observed Properties", description="List observed properties with optional filtering, pagination, and sorting")
async def read_observed_properties(db: AsyncSession = Depends(get_db)):
    observed_properties_data = await get_all_observed_properties(db)

    return [ObservedPropertyRead(**observed_property.__dict__) for observed_property in observed_properties_data]

@router.get("/{observed_property_id}", summary="Get Observed Property by ID", status_code=status.HTTP_200_OK, response_model=ObservedPropertyRead)
async def get_an_observed_property_by_id(
    observed_property_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    db_observed_property = await get_observed_property(db, observed_property_id=observed_property_id)

    return ObservedPropertyRead(**db_observed_property.__dict__)


@router.post("/", summary="Create Observed Property", status_code=status.HTTP_201_CREATED, response_model=ObservedPropertyRead)
async def create_a_new_observed_property(observed_property_in: ObservedPropertyRead, db: AsyncSession = Depends(get_db)):
    created_observed_property_db = await create_observed_property(db=db, observed_property_in=observed_property_in)

    return ObservedPropertyRead(**created_observed_property_db.__dict__)


@router.put("/{observed_property_id}", summary="Update Observed Property", status_code=status.HTTP_200_OK, response_model=ObservedPropertyRead)
async def update_an_observed_property(observed_property_id: UUID, observed_property_in: ObservedPropertyUpdate, db: AsyncSession = Depends(get_db)):
    db_observed_property_to_update = await get_observed_property(db, observed_property_id=observed_property_id)

    updated_observed_property_db = await update_observed_property(
        db=db, db_observed_property=db_observed_property_to_update, observed_property_in=observed_property_in
    )

    return ObservedPropertyRead(**updated_observed_property_db.__dict__)


@router.delete("/{observed_property_id}", summary="Delete Observed Property", status_code=status.HTTP_204_NO_CONTENT)
async def delete_an_observed_property(observed_property_id: UUID, db: AsyncSession = Depends(get_db)):
    db_observed_property_to_delete = await get_observed_property(db, observed_property_id=observed_property_id)

    await delete_observed_property(db=db, db_observed_property=db_observed_property_to_delete)

    return None