from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{BASE_DIR}/data/netsec.db"
    upload_dir: Path = BASE_DIR / "uploads"
    reports_dir: Path = BASE_DIR / "reports"
    samples_dir: Path = BASE_DIR / "data" / "samples"

    # Brute force detection
    brute_force_threshold: int = 5
    brute_force_window_minutes: int = 5

    # Port scan detection
    port_scan_threshold: int = 15
    port_scan_window_minutes: int = 2

    # Traffic spike detection (std deviations from mean)
    traffic_spike_threshold: float = 3.0

    # Off-hours detection (24h format)
    business_hours_start: int = 7
    business_hours_end: int = 19

    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env"}


settings = Settings()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.reports_dir.mkdir(parents=True, exist_ok=True)
settings.samples_dir.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
