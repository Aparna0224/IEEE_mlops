# 🚀 Developer Handover Document: IEEE Paper Generator & MLOps Pipeline

Welcome to the **IEEE Paper Generator** project! This document serves as a comprehensive guide for new developers, data scientists, or DevOps engineers taking over this repository. It covers the architecture, setup, MLOps lifecycle, debugging, and deployment strategies.

---

## 1. Project Overview

The **IEEE Paper Generator** is an enterprise-grade AI system designed to draft, format, and grade academic papers automatically. 

**Key Components:**
- **Generative AI Engine:** Uses local **Ollama (Llama 3)** and **LangGraph** to research and draft IEEE-formatted text.
- **Discriminative ML Evaluator:** An embedded **XGBoost + Sentence-Transformers** model that grades the generated section quality.
- **MLOps Foundations:** Employs **DVC** for data versioning, **MLflow** for experiment tracking and model registry, and **GitHub Actions** for CI/CD.
- **Serving Layer:** A **FastAPI** backend that exposes both LangGraph orchestration and ML scoring over REST endpoints.
- **Monitoring:** Custom Python telemetry writing to JSON logs, parsed locally by a CLI dashboard.

---

## 2. Architecture Explanation

The system is split into multiple interacting pipelines:

1. **User Request (API):** Clients hit the FastAPI backend via REST. 
2. **Generative Pipeline:** `POST /api/langgraph/generate` triggers LangGraph, which iteratively queries Ollama to construct academic sections.
3. **Discriminative Pipeline:** `POST /api/mlops/evaluate-section` triggers the ML API. It calculates NLP features, runs Sentence-Transformers to get text embeddings, and feeds them into a trained XGBRegressor to output a quality score (0.0 to 1.0).
4. **Offline Training Pipeline:** Data Scientists modify `mlops/data/sections_v1.csv`. **DVC** detects this diff and triggers `mlops/train.py`, which registers a new model version via **MLflow**.
5. **CI/CD Pipeline:** **GitHub Actions** intercepts git pushes, runs the DVC retraining sequence, tests the FastPI endpoints, creates an artifact, and builds the production **Docker** image.

---

## 3. Folder Structure Explanation

```text
.
├── backend/                  # FastAPI application
│   ├── api.py                # Main web server entrypoint
│   ├── langgraph_routes.py   # LLM orchestration routes
│   └── mlops_routes.py       # ML inference endpoints
├── mlops/                    # Offline MLOps pipeline
│   ├── data/                 # DVC tracked CSV datasets
│   ├── monitor.py            # Local telemetry dashboard
│   └── train.py              # ML training, feature engineering, MLflow logging
├── models/                   # Serialized ML artifacts (.pkl) and Model registries
├── logs/                     # JSON metrics and error logs for API monitoring
├── outputs/                  # Generated IEEE .tex and .pdf artifacts
├── .github/workflows/        # CI/CD Yaml routines (mlops-pipeline.yml)
├── dvc.yaml                  # Data Versioning Control DAG instructions
├── Dockerfile                # Production multi-stage container
└── requirements.txt          # Python dependencies
```

---

## 4. How to Set Up the Project

Follow these steps to initialize the application on a fresh machine:

1. **Clone Repo & Install Dependencies**
   ```bash
   git clone <repository_url>
   cd IEEE-Paper-Generator
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run Ollama (Generative LLM Requirement)**
   Ensure the Ollama daemon is running globally on your host.
   ```bash
   ollama serve &
   ollama pull llama3
   ```

3. **Train the ML Model & Start MLflow**
   Initialize the model artifacts so the API doesn't crash on startup.
   ```bash
   dvc init
   dvc repro                 # Trains the model and tracks artifacts
   mlflow ui --backend-store-uri sqlite:///mlflow.db &
   ```
   *(View experiments at `http://localhost:5000`)*

4. **Run the Backend**
   ```bash
   python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "outputs/*" --reload-exclude "logs/*"
   ```

---

## 5. How the ML Pipeline Works

1. **Dataset (`mlops/data/sections_v1.csv`):** Contains human-annotated academic paragraphs with quality scores.
2. **Feature Engineering:** `mlops/train.py` calculates heuristic features (word counts, readability rules).
3. **Embeddings:** Extracts dense semantic vectors using `sentence-transformers` (`all-MiniLM-L6-v2`).
4. **Model Training:** Combines text vectors + heuristic features to train an **XGBoost Regressor** (`xgb.XGBRegressor`).
5. **MLflow Tracking:** Logs `max_depth`, `learning_rate`, `rmse`, and `mae` inside the local `mlflow.db`.
6. **Model Registry:** Automatically registers the champion algorithm into MLflow and transitions its alias to `"Production"`.

