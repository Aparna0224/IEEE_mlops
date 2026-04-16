# IEEE Paper Generator - End-to-End MLOps Pipeline

An enterprise-grade, AI-powered system that generates IEEE-formatted research papers using Large Language Models (LLMs) and automatically grades the quality of the generated sections using a discriminative Machine Learning classifier. 

This project demonstrates a **complete production MLOps lifecycle**—incorporating data versioning, experiment tracking, model registries, containerization, CI/CD automation, and real-time inference monitoring.

---

## 1. Architecture

The system balances **Generative AI** (for creation) and **Discriminative ML** (for evaluation). 

```text
[End User] 
    │ (REST API Call)
    ▼
[FastAPI Backend] ──► [Ollama (Llama 3)] (Generates Paper Sections)
    │
    ▼
[MLOps Router (/evaluate-section)] ──► [XGBoost Model] (Evaluates Section Quality)
    │
    ├─► Reads: logs/mlops_metrics.jsonl (Monitoring Datastore)
    ├─► Loads: models/section_quality_xgboost.pkl (Registered Artifact)
    │
    ▼
[DVC Retraining Pipeline] (Triggered via GitHub Actions)
    │ 
    ├─► Data Tracking: mlops/data/sections_v1.csv
    ├─► ML script: mlops/train.py
    │
    ▼
[MLflow API] (Tracks Params, Metrics, transitions to 'Production' Registry)
```

---

## 2. Features

- **Generative Paper Creation:** Uses highly-orchestrated local LLM agents (over LangGraph & Ollama) to draft context-aware sections.
- **Section Quality Evaluation:** An embedded Machine Learning pipeline that maps textual semantics to quality thresholds (Excellent, Needs Improvement, Poor).
- **Data Versioning:** Dataset tracking via **DVC**, preventing unwanted model drift and allowing exact reproducibility.
- **Model Registry & Tracking:** **MLflow** stores hyperparameter iterations, caches serialized artifacts `.pkl`, and promotes champions to the `Production` stage.
- **Automated CI/CD:** **GitHub Actions** detect data/code changes, retrain the model if DVC tracks a difference, run backend pytests, and build the Docker image.
- **Telemetry & Monitoring:** A custom monitoring layer tracks inference latency, payload size, and system error rates.

---

## 3. Tech Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Generative AI:** Ollama (Llama 3), LangChain, LangGraph
- **Machine Learning:** Scikit-Learn, XGBoost, Sentence-Transformers (all-MiniLM)
- **MLOps:** MLflow, DVC (Data Version Control)
- **DevOps:** Docker, GitHub Actions, Bash

---

## 4. Folder Structure

```text
.
├── backend/            # FastAPI application, routers, and LangGraph orchestrators
│   ├── api.py          # Main FastAPI entrypoint
│   └── mlops_routes.py # Inference router for the XGBoost ML model
├── mlops/              # MLOps pipeline components
│   ├── data/           # Raw and versioned datasets (DVC tracked)
│   ├── train.py        # ML training script with MLflow logging
│   └── monitor.py      # CLI dashboard script for telemetry viewing
├── models/             # Directory for pickled artifacts and Ollama files
├── logs/               # Application telemetry, prediction metrics, and error logs
├── outputs/            # Generated IEEE papers (.tex / .pdf)
├── .github/workflows/  # CI/CD action definitions (mlops-pipeline.yml)
├── dvc.yaml            # DVC pipeline DAG (Data tracking logic)
├── Dockerfile          # Multi-stage production container build
└── requirements.txt    # Python dependencies
```

---

## 5. Local Setup Instructions

1. **Install Dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run Ollama (Background)**
   ```bash
   # Ensure Ollama is installed (https://ollama.com)
   ollama serve &
   ollama pull llama3
   ```

3. **Train the ML Model & Version Data**
   ```bash
   dvc init
   dvc add mlops/data/sections_v1.csv
   dvc repro  # Triggers train.py if data or code has changed
   ```

4. **Start MLflow UI**
   ```bash
   mlflow ui --backend-store-uri sqlite:///mlflow.db
   # Access at http://localhost:5000
   ```

