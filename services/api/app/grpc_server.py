import asyncio
from grpc import aio, StatusCode
import sys
import os
from datetime import datetime

# Add shared to path for proto imports
shared_path = os.path.join(os.path.dirname(__file__), '../../..', 'shared')
sys.path.insert(0, shared_path)

from protos import observations_pb2, observations_pb2_grpc
from app.crud.observation import get_all_observations
from logger.logging_config import setup_logging_json

logger = setup_logging_json("grpc-server")


class ObservationServiceServicer(observations_pb2_grpc.ObservationServiceServicer):
    """gRPC service for retrieving observations."""

    def __init__(self, db_factory):
        self.db_factory = db_factory

    async def GetObservations(self, request, context):
        """Stream observations for a datastream, optionally filtered by time range."""
        logger.info(f"GetObservations request: datastream_id={request.datastream_id}, limit={request.limit}")
        try:
            async with self.db_factory() as db:
                # Build filters
                filters = {"datastream_id": request.datastream_id}

                # Parse ISO timestamp strings to datetime objects
                time_start = None
                time_end = None
                if request.time_start:
                    try:
                        time_start = datetime.fromisoformat(request.time_start.replace('Z', '+00:00'))
                    except:
                        time_start = None
                if request.time_end:
                    try:
                        time_end = datetime.fromisoformat(request.time_end.replace('Z', '+00:00'))
                    except:
                        time_end = None

                limit = request.limit if request.limit > 0 else 1000

                # Fetch observations using existing CRUD logic
                observations = await get_all_observations(
                    db,
                    limit=limit,
                    offset=0,
                    filters=filters,
                    time_start=time_start,
                    time_end=time_end,
                )

                # Stream each observation as protobuf message
                count = 0
                for obs in observations:
                    count += 1
                    yield observations_pb2.Observation(
                        id=str(obs.id),
                        datastream_id=str(obs.datastream_id),
                        result_time=obs.result_time.isoformat(),
                        result_numeric=obs.result_numeric or 0.0,
                        result_text=obs.result_text or "",
                        result_boolean=obs.result_boolean or False,
                        result_complex=obs.result_complex or "",
                        parameters=obs.parameters or {},
                    )
                logger.info(f"GetObservations completed: streamed {count} observations")
        except Exception as e:
            logger.error(f"gRPC error: {str(e)}")
            await context.abort(StatusCode.INTERNAL, str(e))


async def serve(db_factory, host: str = "0.0.0.0", port: int = 50051) -> None:
    """Start the gRPC server."""
    try:
        server = aio.server()
        observations_pb2_grpc.add_ObservationServiceServicer_to_server(
            ObservationServiceServicer(db_factory), server
        )

        addr = f"{host}:{port}"
        server.add_insecure_port(addr)
        await server.start()
        logger.info(f"gRPC server started on {addr} with OAuth2 auth")
        await server.wait_for_termination()
    except Exception as e:
        logger.error(f"Failed to start gRPC server: {str(e)}")
        raise


