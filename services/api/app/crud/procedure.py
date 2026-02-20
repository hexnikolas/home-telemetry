from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.future import select
from app.models import Procedure, System
from fastapi import HTTPException
from uuid import UUID
from typing import List
from schemas.procedure_schemas import ProcedureWrite, ProcedureUpdate

async def get_procedure(db: AsyncSession, procedure_id: UUID) -> Procedure:
    """Get a single procedure by its ID."""
    statement = (
        select(Procedure)
        .where(Procedure.id == procedure_id)
    )
    result = await db.execute(statement)
    procedure = result.scalars().first()

    if not procedure:
        raise HTTPException(status_code=404, detail=f"Procedure {procedure_id} not found")

    return procedure


async def get_all_procedures(db: AsyncSession) -> List[Procedure]:
    """Get all procedures."""

    statement = select(Procedure)

    result = await db.execute(statement)
    procedures = result.scalars().all()

    if not procedures:
        raise HTTPException(status_code=404, detail="No procedures were found")

    return procedures


async def create_procedure(db: AsyncSession, procedure_in) -> Procedure:
    """Create a new procedure in the database."""
    procedure_data = procedure_in.model_dump()
    new_procedure = Procedure(
        **procedure_data
    )
    try:
        db.add(new_procedure)
        await db.commit()
        await db.refresh(new_procedure)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating procedure: {str(e)}")

    return new_procedure

async def update_procedure(db: AsyncSession, db_procedure: Procedure, procedure_in: ProcedureUpdate) -> Procedure:
    update_data = procedure_in.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_procedure, key, value)

    try:
        await db.commit()
        await db.refresh(db_procedure)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return db_procedure



async def delete_procedure(db: AsyncSession, db_procedure: Procedure):
    try:
        await db.delete(db_procedure)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error deleting procedure: {str(e)}")
