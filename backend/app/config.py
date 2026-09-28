"""Application configuration, loaded entirely from environment variables.

No secrets or connection strings are hardcoded anywhere in this project.
See .env.example at the repo root for the full list of variables.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "network_dashboard"
    postgres_user: str = "dashboard_user"
    postgres_password: str = "changeme"

    # --- App ---
    log_level: str = "info"
    log_json: bool = False
    cors_origins: str = "http://localhost:5173"

    # --- Network diagnostics ---
    ping_count: int = 3
    ping_timeout_seconds: int = 2
    ping_latency_warning_ms: float = 150.0
    http_timeout_seconds: int = 5
    traceroute_timeout_seconds: int = 10

    # --- Nmap ---
    nmap_top_ports: int = 100
    nmap_timeout_seconds: int = 180
    nmap_max_top_ports: int = 1000  # hard ceiling, even if a caller requests more

    # --- Optional packet capture (tshark) ---
    enable_packet_capture: bool = False
    packet_capture_interface: str = "any"
    packet_capture_duration_seconds: int = 5
    packet_capture_max_packets: int = 200

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
