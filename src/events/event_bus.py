"""
Redis Pub/Sub Event Bus
Enables event-driven communication between Celery workers
"""
import os
import json
import logging
import redis
from typing import Dict, Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Parse Redis URL to get connection params
if REDIS_URL.startswith("redis://"):
    # Extract host and port
    redis_parts = REDIS_URL.replace("redis://", "").split(":")
    REDIS_HOST = redis_parts[0]
    REDIS_PORT = int(redis_parts[1]) if len(redis_parts) > 1 else 6379
else:
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379

# Event channel names
EVENTS = {
    "jobs_scraped": "labor_observatory:jobs_scraped",
    "skills_extracted": "labor_observatory:skills_extracted",
    "skills_enhanced": "labor_observatory:skills_enhanced",
    "clustering_completed": "labor_observatory:clustering_completed",
}


class EventBus:
    """
    Redis Pub/Sub Event Bus for event-driven architecture.

    Usage:
        # Publish event
        bus = EventBus()
        bus.publish("jobs_scraped", {"job_ids": [1, 2, 3], "count": 3})

        # Subscribe to event
        def handler(event_data):
            print(f"Received: {event_data}")

        bus.subscribe("jobs_scraped", handler)
    """

    def __init__(self, db: int = 2):
        """
        Initialize Event Bus with Redis connection.

        Args:
            db: Redis database number (default 2, separate from Celery)
        """
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=db,
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()

    def publish(self, event_name: str, data: Dict[str, Any]) -> None:
        """
        Publish an event to Redis Pub/Sub.

        Args:
            event_name: Name of the event (e.g., "jobs_scraped")
            data: Event payload as dictionary
        """
        channel = EVENTS.get(event_name)
        if not channel:
            logger.warning(f"Unknown event: {event_name}")
            return

        # Add metadata
        event_payload = {
            "event": event_name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        # Publish to Redis
        message = json.dumps(event_payload)
        self.redis_client.publish(channel, message)

        logger.info(f"📢 Event published: {event_name} → {channel}")
        logger.debug(f"Event data: {data}")

    def subscribe(self, event_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Subscribe to an event and call callback when event is received.

        Args:
            event_name: Name of the event to subscribe to
            callback: Function to call with event data
        """
        channel = EVENTS.get(event_name)
        if not channel:
            logger.warning(f"Unknown event: {event_name}")
            return

        self.pubsub.subscribe(channel)
        logger.info(f"👂 Subscribed to event: {event_name} → {channel}")

        # Listen for messages
        for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    event_payload = json.loads(message["data"])
                    logger.info(f"📨 Event received: {event_name}")
                    callback(event_payload)
                except Exception as exc:
                    logger.error(f"Error handling event {event_name}: {exc}")

    def subscribe_pattern(self, pattern: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Subscribe to multiple events using a pattern.

        Args:
            pattern: Redis pattern (e.g., "labor_observatory:*")
            callback: Function to call with event data
        """
        self.pubsub.psubscribe(pattern)
        logger.info(f"👂 Subscribed to pattern: {pattern}")

        for message in self.pubsub.listen():
            if message["type"] == "pmessage":
                try:
                    event_payload = json.loads(message["data"])
                    logger.info(f"📨 Pattern event received: {message['channel']}")
                    callback(event_payload)
                except Exception as exc:
                    logger.error(f"Error handling pattern event: {exc}")

    def close(self):
        """Close Redis connections."""
        self.pubsub.close()
        self.redis_client.close()


# Singleton instance for convenience
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get singleton EventBus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish_event(event_name: str, data: Dict[str, Any]) -> None:
    """
    Convenience function to publish event using singleton.

    Args:
        event_name: Name of the event
        data: Event payload
    """
    bus = get_event_bus()
    bus.publish(event_name, data)


def subscribe_to_event(event_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
    """
    Convenience function to subscribe to event using singleton.

    Args:
        event_name: Name of the event
        callback: Handler function
    """
    bus = get_event_bus()
    bus.subscribe(event_name, callback)


# Example usage:
if __name__ == "__main__":
    # Test publisher
    import time

    def test_handler(event_data):
        print(f"Received event: {event_data}")

    # Start subscriber in background
    import threading
    def start_subscriber():
        subscribe_to_event("jobs_scraped", test_handler)

    subscriber_thread = threading.Thread(target=start_subscriber, daemon=True)
    subscriber_thread.start()

    time.sleep(1)  # Wait for subscriber to connect

    # Publish test event
    publish_event("jobs_scraped", {
        "job_ids": ["123", "456"],
        "count": 2,
        "country": "CO"
    })

    time.sleep(2)  # Wait to receive
