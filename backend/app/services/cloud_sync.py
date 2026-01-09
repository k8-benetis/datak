"""Cloud synchronization and Digital Twin integration via MQTT."""

from datetime import datetime
from typing import Any
import asyncio
import json

import aiomqtt
import structlog

from app.config import get_settings
from app.db.session import async_session_factory
from app.models.sensor import Sensor

logger = structlog.get_logger()
settings = get_settings()


class CloudSync:
    """
    Northbound service for Digital Twin integration via MQTT.
    """

    def __init__(self):
        self._log = logger.bind(component="cloud_sync")
        self._client: aiomqtt.Client | None = None
        self._running = False
        self._loop_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Initialize the cloud sync service."""
        if not settings.digital_twin_enabled:
            self._log.info("Digital Twin integration disabled")
            return

        if not settings.digital_twin_host:
             self._log.warning("Digital Twin enabled but no host configured")
             return

        try:
            self._client = aiomqtt.Client(
                hostname=settings.digital_twin_host,
                port=settings.digital_twin_port,
                username=settings.digital_twin_username,
                password=settings.digital_twin_password,
                # Protocol 443 often implies TLS, aiomqtt handles this if port=8883/443?
                # Usually requires tls_context if not standard.
                # Assuming standard config or handled by aiomqtt defaults for now.
                # If port is 443, it might need tls=True or similar.
                # aiomqtt tries to detect? No.
                # Use tls_context if port is 8883 or 443 and not localhost?
            )
            
            # Simple TLS auto-enable if port matches standard secure ports
            if settings.digital_twin_port in (8883, 443):
                import ssl
                # Create default context
                self._client.tls_context = ssl.create_default_context()

            await self._client.__aenter__()
            self._running = True
            
            self._log.info("Cloud sync connected", host=settings.digital_twin_host)
            
            # TODO: Subscribe to commands if needed in future
            # await self._client.subscribe(f"{settings.digital_twin_topic}/cmd")

        except Exception as e:
            self._log.error("Failed to connect to Digital Twin MQTT", error=str(e))
            self._running = False

    async def stop(self) -> None:
        """Close cloud sync connections."""
        self._running = False
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                pass
            self._client = None

    async def send_reading(
        self,
        sensor_id: int,
        sensor_name: str,
        value: float,
        timestamp: datetime,
        entity_id: str | None = None,
        attribute: str | None = None,
    ) -> bool:
        """
        Send a sensor reading to the Digital Twin.
        """
        if not self._client or not settings.digital_twin_enabled:
            return False

        try:
            # Format: Simple JSON { "attribute": value }
            attr_name = attribute or sensor_name
            
            # Ensure safe attribute name (no spaces, etc?) User template had keys like "temp_c"
            # We use what's configured.
            
            payload = json.dumps({
                attr_name: value
            })

            topic = settings.digital_twin_topic
            if not topic:
                self._log.warning("No Digital Twin topic configured")
                return False

            await self._client.publish(topic, payload)
            return True

        except Exception as e:
            self._log.error("Cloud publish error", error=str(e))
            # Try to reconnect implicitly? 
            # aiomqtt client might be disconnected.
            # We rely on external restart or periodic check, or add logic here.
            return False

    async def generate_device_profile(self) -> dict[str, Any]:
        """
        Generate a device profile JSON for the Digital Twin.
        """
        try:
            async with async_session_factory() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Sensor)
                    .where(Sensor.is_active == True)  # noqa: E712
                    .where(Sensor.deleted_at == None)  # noqa: E711
                )
                sensors = list(result.scalars().all())

            # Build device profile matching user template
            profile = {
                "name": settings.gateway_name or "DaTaK Gateway",
                "description": "Auto-generated profile from DaTaK Gateway sensors",
                "entityType": "DaTaK_Device",
                "mappings": []
            }

            for sensor in sensors:
                mapping = {
                    "incoming_key": sensor.twin_attribute or sensor.name,
                    "target_attribute": sensor.twin_attribute or sensor.name,
                    "type": "Number",
                    "transformation": "val"
                }
                profile["mappings"].append(mapping)

            return profile

        except Exception as e:
            self._log.exception("Profile generation failed", error=str(e))
            return {"error": str(e)}

    # Command receiving logic removed for now as it requires complex subscription handling
    # and wasn't explicitly requested beyond the topic existence.

# Global instance
cloud_sync = CloudSync()
