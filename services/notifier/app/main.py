import asyncio
import os
import json
import yaml
import httpx
import redis.asyncio as aioredis
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from logger.logging_config import setup_logging_json

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GOTIFY_URL = os.getenv("GOTIFY_URL", "http://gotify:80")
GOTIFY_TOKEN = os.getenv("GOTIFY_TOKEN", "")
STREAM_NAME = "observations:global"
CONSUMER_GROUP = "notifier-group"
CONSUMER_NAME = "notifier-1"

# Initialize logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger = setup_logging_json("home-telemetry-notifier", level=LOG_LEVEL)

class NotifierService:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.rules: List[Dict[str, Any]] = []
        self.load_rules()

    def load_rules(self):
        """Load alert rules from YAML file."""
        try:
            with open("app/rules.yaml", "r") as f:
                config = yaml.safe_load(f)
                self.rules = config.get("rules", [])
                logger.info(f"Loaded {len(self.rules)} alert rules")
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            self.rules = []

    async def connect(self):
        """Connect to Redis and ensure Consumer Group exists."""
        self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        try:
            # Create consumer group (MKSTREAM creates the stream if it doesn't exist)
            await self.redis.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
            logger.info(f"Created consumer group {CONSUMER_GROUP}")
        except aioredis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug("Consumer group already exists")
            else:
                raise e

    async def send_gotify(self, title: str, message: str, priority: int = 5):
        """Send a notification to Gotify."""
        if not GOTIFY_TOKEN:
            logger.warning("GOTIFY_TOKEN not set, skipping notification")
            return

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{GOTIFY_URL}/message",
                    headers={"X-Gotify-Key": GOTIFY_TOKEN},
                    json={
                        "title": title,
                        "message": message,
                        "priority": priority
                    }
                )
                response.raise_for_status()
                logger.info(f"Notification sent: {title}")
            except Exception as e:
                logger.error(f"Failed to send Gotify message: {e}")

    async def check_rules(self, observation: Dict[str, Any]):
        """Match observation against rules and check cooldowns."""
        ds_id = observation.get("datastream_id")
        val_str = observation.get("result_numeric")
        
        if not ds_id:
            return

        # 1. Update "Last Seen" for Heartbeat monitoring
        await self.redis.set(f"notifier:last_seen:{ds_id}", datetime.now(timezone.utc).isoformat())

        if not val_str:
            return

        try:
            val = float(val_str)
        except ValueError:
            return

        for rule in self.rules:
            if rule["datastream_id"] == ds_id:
                # Skip heartbeat rules in this threshold-check loop
                if rule.get("type") == "heartbeat":
                    continue

                triggered = False
                condition = rule.get("condition")
                threshold = rule.get("threshold")

                if not condition or threshold is None:
                    continue

                if condition == ">" and val > threshold:
                    triggered = True
                elif condition == "<" and val < threshold:
                    triggered = True

                if triggered:
                    # Check Cooldown in Redis
                    cooldown_key = f"notifier:cooldown:{ds_id}:{rule['name']}"
                    if not await self.redis.get(cooldown_key):
                        # Send alert
                        msg = f"{rule['name']}: {val} (Threshold: {rule['threshold']})"
                        await self.send_gotify("🚨 Telemetry Alert", msg, rule["priority"])
                        
                        # Set Cooldown
                        cooldown_sec = rule.get("cooldown_minutes", 10) * 60
                        await self.redis.set(cooldown_key, "1", ex=cooldown_sec)
                    else:
                        logger.debug(f"Rule {rule['name']} is in cooldown")

    async def monitor_heartbeats(self):
        """Background loop to check for silent sensors."""
        logger.info("Heartbeat monitor started")
        while True:
            try:
                now = datetime.now(timezone.utc)
                for rule in self.rules:
                    if rule.get("type") == "heartbeat":
                        ds_id = rule["datastream_id"]
                        timeout_min = rule.get("timeout_minutes", 30)
                        
                        last_seen_str = await self.redis.get(f"notifier:last_seen:{ds_id}")
                        
                        if last_seen_str:
                            last_seen = datetime.fromisoformat(last_seen_str)
                            diff_min = (now - last_seen).total_seconds() / 60
                            
                            if diff_min > timeout_min:
                                # Sensor is silent!
                                cooldown_key = f"notifier:cooldown:heartbeat:{ds_id}"
                                if not await self.redis.get(cooldown_key):
                                    msg = f"Sensor '{rule['name']}' has been silent for {int(diff_min)} minutes (Limit: {timeout_min})"
                                    await self.send_gotify("🚨 Heartbeat Failure", msg, rule.get("priority", 9))
                                    # Set a long cooldown for heartbeat alerts (e.g. 6 hours)
                                    await self.redis.set(cooldown_key, "1", ex=6 * 3600)
                        else:
                            # Never seen this sensor, initialize it to avoid false alerts on first run
                            await self.redis.set(f"notifier:last_seen:{ds_id}", now.isoformat())
                
                await asyncio.sleep(60) # Check every minute
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(10)

    async def run(self):
        """Main loop consuming from Redis Stream."""
        logger.info("Notifier service started, waiting for observations...")
        
        # Start heartbeat monitor as a background task
        asyncio.create_task(self.monitor_heartbeats())
        
        while True:
            try:
                # Read new messages (> means only never-delivered messages)
                # Count=1 to process one by one
                # Block=5000 (5 seconds)
                streams = await self.redis.xreadgroup(
                    CONSUMER_GROUP, CONSUMER_NAME, {STREAM_NAME: ">"}, count=1, block=5000
                )

                if not streams:
                    continue

                for stream, messages in streams:
                    for msg_id, data in messages:
                        logger.debug(f"Processing message {msg_id}")
                        await self.check_rules(data)
                        # Acknowledge the message
                        await self.redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)

            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(5) # Wait before retry

async def main():
    service = NotifierService()
    await service.connect()
    await service.run()

if __name__ == "__main__":
    asyncio.run(main())
