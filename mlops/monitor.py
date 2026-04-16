import json
import os
import statistics

def display_dashboard():
    metrics_file = "logs/mlops_metrics.jsonl"
    error_file = "logs/mlops_errors.log"
    
    print("========================================")
    print("      MLOPS MONITORING DASHBOARD        ")
    print("========================================")
    print("--- System Performance ---")
    
    req_count = 0
    total_latency = 0.0
    scores = []
    
    if os.path.exists(metrics_file):
        with open(metrics_file, "r") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    req_count += 1
                    total_latency += data.get("latency_ms", 0.0)
                    
                    if "predicted_score" in data:
                        scores.append(data["predicted_score"])
                except Exception:
                    pass
                    
    avg_latency = (total_latency / req_count) if req_count > 0 else 0.0
    
    err_count = 0
    if os.path.exists(error_file):
        with open(error_file, "r") as f:
            err_count = sum(1 for line in f if line.strip())
            
    total_requests = req_count + err_count
    error_rate = (err_count / total_requests * 100) if total_requests > 0 else 0.0
    
    print(f"Total API Requests Evaluated : {req_count}")
    print(f"Average Inference Latency    : {avg_latency:.2f} ms")
    print(f"Total Errors Registered      : {err_count}")
    print(f"Current System Error Rate    : {error_rate:.2f} %")
    
    print("\n--- Model Performance (Drift Detection) ---")
    if len(scores) > 0:
        avg_score = statistics.mean(scores)
        max_score = max(scores)
        min_score = min(scores)
        print(f"Total Predictions Tracked    : {len(scores)}")
        print(f"Average Predicted Score      : {avg_score:.2f}")
        print(f"Score Range (Min, Max)       : ({min_score:.2f}, {max_score:.2f})")
        
        # Simple drift detection
        if avg_score < 0.40:
            print("\n[WARNING] DATA DRIFT DETECTED: Average predicted score is abnormally low.")
            print("Model degradation or unusual inputs suspected. Retraining recommended.")
        elif len(set(scores)) == 1 and len(scores) > 5:
            print("\n[WARNING] MODEL COLLAPSE DETECTED: Model is predicting the exact same score for all recent inputs.")
        else:
            print("\n[STATUS] Model Performance is Stable. No drift detected.")
    else:
        print("No prediction scores found in logs. Await inference traffic.")
        
    print("========================================")

if __name__ == "__main__":
    display_dashboard()
