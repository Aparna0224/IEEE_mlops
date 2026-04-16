# End-to-End AI & MLOps Pipeline Report
**Project:** AI-Powered IEEE Research Paper Generator  
**Focus:** Large Language Models (LLM) integrated with an MLOps-driven Evaluation Engine.

---

## 1. Problem Framing and Business Objective
**Problem:** Automatically generating massive research papers using LLMs often results in hallucinations, structural degradation, and poor formatting. 
**Solution:** We built an end-to-end AI platform that uses local and cloud LLMs to generate papers, coupled with an automated Machine Learning (ML) Ops pipeline. The ML model evaluates the generated sections for quality, clarity, and structural compliance before final PDF generation.

---

## 2. System Architecture & Design
The system is divided into two major AI subsystems orchestrated by a FastAPI backend:

1. **Generative Pipeline (LangGraph):** Extracts research via tools (arXiv), plans the paper structure, and delegates writing to models (Llama-3 locally / Llama-3.3-70b via Groq fallback).
2. **Evaluative Pipeline (MLOps):** Uses semantic embeddings (`sentence-transformers/all-MiniLM-L6-v2`) and traditional NLP features (readability, token counts) fed into an **XGBoost Regressor** to predict the quality score of the generated text.

*Tech Stack:* FastAPI, Next.js, XGBoost, MLflow, Docker, DVC, GitHub Actions, LaTeX.

---

## 3. Data Pipeline & Versioning
- **Data Ingestion:** Sections of IEEE-style text are collected and stored in `mlops/data/sections_v1.csv`.
- **Data Augmentation:** A synthetic augmentation script (`mlops/augment_data.py`) expands the dataset to enable robust model training.
- **Data Versioning:** Handled via **DVC** (`dvc.yaml`). Data changes automatically trigger pipeline recalculations.
- **Preprocessing:** Text lowering, whitespace stripping, and readability score extraction.

---

## 4. Model Training and Experiment Tracking
The ML training script (`mlops/train.py`) executes an automated pipeline:
- **Feature Extraction:** Concatenates dense embeddings (MiniLM) with readability structures.
- **Hyperparameter Tuning:** Utilizes `sklearn.model_selection.GridSearchCV` to automatically find the optimal `max_depth`, `learning_rate`, and `n_estimators` for the XGBoost model.
- **Experiment Tracking:** Integrated directly with **MLflow**. Every run logs hyperparameter metrics (MAE, RMSE, R2) and registers the best model artifact.

---

## 5. Model Packaging and Deployment
- **API Serving:** The trained pickle file (`models/section_quality_xgboost.pkl`) is loaded into FastAPI. The endpoint `/api/mlops/evaluate-section` serves live predictions.
- **Containerization:** The entire backend (including the Heavy LaTeX engine and Ollama binaries) is packaged within a single, optimized `Dockerfile`.
- **Cloud Deployment Sequence:** The Docker image is standardized for immediate deployment on Azure App Service, AWS EC2, or a dedicated compute VM.

---

## 6. CI/CD and Automation (GitHub Actions)
The workflow (`.github/workflows/mlops-pipeline.yml`) defines a robust CI/CD cycle triggered on pushes to the `main` branch.
1. **Disk Space Optimization:** Utilizes `jlumbroso/free-disk-space` to maximize GitHub runner efficiency for heavy ML dependencies.
2. **Automated ML Training:** Executes `dvc repro` to build the model if data has changed.
3. **Artifact Archiving:** Saves the compiled `.pkl` model for deployment.
4. **Integration Testing:** Bootstraps the FastAPI server temporarily via `uvicorn` and validates the ML endpoint using `curl`.
5. **Continuous Deployment (Docker):** Builds the main Docker image and automatically pushes the tagged container to the **GitHub Container Registry (GHCR)**.

---

## 7. Monitoring, Logging & Drift Detection
As inference requests flow into `/api/mlops/evaluate-section`, they are logged to `logs/mlops_metrics.jsonl`. 
The `mlops/monitor.py` dashboard acts as a continuous watchdog tracking:
- **System Metrics:** Inference Latency (ms), Total Requests, Error Rate.
- **Model Performance & Drift:** Tracks the moving average of predicted scores. If the expected score distribution drastically deviates (e.g., collapses below 0.40 consistently), it fires a **Data Drift Warning**, triggering a recommendation for retraining.

---

## Final Review / Viva Preparedness
- **Why use ML to evaluate an LLM?** Because LLM-as-a-judge is slow and expensive. An XGBoost model trained on historical evaluations is ultra-fast (sub 50ms latency) and consistent.
- **Is it reproducible?** Yes, the entire architecture from data ingestion to containerized deployment is mathematically seeded and orchestrated via DVC and Docker.
- **What happens if data changes?** DVC detects the change, GitHub Actions catches that on commit, automatically retrains the model, generates a new pickle, updates MLflow, rebuilds the Docker container, and pushes the new container to GHCR—zero human intervention. 
