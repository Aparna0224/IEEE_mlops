from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import joblib
import numpy as np
import time
import os
import json
import statistics
from datetime import datetime
from typing import Optional

router = APIRouter()

# ─── Global model state (loaded on startup) ───────────────────────────────────
ML_MODEL       = None
EMBEDDING_MODEL = None

# ─── File paths ───────────────────────────────────────────────────────────────
METRICS_FILE  = "logs/mlops_metrics.jsonl"
ERROR_FILE    = "logs/mlops_errors.log"
DRIFT_REPORT  = "logs/drift_report.json"
RETRAIN_LOG   = "logs/retrain_log.jsonl"
ROLLING_WINDOW = 50   # last N predictions used for dashboard stats

# ─── Pydantic models ──────────────────────────────────────────────────────────
class SectionInput(BaseModel):
    text: str
    section_type: str = "General"

class SectionScore(BaseModel):
    score: float
    category: str
    latency_ms: float

# ─── Helpers ──────────────────────────────────────────────────────────────────
def compute_readability(text: str) -> float:
    return len(text.split()) / max(text.count('.') + 1, 1)

def _load_recent_metrics(window: int = ROLLING_WINDOW) -> list:
    records = []
    if not os.path.exists(METRICS_FILE):
        return records
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records[-window:]

def _count_errors() -> int:
    if not os.path.exists(ERROR_FILE):
        return 0
    with open(ERROR_FILE, "r", encoding="utf-8") as f:
        return sum(1 for ln in f if ln.strip())

def _load_drift_report() -> dict:
    if not os.path.exists(DRIFT_REPORT):
        return {"message": "Drift check has not been run yet."}
    try:
        with open(DRIFT_REPORT, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"error": "Could not parse drift report."}

def _last_retrain_entry() -> Optional[dict]:
    if not os.path.exists(RETRAIN_LOG):
        return None
    last = None
    with open(RETRAIN_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                last = json.loads(line)
            except Exception:
                pass
    return last

# ─── Startup: load ML models ──────────────────────────────────────────────────
@router.on_event("startup")
async def load_ml_models():
    global ML_MODEL, EMBEDDING_MODEL
    model_path = "models/section_quality_xgboost.pkl"
    try:
        print(f"Loading ML model from {model_path}...")
        ML_MODEL = joblib.load(model_path)
        from sentence_transformers import SentenceTransformer
        EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
        print("ML Models loaded successfully.")
    except Exception as e:
        print(f"WARNING: ML Models not found or failed to load. Train model first! {e}")

# ─── Route 1: Evaluate Section ────────────────────────────────────────────────
@router.post("/evaluate-section", response_model=SectionScore)
async def evaluate_section(data: SectionInput, request: Request):
    """Evaluate a research paper section using the trained XGBoost ML model."""
    start_time = time.time()

    if ML_MODEL is None or EMBEDDING_MODEL is None:
        raise HTTPException(status_code=503, detail="ML Model not loaded.")

    try:
        text = str(data.text)

        # Feature engineering (must match training pipeline)
        word_count  = len(text.split())
        readability = compute_readability(text)
        dense_vec   = EMBEDDING_MODEL.encode([text])[0]
        features    = np.hstack([[word_count, readability], dense_vec]).reshape(1, -1)

        predicted_score = float(ML_MODEL.predict(features)[0])

        if predicted_score >= 0.8:
            category = "Excellent"
        elif predicted_score >= 0.5:
            category = "Needs Improvement"
        else:
            category = "Poor"

        latency_ms = (time.time() - start_time) * 1000

        # Log inference for monitoring
        log_entry = {
            "timestamp":       time.time(),
            "endpoint":        "/evaluate-section",
            "section_type":    data.section_type,
            "input_words":     word_count,
            "predicted_score": predicted_score,
            "latency_ms":      latency_ms,
            "client_ip":       request.client.host,
        }
        os.makedirs("logs", exist_ok=True)
        with open(METRICS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

        return SectionScore(score=predicted_score, category=category, latency_ms=latency_ms)

    except Exception as e:
        os.makedirs("logs", exist_ok=True)
        with open(ERROR_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.time()} - /evaluate-section Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Route 2: MLOps Monitoring Dashboard ──────────────────────────────────────
@router.get("/dashboard")
async def mlops_dashboard():
    """
    Real-time MLOps monitoring dashboard.

    Returns live statistics computed from inference logs:
    - Request counts, latency, error rate
    - Score distribution and drift status
    - Last drift check result
    - Last retraining run details
    """
    records   = _load_recent_metrics(ROLLING_WINDOW)
    err_count = _count_errors()
    total     = len(records) + err_count

    scores    = [r["predicted_score"] for r in records if "predicted_score" in r]
    latencies = [r["latency_ms"]      for r in records if "latency_ms"      in r]

    # Score distribution
    score_distribution = {"Excellent": 0, "Needs Improvement": 0, "Poor": 0}
    for s in scores:
        if s >= 0.8:
            score_distribution["Excellent"]         += 1
        elif s >= 0.5:
            score_distribution["Needs Improvement"] += 1
        else:
            score_distribution["Poor"]              += 1

    # Drift detection inline summary
    drift_report  = _load_drift_report()
    retrain_entry = _last_retrain_entry()

    performance = {
        "total_requests":     total,
        "successful_requests": len(records),
        "error_count":        err_count,
        "error_rate_pct":     round((err_count / total * 100), 2) if total else 0.0,
        "rolling_window":     ROLLING_WINDOW,
    }

    model_stats = {
        "predictions_tracked":  len(scores),
        "avg_predicted_score":  round(statistics.mean(scores),     4) if scores    else None,
        "min_predicted_score":  round(min(scores),                  4) if scores    else None,
        "max_predicted_score":  round(max(scores),                  4) if scores    else None,
        "score_variance":       round(statistics.variance(scores),  6) if len(scores) > 1 else None,
        "avg_latency_ms":       round(statistics.mean(latencies),   2) if latencies else None,
        "max_latency_ms":       round(max(latencies),               2) if latencies else None,
        "score_distribution":   score_distribution,
    }

    # Simple inline drift flag for dashboard consumers
    drift_flag = "unknown"
    if scores:
        avg_score = statistics.mean(scores)
        if avg_score < 0.40:
            drift_flag = "drift_detected"
        elif len(set(round(s, 2) for s in scores)) == 1 and len(scores) > 5:
            drift_flag = "model_collapse"
        else:
            drift_flag = "stable"

    return {
        "generated_at":    datetime.utcnow().isoformat() + "Z",
        "model_status":    "loaded" if ML_MODEL is not None else "not_loaded",
        "drift_status":    drift_flag,
        "performance":     performance,
        "model_stats":     model_stats,
        "last_drift_check": drift_report,
        "last_retrain":    retrain_entry,
    }


# ─── Route 3: Export Logs ─────────────────────────────────────────────────────
@router.get("/export-logs")
async def export_logs():
    """
    Download the raw inference metrics log (mlops_metrics.jsonl).
    Used by the GitHub Actions scheduled job to persist logs across deploys.
    """
    if not os.path.exists(METRICS_FILE):
        raise HTTPException(status_code=404, detail="No inference logs found yet.")
    return FileResponse(
        path=METRICS_FILE,
        media_type="application/x-ndjson",
        filename="mlops_metrics.jsonl",
    )
