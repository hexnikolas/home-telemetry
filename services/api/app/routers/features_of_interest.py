from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.crud.feature_of_interest import (
    get_all_features_of_interest,
    get_feature_of_interest,
    create_feature_of_interest,
    update_feature_of_interest,
    remove_feature_of_interest
)
from schemas.feature_of_interest_schemas import (
    FeatureOfInterestRead,
    FeatureOfInterestWrite,
    FeatureOfInterestUpdate
)

router = APIRouter()

@router.get("/", response_model=List[FeatureOfInterestRead], summary="List Features of Interest")
async def read_features_of_interest(db: AsyncSession = Depends(get_db)):
    features = await get_all_features_of_interest(db)
    return [FeatureOfInterestRead(**feature.__dict__) for feature in features]


@router.get("/{feature_id}", response_model=FeatureOfInterestRead, summary="Get Feature of Interest by ID")
async def read_feature_of_interest(feature_id: UUID, db: AsyncSession = Depends(get_db)):
    feature = await get_feature_of_interest(db, feature_id)
    return FeatureOfInterestRead(**feature.__dict__)


@router.post("/", response_model=FeatureOfInterestRead, status_code=status.HTTP_201_CREATED, summary="Create Feature of Interest")
async def create_new_feature_of_interest(
    feature_in: FeatureOfInterestWrite, db: AsyncSession = Depends(get_db)
):
    feature = await create_feature_of_interest(db, feature_in)
    return FeatureOfInterestRead(**feature.__dict__)


@router.put("/{feature_id}", response_model=FeatureOfInterestRead, summary="Update Feature of Interest")
async def update_existing_feature_of_interest(
    feature_id: UUID, feature_in: FeatureOfInterestUpdate, db: AsyncSession = Depends(get_db)
):
    feature = await get_feature_of_interest(db, feature_id)
    updated_feature = await update_feature_of_interest(db, feature, feature_in)
    return FeatureOfInterestRead(**updated_feature.__dict__)


@router.delete("/{feature_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Feature of Interest")
async def delete_feature_of_interest(feature_id: UUID, db: AsyncSession = Depends(get_db)):
    feature = await get_feature_of_interest(db=db, feature_id=feature_id)
    await remove_feature_of_interest(db, feature)  # Use the renamed function
    return None