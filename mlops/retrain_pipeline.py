"""
retrain_pipeline.py — Automated Retraining Orchestrator

Triggered automatically by GitHub Actions when drift_check.py exits with code 1.
Implements a Champion/Challenger pattern using MLflow:
  1. Augments training data with synthetic samples
  2. Retrains the XGBoost model
  3. Compares new model (challenger) against current Production model (champion)
  4. Promotes challenger only if it achieves better R² score
  5. Writes a retrain log entry to logs/retrain_log.jsonl

Usage:
  python mlops/retrain_pipeline.py
  python mlops/retrain_pipeline.py --force   # skip champion check, always promote
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import mlflow
import numpy as np
import pandas as pd
import joblib
from mlflow.tracking import MlflowClient
from sentence_transformers import SentenceTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, train_test_split
import xgboost as xgb

# ─── Constants ────────────────────────────────────────────────────────────────

DATA_FILE         = "mlops/data/sections_v1.csv"
MODEL_PATH        = "models/section_quality_xgboost.pkl"
RETRAIN_LOG       = "logs/retrain_log.jsonl"
DRIFT_REPORT      = "logs/drift_report.json"
MLFLOW_DB         = "sqlite:///mlflow.db"
EXPERIMENT_NAME   = "IEEE_Section_Quality_Predictor"
REGISTERED_NAME   = "IEEE_Section_Quality_XGBoost"
MIN_R2_IMPROVEMENT = 0.01  # challenger must beat champion by at least this much


# ─── Feature Engineering ──────────────────────────────────────────────────────

def compute_readability(text: str) -> float:
    return len(text.split()) / max(text.count(".") + 1, 1)


def extract_features(df: pd.DataFrame, emb_model: SentenceTransformer):
    df["word_count"]  = df["text"].apply(lambda x: len(str(x).split()))
    df["readability"] = df["text"].apply(lambda x: compute_readability(str(x)))
    embeddings = emb_model.encode(df["text"].tolist(), show_progress_bar=True)
    X = np.hstack([df[["word_count", "readability"]].values, embeddings])
    y = df["score"].values
    return X, y


# ─── Data Augmentation ────────────────────────────────────────────────────────

def augment_data(num_samples: int = 150) -> int:
    """Add synthetic rows to the training CSV. Returns number of rows added."""
    import random
    import csv

    topics = [
        "deep learning", "quantum computing", "blockchain", "NLP architectures",
        "computer vision", "reinforcement learning", "cybersecurity",
        "edge computing", "federated learning", "5G networks",
    ]
    sections = ["Abstract", "Introduction", "Methodology", "Results", "Conclusion"]

    good = [
        "This paper explores {topic} to improve efficiency. Our novel approach yields a {m}% improvement over baselines.",
        "We introduce a robust framework for {topic}. Extensive evaluation demonstrates superior real-world performance.",
        "The proposed methodology leverages {topic} to address existing limitations. Experimental results confirm theoretical advantages.",
    ]
    avg = [
        "In this study we looked at {topic}. It is somewhat better than previous methods.",
        "We use {topic} in our model. It works okay on the test dataset.",
        "The experiments show that {topic} can be useful sometimes. More research is needed.",
    ]
    bad = [
        "We did {topic} and it didn't really work.",
        "this paper is about {topic}. very cool stuff.",
        "bad results for {topic}. unclear methodology.",
    ]

    new_rows = []
    for _ in range(num_samples):
        topic   = random.choice(topics)
        section = random.choice(sections)
        m       = random.randint(10, 50)
        quality = random.choices(["good", "avg", "bad"], weights=[0.5, 0.3, 0.2])[0]

        if quality == "good":
            text  = random.choice(good).format(topic=topic, m=m)
            score = round(random.uniform(0.75, 0.98), 2)
            vals  = [round(random.uniform(0.8, 1.0), 2)] * 4
        elif quality == "avg":
            text  = random.choice(avg).format(topic=topic, m=m)
            score = round(random.uniform(0.40, 0.74), 2)
            vals  = [round(random.uniform(0.4, 0.7), 2)] * 4
        else:
            text  = random.choice(bad).format(topic=topic, m=m)
            score = round(random.uniform(0.10, 0.39), 2)
            vals  = [round(random.uniform(0.1, 0.3), 2)] * 4

        new_rows.append([section, text, score] + vals)

    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

    print(f"[RETRAIN] ✅  Augmented dataset with {len(new_rows)} synthetic rows → {DATA_FILE}")
    return len(new_rows)


# ─── Champion Score ───────────────────────────────────────────────────────────

def get_champion_r2(client: MlflowClient) -> float | None:
    """Retrieve the R² of the current Production model from MLflow registry."""
    try:
        prod_versions = client.get_latest_versions(REGISTERED_NAME, stages=["Production"])
        if not prod_versions:
            print("[RETRAIN] No Production model found in MLflow registry → treating as first run.")
            return None
        run_id = prod_versions[0].run_id
        run    = client.get_run(run_id)
        r2     = run.data.metrics.get("r2")
        print(f"[RETRAIN] Champion model → run_id={run_id}  R²={r2}")
        return r2
    except Exception as exc:
        print(f"[RETRAIN] ⚠️  Could not retrieve champion R²: {exc}")
        return None


# ─── Training ─────────────────────────────────────────────────────────────────

def train(emb_model: SentenceTransformer) -> dict:
    """Train a new XGBoost challenger model and log to MLflow."""
    print(f"\n[RETRAIN] Loading dataset from {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE)
    print(f"[RETRAIN] Dataset size: {len(df)} rows")

    X, y = extract_features(df, emb_model)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    param_grid = {
        "n_estimators":  [50, 100],
        "max_depth":     [3, 5],
        "learning_rate": [0.05, 0.1],
    }

    with mlflow.start_run(run_name="auto_retrain") as run:
        mlflow.set_tag("trigger", "auto_drift_detection")
        mlflow.set_tag("triggered_at", datetime.utcnow().isoformat())

        print("[RETRAIN] Starting GridSearchCV hyperparameter tuning...")
        gs = GridSearchCV(
            xgb.XGBRegressor(random_state=42),
            param_grid,
            scoring="neg_mean_squared_error",
            cv=3,
            verbose=1,
        )
        gs.fit(X_train, y_train)

        best       = gs.best_estimator_
        best_params = gs.best_params_
        best_params["embedding_model"] = "all-MiniLM-L6-v2"
        mlflow.log_params(best_params)

        y_pred = best.predict(X_test)
        mae  = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2   = r2_score(y_test, y_pred)

        mlflow.log_metric("mae",  mae)
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("r2",   r2)

        print(f"[RETRAIN] Challenger → MAE={mae:.4f}  RMSE={rmse:.4f}  R²={r2:.4f}")

        # Save model artefact
        os.makedirs("models", exist_ok=True)
        joblib.dump(best, MODEL_PATH)
        mlflow.sklearn.log_model(best, "xgboost-model")

        return {
            "run_id":  run.info.run_id,
            "mae":     mae,
            "rmse":    rmse,
            "r2":      r2,
            "params":  best_params,
        }


# ─── Champion / Challenger Promotion ─────────────────────────────────────────

def promote_if_better(client: MlflowClient, challenger: dict, champion_r2: float | None, force: bool) -> bool:
    """Register challenger and promote to Production if it beats the champion."""
    model_uri  = f"runs:/{challenger['run_id']}/xgboost-model"
    mv = mlflow.register_model(model_uri, REGISTERED_NAME)

    should_promote = force or (champion_r2 is None) or (challenger["r2"] >= champion_r2 + MIN_R2_IMPROVEMENT)

    if should_promote:
        client.transition_model_version_stage(
            name=REGISTERED_NAME,
            version=mv.version,
            stage="Production",
        )
        # Archive old production versions
        for old in client.get_latest_versions(REGISTERED_NAME, stages=["Production"]):
            if old.version != mv.version:
                client.transition_model_version_stage(
                    name=REGISTERED_NAME, version=old.version, stage="Archived"
                )
        print(f"[RETRAIN] 🚀  Challenger v{mv.version} promoted to Production  (R²={challenger['r2']:.4f})")
        return True
    else:
        client.transition_model_version_stage(
            name=REGISTERED_NAME,
            version=mv.version,
            stage="Archived",
        )
        print(
            f"[RETRAIN] ⚠️  Challenger NOT promoted — improvement insufficient."
            f"\n           Champion R²={champion_r2:.4f}  Challenger R²={challenger['r2']:.4f}"
            f"  (need ≥ +{MIN_R2_IMPROVEMENT})"
        )
        return False


# ─── Retrain Log ─────────────────────────────────────────────────────────────

def write_retrain_log(entry: dict) -> None:
    os.makedirs(os.path.dirname(RETRAIN_LOG), exist_ok=True)
    with open(RETRAIN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[RETRAIN] Log entry written → {RETRAIN_LOG}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force", action="store_true",
        help="Skip champion comparison and always promote the new model."
    )
    args = parser.parse_args()

    started_at = time.time()
    print("=" * 55)
    print("   IEEE MLOps — Automated Retraining Pipeline")
    print("=" * 55)
    print(f"[RETRAIN] Started at: {datetime.utcnow().isoformat()}Z")
    print(f"[RETRAIN] Force promote: {args.force}\n")

    # Load drift context
    drift_context = {}
    if os.path.exists(DRIFT_REPORT):
        try:
            with open(DRIFT_REPORT) as f:
                drift_context = json.load(f)
            print(f"[RETRAIN] Drift triggers: {drift_context.get('triggered_checks', [])}")
        except Exception:
            pass

    # Setup MLflow
    mlflow.set_tracking_uri(MLFLOW_DB)
    mlflow.set_experiment(EXPERIMENT_NAME)
    client = MlflowClient()

    # 1. Augment data
    print("\n[RETRAIN] Step 1/4 — Augmenting training data...")
    rows_added = augment_data(num_samples=150)

    # 2. Load embedding model
    print("\n[RETRAIN] Step 2/4 — Loading sentence-transformer embedding model...")
    emb_model = SentenceTransformer("all-MiniLM-L6-v2")

    # 3. Get champion R² and train challenger
    print("\n[RETRAIN] Step 3/4 — Retrieving champion metrics from MLflow registry...")
    champion_r2 = get_champion_r2(client)

    print("\n[RETRAIN] Step 4/4 — Training challenger model...")
    challenger = train(emb_model)

    # 4. Promote if better
    promoted = promote_if_better(client, challenger, champion_r2, args.force)

    # 5. Write retrain log
    duration = round(time.time() - started_at, 2)
    log_entry = {
        "timestamp":    datetime.utcnow().isoformat() + "Z",
        "duration_sec": duration,
        "promoted":     promoted,
        "force":        args.force,
        "challenger": {
            "run_id": challenger["run_id"],
            "r2":     round(challenger["r2"],   4),
            "mae":    round(challenger["mae"],  4),
            "rmse":   round(challenger["rmse"], 4),
        },
        "champion_r2": round(champion_r2, 4) if champion_r2 is not None else None,
        "rows_added":  rows_added,
        "drift_triggers": drift_context.get("triggered_checks", []),
    }
    write_retrain_log(log_entry)

    # 6. Summary
    print("\n" + "=" * 55)
    if promoted:
        print("  ✅  RETRAINING COMPLETE — New model deployed to Production")
    else:
        print("  ⚠️   RETRAINING COMPLETE — Challenger did not beat champion")
    print(f"  Duration: {duration}s")
    print("=" * 55)

    # Exit 0 always — the retrain itself is not a failure
    sys.exit(0)


if __name__ == "__main__":
    main()
