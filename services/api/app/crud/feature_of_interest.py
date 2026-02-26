from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException
from uuid import UUID
from app.models import FeatureOfInterest
from schemas.feature_of_interest_schemas import (
    FeatureOfInterestWrite,
    FeatureOfInterestUpdate
)

def handle_media_links(media_links):
    return [str(link) for link in media_links] if media_links else None

async def get_all_features_of_interest(db: AsyncSession):
    statement = select(FeatureOfInterest)
    result = await db.execute(statement)
    features = result.scalars().all()

    if not features:
        raise HTTPException(status_code=404, detail="No features of interest were found")

    return features

async def get_feature_of_interest(db: AsyncSession, feature_id: UUID):
    statement = select(FeatureOfInterest).where(FeatureOfInterest.id == feature_id)
    result = await db.execute(statement)
    feature = result.scalars().first()
    
    if not feature:
        raise HTTPException(status_code=404, detail=f"Feature of Interest {feature_id} not found")
    return feature

async def create_feature_of_interest(db: AsyncSession, feature_in: FeatureOfInterestWrite):
    media_links = handle_media_links(feature_in.media_links)
    new_feature = FeatureOfInterest(
        **feature_in.dict(exclude={"media_links"}),
        media_links=media_links
    )
    try:
        db.add(new_feature)
        await db.commit()
        await db.refresh(new_feature)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    return new_feature

async def update_feature_of_interest(
    db: AsyncSession, db_feature: FeatureOfInterest, feature_in: FeatureOfInterestUpdate
):
    update_data = feature_in.model_dump(exclude_unset=True)

    # Handle media_links separately to avoid redundant processing
    if "media_links" in update_data:
        db_feature.media_links = handle_media_links(update_data.pop("media_links"))

    for key, value in update_data.items():
        setattr(db_feature, key, value)

    try:
        await db.commit()
        await db.refresh(db_feature)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return db_feature

async def remove_feature_of_interest(db: AsyncSession, db_feature: FeatureOfInterest):
    try:
        await db.delete(db_feature)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error deleting feature of interest: {str(e)}")