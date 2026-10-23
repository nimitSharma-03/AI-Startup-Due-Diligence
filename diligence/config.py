"""Runtime configuration read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _list(value: str | None) -> list[str]:
    return [item.strip().rstrip("/") for item in (value or "").split(",") if item.strip()]


@dataclass
class Config:
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "production"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    # Cross-origin callers allowed to use the API. The bundled frontend is
    # served from the same origin and needs no entry here.
    cors_origins: list[str] = field(default_factory=lambda: _list(os.getenv("CORS_ORIGINS")))
    max_upload_mb: float = field(default_factory=lambda: float(os.getenv("MAX_UPLOAD_MB", "5")))
    upload_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("UPLOAD_TTL_SECONDS", "7200")))
    max_uploads: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOADS", "20")))
    max_batch_records: int = 1000
    model_dir: Path = field(default_factory=lambda: Path(os.getenv("MODEL_DIR", ROOT / "model")))
    reference_csv: Path = field(default_factory=lambda: Path(os.getenv("REFERENCE_CSV", ROOT / "data" / "CleanStartups.csv")))
    frontend_dist: Path = field(default_factory=lambda: Path(os.getenv("FRONTEND_DIST", ROOT / "frontend" / "dist")))

    def __post_init__(self) -> None:
        if self.env == "development" and not self.cors_origins:
            self.cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def max_content_length(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)
