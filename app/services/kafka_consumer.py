"""
Kafka Consumer Service for analytics-and-dashboards microservice
"""

import asyncio
import json
from typing import Optional
from datetime import datetime

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError
from aiokafka.admin import AIOKafkaAdminClient

from app.core.config import settings
from app.core.logging import logger
from app.database import database
from app.services.beat_metrics_service import BeatMetricsService
from app.schemas.beat_metrics import BeatMetricsCreate
import httpx
import json


class KafkaService:
    """Service for managing Kafka producer and consumer connections"""

    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self.admin: Optional[AIOKafkaAdminClient] = None
        self.is_connected: bool = False
        self._consumer_task: Optional[asyncio.Task] = None
        self.beat_metrics_service: Optional[BeatMetricsService] = None

    async def start_kafka_consumer(self):
        """
        Start Kafka consumer with retry logic and cooldown period.
        Implements infinite retry loop with cooldown similar to Node.js version.
        """
        if not settings.ENABLE_KAFKA:
            logger.info("Kafka is disabled in configuration")
            return

        max_retries = settings.KAFKA_CONNECTION_MAX_RETRIES
        retry_delay = settings.KAFKA_CONNECTION_RETRY_DELAY / 1000  # Convert to seconds
        cooldown_after_fail = settings.KAFKA_COOLDOWN / 1000  # Convert to seconds

        attempt = 1

        while True:
            try:
                logger.info(f"Connecting to Kafka... (Attempt {attempt}/{max_retries})")

                # Initialize consumer with topics
                self.consumer = AIOKafkaConsumer(
                    # Subscribe to topics here - add your topics as needed
                    # Example: "analytics-events", "metrics-events"
                    bootstrap_servers=settings.KAFKA_BROKER,
                    group_id="analytics-service-group",
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    client_id="analytics-and-dashboards",
                    # tuning to avoid too aggressive rebalances
                    session_timeout_ms=getattr(settings, 'KAFKA_SESSION_TIMEOUT_MS', 30000),
                    heartbeat_interval_ms=getattr(settings, 'KAFKA_HEARTBEAT_INTERVAL_MS', 10000),
                    max_poll_interval_ms=getattr(settings, 'KAFKA_MAX_POLL_INTERVAL_MS', 300000),
                )

                # Initialize producer
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BROKER,
                    client_id="analytics-and-dashboards",
                )

                # Connect consumer and producer
                await self.consumer.start()
                await self.producer.start()

                # Subscribe to topics after connection
                self.consumer.subscribe(["beats-events"])

                # Initialize beat_metrics service
                self.beat_metrics_service = BeatMetricsService(database.db)

                self.is_connected = True
                logger.info("✅ Kafka connected & listening to 'beats-events' topic")

                # Start consuming messages
                self._consumer_task = asyncio.create_task(self._consume_messages())

                # Reset attempt counter on successful connection
                attempt = 1
                break

            except Exception as error:
                self.is_connected = False
                logger.error(f"❌ Kafka connection failed: {error}")

                if attempt >= max_retries:
                    logger.warning(
                        f"Max retries reached. Cooling down for {cooldown_after_fail}s before trying again..."
                    )
                    await asyncio.sleep(cooldown_after_fail)
                    attempt = 1
                else:
                    attempt += 1
                    logger.warning(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)

    async def _consume_messages(self):
        """
        Consume messages from Kafka topics.
        Similar to consumer.run() in Node.js version.
        """
        try:
            async for message in self.consumer:
                try:
                    # Log message metadata (topic/partition/offset/key/value preview)
                    try:
                        raw_value = message.value.decode("utf-8", errors="replace") if message.value else None
                    except Exception:
                        raw_value = None

                    key = None
                    if message.key:
                        try:
                            key = message.key.decode("utf-8", errors="replace")
                        except Exception:
                            key = repr(message.key)

                    logger.debug(
                        f"Received Kafka message topic={message.topic} partition={message.partition} "
                        f"offset={message.offset} key={key} value_preview={raw_value[:200] if raw_value else None}"
                    )

                    # Parse the message value as JSON
                    event = json.loads(raw_value) if raw_value else {}
                    await self._process_event(event)
                except json.JSONDecodeError as error:
                    logger.error(
                        f"Error parsing message as JSON: {error}, " f"Message: {message.value}"
                    )
                    await self._send_to_dlq(message.value.decode("utf-8"), str(error))
                except Exception as error:
                    logger.error(f"Error processing message: {error}, " f"Message: {message.value}")
                    await self._send_to_dlq(message.value.decode("utf-8"), str(error))
        except Exception as error:
            logger.error(f"Error in Kafka consumer loop: {error}")
            self.is_connected = False

    async def _process_event(self, event: dict):
        """
        Process individual Kafka events.
        Handles BEAT_CREATED events to calculate beat metrics automatically.

        Args:
            event: Parsed event dictionary with 'type' and 'payload' fields
        """
        event_type = event.get("type", "UNKNOWN")

        # Log the event for debugging
        logger.debug(f"Processing event type: {event_type}")

        # Process BEAT_CREATED event
        if event_type == "BEAT_CREATED":
            await self._handle_beat_created(event.get("payload"))
        else:
            logger.info(f"Unhandled event type: {event_type}")

        logger.debug(f"Event {event_type} processed")

    async def _handle_beat_created(self, payload: dict):
        """
        Handle BEAT_CREATED event by calculating beat metrics.

        Expected payload structure:
        {
            "beatId": "string",
            "audioUrl": "string",
            "userId": "string"
        }

        Args:
            payload: Event payload containing beat information
        """
        try:
            beat_id = payload.get("beatId")
            audio_url = payload.get("audioUrl")
            user_id = payload.get("userId")

            if not beat_id or not audio_url:
                logger.error(f"Invalid BEAT_CREATED payload: missing beatId or audioUrl. Payload: {payload}")
                return

            logger.info(f"Processing BEAT_CREATED event for beat: {beat_id}")

            # First approximation: call the HTTP API endpoint so the same HTTP
            # path is exercised as when requests come through the gateway.
            # Build URL to local API and send a POST with form data.
            api_url = f"http://{settings.HOST}:{settings.PORT}/api/v1/analytics/beat-metrics"

            headers = {
                # Emulate gateway-authenticated headers so middleware allows the request
                "x-gateway-authenticated": "true",
                "x-user-id": user_id or "system",
                # Send roles as JSON so the middleware can parse it back to list
                "x-roles": json.dumps(["admin"]),
            }

            data = {
                "beatId": beat_id,
            }
            if audio_url:
                data["audioUrl"] = audio_url

            # Retry loop for HTTP call
            max_retries = 3
            retry_delay = 2
            last_exc = None

            async with httpx.AsyncClient(timeout=30.0) as client:
                for attempt in range(1, max_retries + 1):
                    try:
                        resp = await client.post(api_url, data=data, headers=headers)
                        if resp.status_code in (200, 201):
                            try:
                                body = resp.json()
                                logger.info(
                                    f"✅ Beat metrics calculated via HTTP for beat: {beat_id}, metrics ID: {body.get('id') if isinstance(body, dict) else 'unknown'}"
                                )
                            except Exception:
                                logger.info(f"✅ Beat metrics HTTP call succeeded for beat: {beat_id}")
                            return
                        else:
                            last_exc = Exception(f"Unexpected status code: {resp.status_code}, body: {resp.text}")
                            logger.warning(f"Attempt {attempt} failed for beat {beat_id}: {last_exc}")
                    except Exception as error:
                        last_exc = error
                        logger.error(f"HTTP request attempt {attempt} failed: {error}")

                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)

            # If we reach here, all retries failed — send to DLQ
            await self._send_to_dlq(json.dumps(payload), str(last_exc))

        except Exception as error:
            logger.error(f"Error handling BEAT_CREATED event: {error}", exc_info=True)
            # Re-raise to send to DLQ
            raise

    async def _send_to_dlq(self, original_message: str, error_reason: str):
        """
        Send failed messages to Dead Letter Queue (DLQ).
        Similar to sendToDLQ() in Node.js version.

        Args:
            original_message: The original message that failed
            error_reason: Reason for the failure
        """
        if not self.is_connected or not self.producer:
            logger.error("Cannot send to DLQ: Kafka producer not available")
            return

        try:
            dlq_message = {
                "originalEvent": original_message,
                "error": error_reason,
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self.producer.send_and_wait(
                "analytics-dlq",
                value=json.dumps(dlq_message).encode("utf-8"),
            )
            logger.warning(f"Event sent to DLQ, reason: {error_reason}")
        except Exception as error:
            logger.error(f"Failed to send event to DLQ: {error}")

    async def send_message(self, topic: str, message: bytes, key: bytes = None):
        """
        Send a message to a Kafka topic using the producer.

        Args:
            topic: Kafka topic name
            message: Message bytes to send
            key: Optional message key
        """
        if not self.is_connected or not self.producer:
            logger.warning("Cannot send message: Kafka is not connected")
            return False

        try:
            await self.producer.send_and_wait(topic, value=message, key=key)
            logger.debug(f"Message sent to topic '{topic}'")
            return True
        except Exception as error:
            logger.error(f"Error sending message to Kafka: {error}")
            return False

    async def is_kafka_connected(self) -> bool:
        """
        Check if Kafka is connected by attempting to connect admin client.
        Similar to isKafkaConnected() in Node.js version.

        Returns:
            bool: True if connected, False otherwise
        """
        try:
            admin = AIOKafkaAdminClient(
                bootstrap_servers=settings.KAFKA_BROKER,
                client_id="analytics-and-dashboards",
            )
            await admin.start()
            # Try to list topics to verify connection
            await admin.list_topics()
            await admin.close()
            return True
        except Exception:
            return False

    async def check_health(self) -> dict:
        """
        Check Kafka connection health.

        Returns:
            dict: Health status information
        """
        return {
            "kafka": "connected" if self.is_connected else "disconnected",
            "enabled": settings.ENABLE_KAFKA,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def stop(self):
        """Stop Kafka consumer and producer gracefully"""
        logger.info("Stopping Kafka connections...")

        # Cancel consumer task if running
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                logger.info("Kafka consumer task cancelled")

        # Stop consumer
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as error:
                logger.error(f"Error stopping Kafka consumer: {error}")

        # Stop producer
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("Kafka producer stopped")
            except Exception as error:
                logger.error(f"Error stopping Kafka producer: {error}")

        self.is_connected = False


# Global instances for export (similar to Node.js export pattern)
kafka_service = KafkaService()
consumer = kafka_service.consumer
producer = kafka_service.producer