5. **Run the FastAPI Backend**
   ```bash
   python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "outputs/*" --reload-exclude "logs/*"
   ```

---

## 6. API Endpoints

### Generate Paper (LLM)
`POST /api/langgraph/generate`
- **Description:** Triggers the multi-agent system to fetch research and draft IEEE LaTeX code using Ollama.

### Evaluate Section (MLOps)
`POST /api/mlops/evaluate-section`
- **Description:** Evaluates the quality of a given text block.
- **Request:**
  ```json
  {
    "text": "The proposed architecture utilizes quantization...",
    "section_type": "Methodology"
  }
  ```
- **Response:**
  ```json
  {
    "score": 0.902,
    "category": "Excellent",
    "latency_ms": 45.12
  }
  ```

---

## 7. Running with Docker

To deploy the entire system (Backend + ML Model packaged internally):

```bash
# Build the production image
docker build -t ieee-paper-generator:latest .

# Run the container (Ensure Ollama is accessible at host boundary if running externally)
docker run -p 8000:8000 ieee-paper-generator:latest
```

---

## 8. CI/CD Pipeline

The `.github/workflows/mlops-pipeline.yml` automates the release cycle. On a push to `main`:
1. **Runner Checkout & Setup**: Installs Python and dependencies.
2. **DVC Pipeline Execution**: Runs `dvc repro`. If the dataset hash has changed, the XGBoost model is retrained automatically.
3. **Testing**: Spins up a ephemeral Uvicorn instance and actively CURLs the `/api/mlops/evaluate-section` health-check endpoints.
4. **Artifact Archival**: Uploads the serialized `.pkl` models to GitHub Artifacts.
5. **Docker Build**: Validates that the production `Dockerfile` successfully packages the application.

---

## 9. Monitoring & Logging

Every inference request sent to the ML model is intercepted and logged into `logs/mlops_metrics.jsonl`.
To view real-time system health, error rates, and API telemetry:

```bash
python mlops/monitor.py
```

*Example Output:*
```text
========================================
      MLOPS MONITORING DASHBOARD        
========================================
Total API Requests Evaluated : 142
Average Inference Latency    : 38.40 ms
Total Errors Registered      : 0
Current System Error Rate    : 0.00 %
========================================
```

---

## 10. MLOps Workflow lifecycle

1. **Ingest / Data Change:** Data Scientists append human-graded text examples to `sections_v1.csv`.
2. **Version:** `dvc add` registers the delta.
3. **Train & Track:** `dvc repro` calculates embeddings (Sentence-Transformers) and trains `XGBRegressor`, logging metrics to **MLflow**.
4. **Registry:** MLflow promotes the model to `Production`.
5. **Serving:** FastAPI dynamically boots the latest pickled `Production` model into RAM.
6. **Monitor:** Usage and latencies emit to monitoring logs for future data-drift checks.

---

## 11. Demo Flow (For Evaluators)

1. **Explain the Codebase**: Point out `mlops/train.py` (modeling), `backend/mlops_routes.py` (serving), and `dvc.yaml` (pipeline).
2. **Show the MLflow UI**: Open `http://localhost:5000` to show the tracked model parameters (e.g., `learning_rate`=0.1) and metrics (`mae`, `rmse`). Show the internal Model Registry marking the model as `Production`.
3. **Trigger Inference**: In the terminal, send a quick `curl` to `/api/mlops/evaluate-section`.
4. **View Telemetry**: Run `python mlops/monitor.py` to prove the API request was actively logged and analyzed.
5. **Demonstrate Automation**: Open the project's GitHub Actions tab and show the green checkmarks validating the `dvc repro` step and `Docker build`.

---

## 12. Future Improvements

- **Data Drift Detection:** Incorporate EvidentlyAI to detect statistical shifts in prompt structure distributions compared to the training baseline.
- **Advanced Dashboarding:** Move from the CLI monitor to Grafana + Prometheus to visualize time-series inference latencies dynamically.
- **Automated Active Learning:** Pipeline rejected human-corrections from the UI back into the `sections_v1.csv` automatically for nightly DVC retraining.
