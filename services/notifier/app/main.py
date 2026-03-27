import asyncio
import os
import yaml
import httpx
import redis.asyncio as aioredis
import docker
from typing import Any
from datetime import datetime, timezone
from logger.logging_config import setup_logging_json, setup_logging_colored

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GOTIFY_URL = os.getenv("GOTIFY_URL", "http://gotify:80")
GOTIFY_TOKEN = os.getenv("GOTIFY_TOKEN", "")
STREAM_NAME = "observations:global"
CONSUMER_GROUP = "notifier-group"
CONSUMER_NAME = "notifier-1"
RABBITMQ_MANAGEMENT_URL = os.getenv("RABBITMQ_MANAGEMENT_URL", "http://rabbitmq:15672")
RABBITMQ_MANAGEMENT_USER = os.getenv("RABBITMQ_MANAGEMENT_USER", "guest")
RABBITMQ_MANAGEMENT_PASS = os.getenv("RABBITMQ_MANAGEMENT_PASS", "guest")
RABBITMQ_QUEUE_NAME = os.getenv("RABBITMQ_QUEUE_NAME", "observations")
CHECK_INTERVAL_HEALTH = int(os.getenv("CHECK_INTERVAL_HEALTH", "30"))
CHECK_INTERVAL_HEARTBEAT = int(os.getenv("CHECK_INTERVAL_HEARTBEAT", "60"))
CHECK_INTERVAL_QUEUE = int(os.getenv("CHECK_INTERVAL_QUEUE", "60"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
if LOG_FORMAT == "colored":
    logger = setup_logging_colored("home-telemetry-notifier", level=LOG_LEVEL)
else:
    logger = setup_logging_json("home-telemetry-notifier", level=LOG_LEVEL)

# ---------------------------------------------------------------------------
# Containers that have Docker healthchecks defined
# ---------------------------------------------------------------------------
HEALTHCHECKED_CONTAINERS: set[str] = {
    "home-telemetry-api",
    "home-telemetry-timescaledb",
    "home-telemetry-rabbitmq",
    "home-telemetry-ingestion-worker",
    "home-telemetry-jobs-worker",
    "home-telemetry-jobs-scheduler",
    "redis",
}

# Containers whose health depends on Redis — suppress alerts during Redis
# outages and for a grace period after recovery.
REDIS_DEPENDENT: set[str] = {
    "home-telemetry-ingestion-worker",
    "home-telemetry-jobs-worker",
    "home-telemetry-jobs-scheduler",
}


def _evaluate_condition(value: float, condition: str, threshold: float) -> bool:
    """Return True when *value* violates the given condition/threshold."""
    if condition == ">":
        return value > threshold
    if condition == "<":
        return value < threshold
    if condition == ">=":
        return value >= threshold
    if condition == "<=":
        return value <= threshold
    if condition in ("=", "=="):
        return value == threshold
    return False


class NotifierService:
    """Core notifier — consumes observations, evaluates rules, monitors
    Docker container health, and pushes alerts to Gotify."""

    def __init__(self) -> None:
        self.redis: aioredis.Redis | None = None
        self.docker_client: docker.DockerClient | None = None
        self.rules: list[dict[str, Any]] = []

        # Redis health tracking
        self.redis_healthy = True
        self.redis_recovery_ts: float = 0.0
        self.redis_grace_seconds = 60

        # Docker state tracking  (container_name -> last known health string)
        self.container_health: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def load_rules(self) -> None:
        """Load alert rules from the YAML file."""
        path = os.path.join(os.path.dirname(__file__), "rules.yaml")
        try:
            with open(path, "r") as fh:
                config = yaml.safe_load(fh)
                self.rules = config.get("rules", [])
            logger.info(f"Loaded {len(self.rules)} alert rules from {path}")
        except Exception as exc:
            logger.error(f"Failed to load rules: {exc}")
            self.rules = []

    async def connect(self) -> None:
        """Set up Redis and Docker connections."""
        # -- Redis --
        logger.info("Connecting to Redis …")
        self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        await self.redis.ping()
        logger.info("Redis connected")

        # -- Consumer group --
        try:
            await self.redis.xgroup_create(
                STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True
            )
            logger.info(f"Created consumer group '{CONSUMER_GROUP}'")
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
            logger.debug(f"Consumer group '{CONSUMER_GROUP}' already exists")

        # -- Docker --
        logger.info("Connecting to Docker …")
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Docker connected")
        except Exception as exc:
            logger.warning(f"Docker unavailable — container monitoring disabled: {exc}")
            self.docker_client = None

    # ------------------------------------------------------------------
    # Gotify
    # ------------------------------------------------------------------
    async def send_alert(self, title: str, message: str, priority: int = 5) -> None:
        """Push a notification to Gotify."""
        if not GOTIFY_TOKEN:
            logger.debug(f"Alert (no token): {title} — {message}")
            return
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GOTIFY_URL}/message",
                    headers={"X-Gotify-Key": GOTIFY_TOKEN},
                    json={"title": title, "message": message, "priority": priority},
                    timeout=5,
                )
                resp.raise_for_status()
            logger.info(f"Alert sent: {title}")
        except Exception as exc:
            logger.error(f"Failed to send alert: {exc}")

    # ------------------------------------------------------------------
    # Cooldown helper
    # ------------------------------------------------------------------
    async def _is_in_cooldown(self, key: str) -> bool:
        """Return True if *key* is still cooling down."""
        return bool(await self.redis.get(key))

    async def _set_cooldown(self, key: str, minutes: int) -> None:
        await self.redis.set(key, "1", ex=minutes * 60)

    # ------------------------------------------------------------------
    # Redis health monitor
    # ------------------------------------------------------------------
    async def monitor_redis_health(self) -> None:
        """Periodically ping Redis and track up/down transitions."""
        logger.info("Redis health monitor started")
        was_healthy = True

        while True:
            try:
                await self.redis.ping()
                is_healthy = True
            except Exception:
                is_healthy = False

            if was_healthy and not is_healthy:
                self.redis_healthy = False
                logger.error("Redis is DOWN")
                await self.send_alert(
                    "🔴 Redis Down", "Redis is not responding to PING", priority=9
                )
            elif not was_healthy and is_healthy:
                self.redis_healthy = True
                self.redis_recovery_ts = asyncio.get_event_loop().time()
                logger.info("Redis recovered")
                await self.send_alert(
                    "✅ Redis Recovered", "Redis is responding again", priority=5
                )

            was_healthy = is_healthy
            await asyncio.sleep(CHECK_INTERVAL_HEALTH)

    # ------------------------------------------------------------------
    # Docker container health monitor
    # ------------------------------------------------------------------
    def _in_redis_grace(self) -> bool:
        """True when Redis is down or recently recovered."""
        if not self.redis_healthy:
            return True
        elapsed = asyncio.get_event_loop().time() - self.redis_recovery_ts
        return elapsed < self.redis_grace_seconds

    async def monitor_docker_health(self) -> None:
        """Watch containers that have Docker HEALTHCHECK defined and alert on
        status changes (healthy ↔ unhealthy / stopped)."""
        if self.docker_client is None:
            return

        logger.info(
            f"Docker health monitor started — tracking {len(HEALTHCHECKED_CONTAINERS)} containers"
        )
        first_run = True

        while True:
            try:
                all_containers = {c.name: c for c in self.docker_client.containers.list(all=True)}
                current: dict[str, str] = {}

                for name in HEALTHCHECKED_CONTAINERS:
                    container = all_containers.get(name)
                    if container is None:
                        current[name] = "not_found"
                        continue

                    state = container.attrs.get("State", {})
                    health = state.get("Health")
                    if health:
                        current[name] = health.get("Status", "unknown")
                    elif state.get("Running"):
                        current[name] = "running (no healthcheck)"
                    else:
                        current[name] = "stopped"

                # First iteration — just log and store state
                if first_run:
                    for name in sorted(current):
                        logger.info(f"  {name}: {current[name]}")
                    self.container_health = current
                    first_run = False
                    await asyncio.sleep(CHECK_INTERVAL_HEALTH)
                    continue

                # Detect transitions
                for name, status in current.items():
                    prev = self.container_health.get(name)
                    if prev == status:
                        continue  # no change

                    # Suppress alerts for Redis-dependent containers during
                    # Redis outage / grace period.
                    if name in REDIS_DEPENDENT and self._in_redis_grace():
                        logger.debug(
                            f"Suppressing alert for {name} ({prev} → {status}) — Redis grace"
                        )
                        continue

                    is_bad = status in ("unhealthy", "stopped", "not_found")
                    emoji = "🔴" if is_bad else "🟢"
                    prio = 9 if is_bad else 5
                    logger.warning(f"{emoji} {name}: {prev} → {status}")
                    await self.send_alert(
                        f"{emoji} Container {name}",
                        f"Status changed: {prev} → {status}",
                        priority=prio,
                    )

                self.container_health = current

            except Exception as exc:
                logger.error(f"Docker health monitor error: {exc}")

            await asyncio.sleep(CHECK_INTERVAL_HEALTH)

    # ------------------------------------------------------------------
    # RabbitMQ queue depth monitor
    # ------------------------------------------------------------------
    async def monitor_rabbitmq_queue(self) -> None:
        """Check the RabbitMQ management API for queue size."""
        queue_rule = next(
            (
                r
                for r in self.rules
                if r.get("type") == "system_metric"
                and r.get("metric") == "rabbitmq_queue_size"
            ),
            None,
        )
        if queue_rule is None:
            logger.debug("No rabbitmq_queue_size rule — queue monitor disabled")
            return

        threshold = float(queue_rule.get("threshold", 100))
        condition = queue_rule.get("condition", ">")
        cooldown_min = queue_rule.get("cooldown_minutes", 30)
        priority = queue_rule.get("priority", 8)
        cooldown_key = "notifier:cooldown:rabbitmq_queue"

        logger.info(
            f"RabbitMQ queue monitor started (threshold: {condition} {threshold})"
        )

        while True:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{RABBITMQ_MANAGEMENT_URL}/api/queues/%2F/{RABBITMQ_QUEUE_NAME}",
                        auth=(RABBITMQ_MANAGEMENT_USER, RABBITMQ_MANAGEMENT_PASS),
                        timeout=5,
                    )
                    resp.raise_for_status()
                    queue_size = resp.json().get("messages", 0)

                if _evaluate_condition(queue_size, condition, threshold):
                    if not await self._is_in_cooldown(cooldown_key):
                        logger.warning(
                            f"Queue threshold breached: {queue_size} msgs ({condition} {threshold})"
                        )
                        await self.send_alert(
                            "⚠️ RabbitMQ Queue Alert",
                            f"{queue_rule['name']}: {queue_size} messages (threshold: {threshold})",
                            priority=priority,
                        )
                        await self._set_cooldown(cooldown_key, cooldown_min)
                    else:
                        logger.debug(f"Queue alert in cooldown (size: {queue_size})")
                else:
                    logger.debug(f"Queue OK: {queue_size}/{threshold}")

            except Exception as exc:
                logger.error(f"RabbitMQ queue monitor error: {exc}")

            await asyncio.sleep(CHECK_INTERVAL_QUEUE)

    # ------------------------------------------------------------------
    # Heartbeat (sensor-offline) monitor
    # ------------------------------------------------------------------
    async def monitor_heartbeats(self) -> None:
        """Alert when a datastream hasn't reported data within its timeout."""
        heartbeat_rules = [r for r in self.rules if r.get("type") == "heartbeat"]
        if not heartbeat_rules:
            logger.debug("No heartbeat rules configured")
            return

        logger.info(f"Heartbeat monitor started — {len(heartbeat_rules)} rules:")
        for rule in heartbeat_rules:
            logger.info(
                f"  {rule['name']}: timeout {rule.get('timeout_minutes', 30)} min"
            )

        while True:
            try:
                now = datetime.now(timezone.utc)
                for rule in heartbeat_rules:
                    ds_id = rule.get("datastream_id")
                    timeout_min = rule.get("timeout_minutes", 30)
                    cooldown_key = f"notifier:cooldown:heartbeat:{ds_id}"

                    last_seen_raw = await self.redis.get(f"notifier:last_seen:{ds_id}")
                    if last_seen_raw is None:
                        # Never seen — can't evaluate yet
                        continue

                    last_seen = datetime.fromisoformat(last_seen_raw)
                    silent_min = (now - last_seen).total_seconds() / 60

                    if silent_min > timeout_min:
                        if not await self._is_in_cooldown(cooldown_key):
                            logger.error(
                                f"Heartbeat missed: '{rule['name']}' silent for "
                                f"{int(silent_min)} min (limit: {timeout_min} min)"
                            )
                            await self.send_alert(
                                "🚨 Heartbeat Failure",
                                f"'{rule['name']}' silent for {int(silent_min)} min "
                                f"(limit: {timeout_min} min)",
                                priority=rule.get("priority", 9),
                            )
                            # Long cooldown so we don't spam for a dead sensor
                            await self._set_cooldown(cooldown_key, 6 * 60)
                        else:
                            logger.debug(f"Heartbeat alert in cooldown: {rule['name']}")

            except Exception as exc:
                logger.error(f"Heartbeat monitor error: {exc}")

            await asyncio.sleep(CHECK_INTERVAL_HEARTBEAT)

    # ------------------------------------------------------------------
    # Observation rule checker
    # ------------------------------------------------------------------
    async def check_rules(self, observation: dict[str, Any]) -> None:
        """Evaluate an incoming observation against threshold rules and update
        the last-seen timestamp for heartbeat tracking."""
        ds_id = observation.get("datastream_id")
        val_str = observation.get("result_numeric")
        if not ds_id or val_str is None:
            return

        # Update last-seen for heartbeat monitoring (7-day TTL)
        await self.redis.set(
            f"notifier:last_seen:{ds_id}",
            datetime.now(timezone.utc).isoformat(),
            ex=7 * 86400,
        )

        try:
            value = float(val_str)
        except (ValueError, TypeError):
            return

        for rule in self.rules:
            # Skip non-threshold rules
            if rule.get("type") in ("heartbeat", "system_metric"):
                continue
            if rule.get("datastream_id") != ds_id:
                continue

            condition = rule.get("condition")
            threshold = rule.get("threshold")
            if condition is None or threshold is None:
                continue

            if _evaluate_condition(value, condition, float(threshold)):
                cooldown_key = f"notifier:cooldown:{ds_id}:{rule['name']}"
                if not await self._is_in_cooldown(cooldown_key):
                    logger.warning(
                        f"Threshold violation: '{rule['name']}' = {value} "
                        f"({condition} {threshold})"
                    )
                    await self.send_alert(
                        "🚨 Telemetry Alert",
                        f"{rule['name']}: {value} (threshold: {threshold})",
                        priority=rule.get("priority", 8),
                    )
                    await self._set_cooldown(
                        cooldown_key, rule.get("cooldown_minutes", 10)
                    )
                else:
                    logger.debug(f"Rule in cooldown: {rule['name']}")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    async def run(self) -> None:
        """Start background monitors and consume the Redis observation stream."""
        logger.info("Notifier service starting …")

        tasks = [
            asyncio.create_task(self.monitor_redis_health()),
            asyncio.create_task(self.monitor_docker_health()),
            asyncio.create_task(self.monitor_rabbitmq_queue()),
            asyncio.create_task(self.monitor_heartbeats()),
        ]

        logger.info("All monitors started — entering consumer loop")

        try:
            while True:
                try:
                    streams = await self.redis.xreadgroup(
                        CONSUMER_GROUP,
                        CONSUMER_NAME,
                        {STREAM_NAME: ">"},
                        count=10,
                        block=5000,
                    )
                    if not streams:
                        continue

                    for _stream, messages in streams:
                        for msg_id, data in messages:
                            logger.debug(f"Processing observation {msg_id}")
                            await self.check_rules(data)
                            await self.redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)

                except aioredis.ConnectionError:
                    logger.error("Redis connection lost — retrying in 5 s")
                    await asyncio.sleep(5)
                except Exception as exc:
                    logger.error(f"Consumer loop error: {exc}")
                    await asyncio.sleep(5)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


async def main() -> None:
    service = NotifierService()
    service.load_rules()
    await service.connect()
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
