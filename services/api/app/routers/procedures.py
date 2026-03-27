from fastapi import APIRouter, Depends, status, Query
from schemas.procedure_schemas import ProcedureRead, ProcedureWrite, ProcedureUpdate
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.crud.procedure import (
    get_all_procedures, 
    get_procedure, 
    create_procedure, 
    update_procedure, 
    delete_procedure
)
from pydantic import UUID4
from app.auth.dependencies import require_scope

router = APIRouter()


@router.get("/", response_model=List[ProcedureRead], summary="List Procedures", description="List procedures with optional filtering, pagination, and sorting", dependencies=[Depends(require_scope("procedures:read"))])
async def read_procedures(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    procedures_data = await get_all_procedures(db, limit=limit, offset=offset)
    return [ProcedureRead(**{k: v for k, v in procedure.__dict__.items() if not k.startswith("_")}) for procedure in procedures_data]


@router.get("/{procedure_id}", summary="Get Procedure by ID", status_code=status.HTTP_200_OK, response_model=ProcedureRead, dependencies=[Depends(require_scope("procedures:read"))])
async def get_a_procedure_by_id(
    procedure_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    db_procedure = await get_procedure(db, procedure_id=procedure_id)

    # Build a clean dictionary of attributes
    procedure_data = {k: v for k, v in db_procedure.__dict__.items() if not k.startswith("_")}

    return ProcedureRead(**procedure_data)


@router.post("/", summary="Create Procedure", status_code=status.HTTP_201_CREATED, response_model=ProcedureRead, dependencies=[Depends(require_scope("procedures:write"))])
async def create_a_new_procedure(procedure_in: ProcedureWrite, db: AsyncSession = Depends(get_db)):
    created_procedure_db = await create_procedure(db=db, procedure_in=procedure_in)

    # Build a clean dictionary of attributes
    procedure_data = {k: v for k, v in created_procedure_db.__dict__.items() if not k.startswith("_")}

    # Validate and return Pydantic model
    return ProcedureRead(**procedure_data)


@router.put("/{procedure_id}", summary="Update Procedure", status_code=status.HTTP_200_OK, response_model=ProcedureRead, dependencies=[Depends(require_scope("procedures:write"))])
async def update_a_procedure(procedure_id: UUID, procedure_in: ProcedureUpdate, db: AsyncSession = Depends(get_db)):
    db_procedure_to_update = await get_procedure(db, procedure_id=procedure_id)

    updated_procedure_db = await update_procedure(
        db=db, db_procedure=db_procedure_to_update, procedure_in=procedure_in
    )

    procedure_data = {k: v for k, v in updated_procedure_db.__dict__.items() if not k.startswith("_")}

    # Validate and return Pydantic model
    return ProcedureRead(**procedure_data)


@router.delete("/{procedure_id}", summary="Delete Procedure", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_scope("procedures:write"))])
async def delete_a_procedure(procedure_id: UUID, db: AsyncSession = Depends(get_db)):
    db_procedure_to_delete = await get_procedure(db, procedure_id=procedure_id)

    await delete_procedure(db=db, db_procedure=db_procedure_to_delete)

    return None
