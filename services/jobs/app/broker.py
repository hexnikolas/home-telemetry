"""Dramatiq broker configuration"""
import os
from dramatiq.brokers.redis import RedisBroker

# Configure Redis broker
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

broker = RedisBroker(url=REDIS_URL)