---

## 6. How to Retrain Model

If you get newly graded data or want to alter training features:
1. Update `mlops/data/sections_v1.csv` with new rows.
2. Tell DVC to observe the change:
   ```bash
   dvc add mlops/data/sections_v1.csv
   ```
3. Run the pipeline:
   ```bash
   dvc repro
   ```
   *DVC checks the file hashes. If the CSV changed, it reruns `train.py`. The new model overwrites the `.pkl` and bumps the MLflow version.*

---

## 7. How CI/CD Works

The pipeline is defined in `.github/workflows/mlops-pipeline.yml`. On every push to `main` or Pull Request:
1. **Install Dependencies:** Spins up Ubuntu, installs `requirements.txt`.
2. **Run Training:** Triggers the offline ML training logic ensuring no runtime compilation errors exist.
3. **Download Ollama & Llama 3:** Starts a local containerized Ollama instance on the GitHub runner.
4. **Test API:** Spins up Uvicorn in the background and hits `/api/mlops/evaluate-section` with an integration test `curl`.
5. **Build Docker:** Validates that the full `ieee-paper-generator:latest` image compiles cleanly.

---

## 8. How to Debug Issues

* **Model Not Loading (503 Error on `/evaluate-section`):**
  You forgot to train the model first. Run `python mlops/train.py` or `dvc repro`.
* **Ollama Not Running (Connection Refused):**
  Ensure the Ollama app is running locally. Check `http://127.0.0.1:11434`.
* **API Errors / 500s:**
  Check the Uvicorn trace or look inside `logs/mlops_errors.log`.
* **Task Interrupted by Server Restart:**
  Uvicorn is reloading because LangGraph saved a file. Ensure you boot Uvicorn with `--reload-exclude "outputs/*" --reload-exclude "logs/*"`.

---

## 9. Monitoring System

We inject telemetry for the discriminative ML layer manually. 
* **`logs/mlops_metrics.jsonl`**: Captures latency, request payload size, and predicted scores.
* **`logs/mlops_errors.log`**: Captures stack traces of failed requests.

**To view the real-time operational dashboard, run:**
```bash
python mlops/monitor.py
```

---

## 10. Deployment Guide

**Docker (Recommended for Production)**
The application is pre-configured in a multi-stage `Dockerfile`.
```bash
# Build the container (Includes the ML .pkl models inherently)
docker build -t ieee-paper-generator:latest .

# Run the container mapping Port 8000
docker run -p 8000:8000 ieee-paper-generator:latest
```

*(Note: To connect the containerized FastAPI to a host-level Ollama service, you may need to pass `--add-host=host.docker.internal:host-gateway` and set external ENV variables).*

---

## 11. Important Configurations

Key environment variables (can be placed in an `.env` file):
* `MODEL_PROVIDER`: Enforced as `"ollama"`. (Historical Groq hooks were stripped).
* `OLLAMA_BASE_URL`: Defaults to `http://localhost:11434`. Change if Ollama is running on a different server.
* `PORT`: Default 8000 for FastAPI.

---

## 12. Known Limitations

* **Small Dataset:** The existing `sections_v1.csv` is a dummy sample. The XGBoost model will overfit rapidly until thousands of real labeled paragraphs are provided.
* **No UI Dashboard:** The current monitor is CLI-based. There is no web-based Grafana implementation yet.
* **Synchronous ML execution:** The XGBoost inference runs on the main FastAPI asyncio event loop, which could block concurrent requests under heavy load.

---

## 13. Future Work

* **Scaling inference:** Move the ML `/evaluate-section` inference to a dedicated Celery/Redis worker queue rather than synchronous FastAPI threads.
* **Model Improvements:** Upgrade from XGBoost to a fully fine-tuned BERT layer if grading requires deep contextual analysis instead of heuristics + basic embeddings.
* **Automated Data Flywheel:** Pipe user corrections from the frontend back into `sections_v1.csv` on S3 automatically for continuous nightly retraining loops.

---

## 14. Contact / Ownership

**Maintainer:** [Your Name / Team Name]
**Email:** [Your Email]
**Project Link:** [Repository URL]

*End of Document. Happy Coding!* 🚀
