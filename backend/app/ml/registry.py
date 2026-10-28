"""
Model registry — tracks which model version is currently 'live'.

This is a lightweight MLOps pattern: we never overwrite model artifacts, we
version them and point a single pointer file (registry.json) at the active one.
This gives us free rollback — change one line in registry.json to revert.
"""
import json
from datetime import datetime
from pathlib import Path

from app.config import settings

REGISTRY_FILENAME = "registry.json"


def _registry_path() -> Path:
    return settings.ml_models_path / REGISTRY_FILENAME


def set_active_model(
    path: str,
    accuracy: float,
    sample_count: int,
    classes: list[str],
    per_class_f1: dict[str, float] | None = None,
    confusion_matrix: dict | None = None,
) -> None:
    """Record a newly-trained model as the live one."""
    data = {
        "active_model_path": path,
        "accuracy": accuracy,
        "trained_on_samples": sample_count,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "classes": classes,
        "per_class_f1": per_class_f1 or {},
        "confusion_matrix": confusion_matrix or {},
    }
    _registry_path().write_text(json.dumps(data, indent=2))
    # Invalidate the inference cache so the next prediction picks up the new model
    _invalidate_cache()


def get_active_model_info() -> dict | None:
    """Return current registry contents, or None if no model is registered."""
    rp = _registry_path()
    if not rp.exists():
        return None
    return json.loads(rp.read_text())


def _invalidate_cache() -> None:
    """Clear the lru_cache on the inference model loader (lazy import)."""
    try:
        from app.ml.inference import categoriser_service
        categoriser_service._load_model.cache_clear()
    except Exception:
        pass


def list_model_versions() -> list[dict]:
    """List all saved model artifacts — useful for a 'rollback' UI."""
    md = settings.ml_models_path
    if not md.exists():
        return []
    return sorted(
        [
            {
                "filename": p.name,
                "size_kb": round(p.stat().st_size / 1024, 1),
                "created_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            }
            for p in md.glob("categoriser_*.joblib")
        ],
        key=lambda x: x["created_at"],
        reverse=True,
    )
