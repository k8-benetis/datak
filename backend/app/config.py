"""Application configuration using pydantic-settings."""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class Settings(BaseSettings):
    """Application settings loaded from environment and config file."""

    model_config = SettingsConfigDict(
        env_prefix="DATAK_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Gateway
    gateway_name: str = "DaTaK-Gateway"
    log_level: str = "INFO"
    data_dir: Path = Path("data")

    # Database (SQLite)
    database_url: str = "sqlite+aiosqlite:///data/gateway.db"
    database_echo: bool = False

    # InfluxDB
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = "datak-dev-token"
    influxdb_org: str = "datak"
    influxdb_bucket: str = "sensors"
    influxdb_retention_days: int = 30

    # MQTT
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_client_id: str = "datak-gateway"
    mqtt_username: str | None = None
    mqtt_password: str | None = None

    # Digital Twin
    digital_twin_enabled: bool = False
    digital_twin_endpoint: str = ""
    digital_twin_api_key: str = ""
    digital_twin_timeout: int = 10

    # Security
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    token_expire_minutes: int = 1440

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://100.95.129.22:5173",
    ]

    # Reports
    reports_enabled: bool = True
    reports_output_dir: Path = Path("data/exports")

    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 9100

    @field_validator("data_dir", "reports_output_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: Any) -> Path:
        """Convert string to Path."""
        return Path(v) if isinstance(v, str) else v

    @classmethod
    def from_yaml(cls, config_path: Path) -> "Settings":
        """Load settings from YAML config file."""
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

        # Flatten nested config to match env var style
        flat_config: dict[str, Any] = {}

        def flatten(data: dict, prefix: str = "") -> None:
            for key, value in data.items():
                full_key = f"{prefix}{key}" if prefix else key
                if isinstance(value, dict):
                    flatten(value, f"{full_key}_")
                else:
                    flat_config[full_key] = value

        flatten(config)
        return cls(**flat_config)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    config_path = Path("configs/gateway.yaml")
    return Settings.from_yaml(config_path)
