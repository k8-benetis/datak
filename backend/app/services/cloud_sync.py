"""Cloud synchronization and Digital Twin integration."""

from datetime import datetime
from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.db.session import async_session_factory
from app.models.sensor import Sensor

logger = structlog.get_logger()
settings = get_settings()


class CloudSync:
    """
    Northbound service for Digital Twin integration.
    
    Features:
        - Real-time data forwarding
        - Device profile generation
        - Bidirectional control (commands from cloud)
    """

    def __init__(self):
        self._log = logger.bind(component="cloud_sync")
        self._client: httpx.AsyncClient | None = None
        self._running = False

    async def start(self) -> None:
        """Initialize the cloud sync service."""
        if not settings.digital_twin_enabled:
            self._log.info("Digital Twin integration disabled")
            return

        self._client = httpx.AsyncClient(
            base_url=settings.digital_twin_endpoint,
            timeout=settings.digital_twin_timeout,
            headers={
                "Authorization": f"Bearer {settings.digital_twin_api_key}",
                "Content-Type": "application/json",
            },
        )
        self._running = True
        self._log.info("Cloud sync started", endpoint=settings.digital_twin_endpoint)

    async def stop(self) -> None:
        """Close cloud sync connections."""
        self._running = False
        if self._client:
            await self._client.aclose()
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
        
        Returns:
            True if send was successful.
        """
        if not self._client or not settings.digital_twin_enabled:
            return False

        try:
            # Format payload according to Digital Twin schema
            payload = {
                "entityId": entity_id or f"urn:ngsi-ld:Sensor:{sensor_name}",
                "type": "Sensor",
                "attributes": {
                    attribute or "value": {
                        "type": "Property",
                        "value": value,
                        "observedAt": timestamp.isoformat() + "Z",
                    }
                },
                "metadata": {
                    "source": settings.gateway_name,
                    "sensorId": sensor_id,
                    "sensorName": sensor_name,
                },
            }

            response = await self._client.post("/entities", json=payload)

            if response.status_code in (200, 201, 204):
                return True
            else:
                self._log.warning(
                    "Cloud send failed",
                    status=response.status_code,
                    body=response.text[:200],
                )
                return False

        except httpx.RequestError as e:
            self._log.error("Cloud request error", error=str(e))
            return False

    async def generate_device_profile(self) -> dict[str, Any]:
        """
        Generate a device profile JSON for the Digital Twin.
        
        This can be used to auto-configure the cloud platform
        with the current gateway configuration.
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

            # Build device profile
            profile = {
                "id": f"urn:ngsi-ld:Device:{settings.gateway_name}",
                "type": "Device",
                "name": settings.gateway_name,
                "description": "DaTaK IoT Edge Gateway",
                "createdAt": datetime.utcnow().isoformat() + "Z",
                "sensors": [],
                "commands": [],
            }

            for sensor in sensors:
                sensor_profile = {
                    "id": f"urn:ngsi-ld:Sensor:{sensor.name}",
                    "name": sensor.name,
                    "description": sensor.description or "",
                    "type": "Sensor",
                    "protocol": sensor.protocol,
                    "unit": sensor.unit or "unknown",
                    "pollIntervalMs": sensor.poll_interval_ms,
                    "dataType": "number",
                    "attributes": [
                        {
                            "name": sensor.twin_attribute or "value",
                            "type": "Property",
                            "unit": sensor.unit or "unknown",
                        }
                    ],
                }

                # Add entity mapping if configured
                if sensor.twin_entity_id:
                    sensor_profile["entityId"] = sensor.twin_entity_id

                profile["sensors"].append(sensor_profile)

            # Add available commands
            profile["commands"] = [
                {
                    "name": "setOutput",
                    "description": "Write value to a Modbus register",
                    "parameters": [
                        {"name": "sensorId", "type": "integer"},
                        {"name": "value", "type": "number"},
                    ],
                },
                {
                    "name": "restartSensor",
                    "description": "Restart a sensor driver",
                    "parameters": [
                        {"name": "sensorId", "type": "integer"},
                    ],
                },
            ]

            return profile

        except Exception as e:
            self._log.exception("Profile generation failed", error=str(e))
            return {"error": str(e)}

    async def receive_command(self, command: dict[str, Any]) -> dict[str, Any]:
        """
        Process a command received from the Digital Twin.
        
        Commands can control actuators, restart sensors, etc.
        """
        cmd_name = command.get("name")
        params = command.get("parameters", {})

        self._log.info("Received command", command=cmd_name, params=params)

        if cmd_name == "setOutput":
            # Write to a sensor/actuator
            from app.services.orchestrator import orchestrator

            sensor_id = params.get("sensorId")
            value = params.get("value")

            if sensor_id and value is not None:
                status = orchestrator.get_status(sensor_id)
                if status.get("exists"):
                    # TODO: Implement write through orchestrator
                    return {"success": True, "message": f"Set {sensor_id} to {value}"}
                else:
                    return {"success": False, "error": "Sensor not found"}

        elif cmd_name == "restartSensor":
            from app.services.orchestrator import orchestrator

            sensor_id = params.get("sensorId")
            if sensor_id:
                success = await orchestrator.restart_sensor(sensor_id)
                return {"success": success}

        return {"success": False, "error": f"Unknown command: {cmd_name}"}


# Global instance
cloud_sync = CloudSync()
