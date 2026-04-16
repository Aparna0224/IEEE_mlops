import os
import pandas as pd
import numpy as np
import mlflow
import joblib
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sentence_transformers import SentenceTransformer
import xgboost as xgb

# 1. Feature Engineering & Preprocessing
def preprocess_text(text):
    return str(text).lower().strip()

def compute_readability(text):
    return len(text.split()) / max(text.count('.') + 1, 1)

def extract_features(df, embedding_model):
    print("Extracting features using sentence-transformers...")
    
    # Simple NLP features
    df['word_count'] = df['text'].apply(lambda x: len(str(x).split()))
    df['readability'] = df['text'].apply(lambda x: compute_readability(str(x)))
    
    # Dense embeddings
    embeddings = embedding_model.encode(df['text'].tolist())
    
    # Combine engineered features with embeddings
    advanced_features = df[['word_count', 'readability']].values
    X = np.hstack([advanced_features, embeddings])
    y = df['score'].values
    
    return X, y

def main():
    # Setup MLflow Tracking
    os.makedirs("models", exist_ok=True)
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("IEEE_Section_Quality_Predictor")
    
    # Load dataset (Version controlled implicitly by filename or via DVC)
    data_path = "mlops/data/sections_v1.csv"
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    # Load lightweight embedding model
    print("Loading SentenceTransformer (all-MiniLM-L6-v2)...")
    emb_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    X, y = extract_features(df, emb_model)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Log experiment parameters and metrics
    with mlflow.start_run():
        print("Starting Hyperparameter Tuning with GridSearchCV...")
        
        param_grid = {
            'n_estimators': [50, 100],
            'max_depth': [3, 5],
            'learning_rate': [0.05, 0.1]
        }
        
        base_model = xgb.XGBRegressor(random_state=42)
        grid_search = GridSearchCV(
            estimator=base_model,
            param_grid=param_grid,
            scoring='neg_mean_squared_error',
            cv=3,
            verbose=1
        )
        
        grid_search.fit(X_train, y_train)
        
        best_model = grid_search.best_estimator_
        best_params = grid_search.best_params_
        best_params["embedding_model"] = "all-MiniLM-L6-v2"
        
        mlflow.log_params(best_params)
        print(f"Best params found: {best_params}")
        
        # Predictions
        y_pred = best_model.predict(X_test)
        
        # Evaluation
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        print(f"Results -> MAE: {mae:.4f} | RMSE: {rmse:.4f} | R2: {r2:.4f}")
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("r2", r2)
        
        # Save local model artifacts for FastAPI inference
        model_path = "models/section_quality_xgboost.pkl"
        joblib.dump(best_model, model_path)
        print(f"Model saved to {model_path}")
        
        # Log model specifically to MLFlow
        mlflow.sklearn.log_model(best_model, "xgboost-model")
        
        # Register Model to MLflow Registry
        run_id = mlflow.active_run().info.run_id
        model_uri = f"runs:/{run_id}/xgboost-model"
        print(f"Registering model in MLflow Registry (Run ID: {run_id})...")
        mv = mlflow.register_model(model_uri, "IEEE_Section_Quality_XGBoost")
        
        # Transition model to Production stage
        from mlflow.tracking import MlflowClient
        client = MlflowClient()
        client.transition_model_version_stage(
            name="IEEE_Section_Quality_XGBoost",
            version=mv.version,
            stage="Production"
        )
        print(f"Model version {mv.version} successfully transitioned to Production stage.")
        
if __name__ == "__main__":
    main()
