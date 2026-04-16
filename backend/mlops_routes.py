from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import joblib
import numpy as np
import time
import os
import json

router = APIRouter()

# Global variables for models (loaded on startup)
ML_MODEL = None
EMBEDDING_MODEL = None

class SectionInput(BaseModel):
    text: str
    section_type: str = "General"

class SectionScore(BaseModel):
    score: float
    category: str
    latency_ms: float

def compute_readability(text: str) -> float:
    return len(text.split()) / max(text.count('.') + 1, 1)

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

@router.post("/evaluate-section", response_model=SectionScore)
async def evaluate_section(data: SectionInput, request: Request):
    """Evaluate a research paper section using trained ML model"""
    start_time = time.time()
    
    if ML_MODEL is None or EMBEDDING_MODEL is None:
        raise HTTPException(status_code=503, detail="ML Model not loaded.")
        
    try:
        text = str(data.text)
        
        # 1. Feature Engineering matching training mapping
        word_count = len(text.split())
        readability = compute_readability(text)
        dense_vec = EMBEDDING_MODEL.encode([text])[0]
        
        # 2. Combine Features
        features = np.hstack([[word_count, readability], dense_vec]).reshape(1, -1)
        
        # 3. Inference
        predicted_score = float(ML_MODEL.predict(features)[0])
        
        # 4. Classification Thresholding
        if predicted_score >= 0.8:
            category = "Excellent"
        elif predicted_score >= 0.5:
            category = "Needs Improvement"
        else:
            category = "Poor"
            
        # 5. Monitoring / Logging
        latency_ms = (time.time() - start_time) * 1000
        
        log_entry = {
            "timestamp": time.time(),
            "endpoint": "/evaluate-section",
            "section_type": data.section_type,
            "input_words": word_count,
            "predicted_score": predicted_score,
            "latency_ms": latency_ms,
            "client_ip": request.client.host
        }
        
        os.makedirs("logs", exist_ok=True)
        with open("logs/mlops_metrics.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        return SectionScore(score=predicted_score, category=category, latency_ms=latency_ms)
        
    except Exception as e:
        # Error Monitoring Log
        with open("logs/mlops_errors.log", "a") as f:
            f.write(f"{time.time()} - /evaluate-section Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))
