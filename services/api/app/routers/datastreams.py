from fastapi import APIRouter, Depends, status
from schemas.datastream_schemas import DatastreamRead, DatastreamUpdate
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.crud.datastream import get_all_datastreams, get_datastream, create_datastream, update_datastream, delete_datastream

router = APIRouter()

@router.get("/", response_model=List[DatastreamRead], summary="List Datastreams", description="List datastreams with optional filtering, pagination, and sorting")
async def read_datastreams(db: AsyncSession = Depends(get_db)):
    datastreams_data = await get_all_datastreams(db)

    return [DatastreamRead(**datastream.__dict__) for datastream in datastreams_data]

@router.get("/{datastream_id}", summary="Get Datastream by ID", status_code=status.HTTP_200_OK, response_model=DatastreamRead)
async def get_a_datastream_by_id(
    datastream_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    db_datastream = await get_datastream(db, datastream_id=datastream_id)

    return DatastreamRead(**db_datastream.__dict__)


@router.post("/", summary="Create Datastream", status_code=status.HTTP_201_CREATED, response_model=DatastreamRead)
async def create_a_new_datastream(datastream_in: DatastreamRead, db: AsyncSession = Depends(get_db)):
    created_datastream_db = await create_datastream(db=db, datastream_in=datastream_in)

    return DatastreamRead(**created_datastream_db.__dict__)


@router.put("/{datastream_id}", summary="Update Datastream", status_code=status.HTTP_200_OK, response_model=DatastreamRead)
async def update_a_datastream(datastream_id: UUID, datastream_in: DatastreamUpdate, db: AsyncSession = Depends(get_db)):
    db_datastream_to_update = await get_datastream(db, datastream_id=datastream_id)

    updated_datastream_db = await update_datastream(
        db=db, db_datastream=db_datastream_to_update, datastream_in=datastream_in
    )

    return DatastreamRead(**updated_datastream_db.__dict__)


@router.delete("/{datastream_id}", summary="Delete Datastream", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_datastream(datastream_id: UUID, db: AsyncSession = Depends(get_db)):
    db_datastream_to_delete = await get_datastream(db, datastream_id=datastream_id)

    await delete_datastream(db=db, db_datastream=db_datastream_to_delete)

    return None