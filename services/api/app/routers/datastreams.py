from fastapi import APIRouter, Depends, status, Query, WebSocket, WebSocketDisconnect
from schemas.datastream_schemas import DatastreamRead, DatastreamUpdate
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.crud.datastream import (
    get_all_datastreams, 
    get_datastream, 
    create_datastream, 
    update_datastream, 
    delete_datastream
)
from app.crud.observation import get_redis_client
import json
from logger.logging_config import logger


router = APIRouter()


@router.get("/", response_model=List[DatastreamRead], summary="List Datastreams", description="List datastreams with optional filtering, pagination, and sorting")
async def read_datastreams(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    datastreams_data = await get_all_datastreams(db, limit=limit, offset=offset)
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


@router.websocket("/ws/{datastream_id}")
async def websocket_datastream(websocket: WebSocket, datastream_id: UUID):
    await websocket.accept()
    redis = await get_redis_client()
    stream_key = f"datastream:{str(datastream_id)}"
    last_id = "$"  # Start from new messages only
    
    try:
        while True:
            # Read from stream with blocking
            result = await redis.xread({stream_key: last_id}, block=0)
            
            if result:
                for stream, messages in result:
                    for message_id, data in messages:
                        last_id = message_id
                        # Convert message_id and data for JSON serialization
                        message_id_str = message_id.decode() if isinstance(message_id, bytes) else message_id
                        await websocket.send_json({
                            "id": message_id_str,
                            "data": data
                        })
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for datastream {datastream_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket for datastream {datastream_id}: {str(e)}")
        try:
            await websocket.close(code=1000)
        except:
            pass


