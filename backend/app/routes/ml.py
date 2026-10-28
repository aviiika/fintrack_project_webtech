"""
ML API endpoints — this is what powers the Model Insights page in the frontend.

These routes make the machine learning layer visible, controllable, and testable
through the UI, which is the single most important thing for a viva demo.
"""
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Query

from app.ml.inference.anomaly_service import flag_anomalies
from app.ml.inference.categoriser_service import predict_category
from app.ml.inference.forecast_service import project_month_end
from app.ml.registry import get_active_model_info, list_model_versions
from app.ml.training.train_categoriser import train
from app.schemas.all import (
    AnomalyFlag,
    CategoryPrediction,
    CorrectionStatus,
    ModelInfo,
    PredictionRequest,
    RetrainResult,
    SpendForecast,
)
from app.services.transaction_service import get_correction_status
from app.utils.deps import CurrentUser, DbSession

router = APIRouter(prefix="/ml", tags=["machine learning"])


# ─── Model metadata ──────────────────────────────────────────────────────────

@router.get("/model-info", response_model=ModelInfo)
async def model_info(cu: CurrentUser) -> ModelInfo:
    """Return metadata about the currently-active model.

    Called by the Model Insights page on load. If no model is trained yet,
    returns status='no_model_trained', so the UI can show "using keyword rules".
    """
    info = get_active_model_info()
    if info is None:
        return ModelInfo(status="no_model_trained", using="keyword_rules")

    return ModelInfo(
        status="active",
        using="ml_with_fallback",
        active_model_path=info["active_model_path"],
        accuracy=info["accuracy"],
        trained_on_samples=info["trained_on_samples"],
        trained_at=datetime.fromisoformat(info["trained_at"]),
        classes=info["classes"],
        per_class_f1=info.get("per_class_f1"),
        confusion_matrix=info.get("confusion_matrix"),
    )


@router.get("/versions")
async def versions(cu: CurrentUser):
    """List all saved model artifacts (newest first). Enables rollback UI."""
    return {"versions": list_model_versions()}


# ─── Live inference preview ──────────────────────────────────────────────────

@router.post("/predict", response_model=CategoryPrediction)
async def predict_preview(payload: PredictionRequest, cu: CurrentUser) -> CategoryPrediction:
    """Preview what the categoriser would predict for a description.

    Used by the Model Insights page's "try it" box — the user types a
    description and sees the predicted category + confidence immediately.
    """
    result = predict_category(payload.description, payload.txn_type)
    return CategoryPrediction(**result)


# ─── Retraining ──────────────────────────────────────────────────────────────

@router.post("/retrain", response_model=RetrainResult)
async def retrain(db: DbSession, cu: CurrentUser) -> RetrainResult:
    """Manually trigger a retrain.

    In a larger production system this would enqueue a background job;
    for this scale, inline execution is correct (training takes <1s).
    """
    try:
        result = train(db=db)
    except Exception as e:
        raise HTTPException(500, f"Training failed: {e}") from e

    info = await model_info(cu) if result["status"] == "trained" else None
    return RetrainResult(
        status=result["status"],
        message=result["message"],
        model_info=info,
    )


# ─── Feedback loop status ────────────────────────────────────────────────────

@router.get("/correction-status", response_model=CorrectionStatus)
async def correction_status(db: DbSession, cu: CurrentUser) -> CorrectionStatus:
    """How many corrections until the next automatic retrain fires?"""
    return CorrectionStatus(**get_correction_status(db, cu.id))


# ─── Anomaly detection ───────────────────────────────────────────────────────

@router.get("/anomalies", response_model=list[AnomalyFlag])
async def anomalies(db: DbSession, cu: CurrentUser,
                     month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")):
    """Return statistically-unusual transactions (z-score > 2.5 vs user's own history)."""
    return [AnomalyFlag(**a) for a in flag_anomalies(db, cu.id, month=month)]


# ─── Spending forecast ───────────────────────────────────────────────────────

@router.get("/forecast", response_model=SpendForecast)
async def forecast(db: DbSession, cu: CurrentUser) -> SpendForecast:
    """Project this month's total spending from partial data (linear trend)."""
    return SpendForecast(**project_month_end(db, cu.id))
