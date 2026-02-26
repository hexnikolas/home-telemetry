from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.future import select
from app.models import ObservedProperty
from fastapi import HTTPException
from uuid import UUID
from typing import List
from schemas.observed_property_schemas import ObservedPropertyUpdate

async def get_observed_property(db: AsyncSession, observed_property_id: UUID) -> ObservedProperty:
    statement = (
        select(ObservedProperty)
        .where(ObservedProperty.id == observed_property_id)
    )
    result = await db.execute(statement)
    observed_property = result.scalars().first()

    if not observed_property:
        raise HTTPException(status_code=404, detail=f"ObservedProperty {observed_property_id} not found")

    return observed_property


async def get_all_observed_properties(db: AsyncSession) -> List[ObservedProperty]:
    statement = select(ObservedProperty)

    result = await db.execute(statement)
    observed_properties = result.scalars().all()

    if not observed_properties:
        raise HTTPException(status_code=404, detail="No observed properties were found")

    return observed_properties


async def create_observed_property(db: AsyncSession, observed_property_in) -> ObservedProperty:
    new_observed_property = ObservedProperty(**observed_property_in.model_dump())
    try:
        db.add(new_observed_property)
        await db.commit()
        await db.refresh(new_observed_property)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating observed property: {str(e)}")

    return new_observed_property

async def update_observed_property(db: AsyncSession, db_observed_property: ObservedProperty, observed_property_in: ObservedPropertyUpdate) -> ObservedProperty:
    update_data = observed_property_in.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_observed_property, key, value)

    try:
        await db.commit()
        await db.refresh(db_observed_property)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return db_observed_property


async def delete_observed_property(db: AsyncSession, db_observed_property: ObservedProperty):
    try:
        await db.delete(db_observed_property)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error deleting observed property: {str(e)}")