#!/usr/bin/env python3
"""Quick test to compare REST vs gRPC observation fetching"""
import asyncio
from app.ml_models.prophet_model import compare_fetch_methods
from logger.logging_config import setup_logging_colored

logger = setup_logging_colored("grpc-comparison")


async def main():
    # Use the same datastream from the earlier test
    datastream_id = "d84925e1-c18c-4605-90be-3e0079e868f5"
    days = 50

    logger.info(f"Starting comparison test...")
    await compare_fetch_methods(datastream_id, days)


if __name__ == "__main__":
    asyncio.run(main())

