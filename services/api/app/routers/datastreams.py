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


# Redis connection URL (adjust if needed)
REDIS_URL = "redis://redis:6379/0"

# WebSocket endpoint for datastream updates
@router.websocket("/ws/datastreams")
async def websocket_datastreams(websocket: WebSocket):
    await websocket.accept()
    try:
        # Receive a JSON list of datastream UUIDs to subscribe to
        subscribe_message = await websocket.receive_text()
        import json
        datastream_ids = json.loads(subscribe_message)
        if not isinstance(datastream_ids, list):
            await websocket.send_text(json.dumps({"error": "Expected a list of datastream UUIDs."}))
            await websocket.close()
            return

        import aioredis
        redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        pubsub = redis.pubsub()
        channels = [f"datastream:{ds_id}" for ds_id in datastream_ids]
        await pubsub.subscribe(*channels)

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if message:
                    # Forward the observation to the client
                    await websocket.send_text(message["data"])
                # Also check for disconnects
                try:
                    await websocket.receive_text()
                except WebSocketDisconnect:
                    break
                except Exception:
                    pass
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
            await redis.close()
    except Exception as e:
        await websocket.send_text(json.dumps({"error": str(e)}))
        await websocket.close()