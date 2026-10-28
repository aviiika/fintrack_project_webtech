from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "FinTrack Pro API"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    database_url: str = "sqlite:///./fintrack.db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    ml_models_dir: str = "app/ml/models"
    # Confidence gating is computed RELATIVE to the number of categories rather
    # than hardcoded, because an absolute threshold silently assumes a binary
    # classifier. With 13 categories, a softmax rarely exceeds ~0.35 even when
    # the prediction is right, so a fixed 0.55 made the ML path unreachable --
    # the model trained fine and then never once got to decide. See
    # categoriser_service.confidence_threshold() for the formula.
    ml_confidence_multiplier: float = 2.5   # x random baseline (1 / n_classes)
    ml_confidence_floor: float = 0.15       # never trust less than this
    ml_confidence_ceiling: float = 0.60     # never demand more than this
    ml_confidence_margin: float = 0.04      # top-1 must beat top-2 by this much
    ml_min_training_samples: int = 50
    ml_retrain_every_n_corrections: int = 25
    # Week 2: stock portfolio
    stock_price_cache_ttl_seconds: int = 60
    ws_push_interval_seconds: int = 5
    # Week 3: net worth / scheduler
    networth_snapshot_hour: int = 2
    enable_background_jobs: bool = True

    @property
    def cors_origins_list(self): return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    @property
    def ml_models_path(self):
        p = Path(self.ml_models_dir); p.mkdir(parents=True, exist_ok=True); return p

@lru_cache
def get_settings(): return Settings()
settings = get_settings()
