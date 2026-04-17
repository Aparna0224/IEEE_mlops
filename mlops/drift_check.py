"""
drift_check.py — Automated Drift Detection for IEEE Paper Generator MLOps Pipeline

Reads inference logs (logs/mlops_metrics.jsonl) and computes rolling statistics
to detect model/data drift. Outputs logs/drift_report.json with a retrain decision.

Exit codes:
  0 — No drift detected, no retraining needed
  1 — Drift detected, retraining should be triggered

Used by GitHub Actions scheduled job to conditionally trigger auto-retraining.
"""

import json
import os
import statistics
import sys
import time
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

METRICS_FILE   = "logs/mlops_metrics.jsonl"
ERROR_FILE     = "logs/mlops_errors.log"
DRIFT_REPORT   = "logs/drift_report.json"

# Thresholds
SCORE_DRIFT_THRESHOLD    = 0.40   # avg predicted score below this → drift
LATENCY_DRIFT_MS         = 2000.0 # avg latency above this (ms) → drift
ERROR_RATE_THRESHOLD     = 15.0   # error rate % above this → drift
SCORE_VARIANCE_THRESHOLD = 0.005  # variance below this (model collapse) → drift
MIN_SAMPLES_REQUIRED     = 5      # need at least this many predictions to evaluate
ROLLING_WINDOW           = 50     # evaluate last N predictions only


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_recent_metrics(filepath: str, window: int) -> list[dict]:
    """Load the last `window` entries from a JSONL metrics file."""
    records = []
    if not os.path.exists(filepath):
        return records
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records[-window:]  # rolling window


def count_errors(filepath: str) -> int:
    """Count non-empty lines in the error log."""
    if not os.path.exists(filepath):
        return 0
    with open(filepath, "r", encoding="utf-8") as f:
        return sum(1 for ln in f if ln.strip())


def load_previous_report() -> dict:
    """Load any existing drift report so we can compare."""
    if not os.path.exists(DRIFT_REPORT):
        return {}
    try:
        with open(DRIFT_REPORT, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_report(report: dict) -> None:
    os.makedirs(os.path.dirname(DRIFT_REPORT), exist_ok=True)
    with open(DRIFT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[DRIFT] Report written → {DRIFT_REPORT}")


# ─── Drift Checks ─────────────────────────────────────────────────────────────

def check_score_drift(scores: list[float]) -> tuple[bool, str]:
    """Flag if average predicted score is abnormally low."""
    if not scores:
        return False, "no_data"
    avg = statistics.mean(scores)
    print(f"[DRIFT] Score check: avg={avg:.4f} threshold={SCORE_DRIFT_THRESHOLD}")
    if avg < SCORE_DRIFT_THRESHOLD:
        return True, f"avg_score={avg:.4f} < threshold={SCORE_DRIFT_THRESHOLD}"
    return False, f"avg_score={avg:.4f} (ok)"


def check_model_collapse(scores: list[float]) -> tuple[bool, str]:
    """Flag if model predicts nearly identical scores for every input."""
    if len(scores) < MIN_SAMPLES_REQUIRED:
        return False, "insufficient_data"
    var = statistics.variance(scores) if len(scores) > 1 else 0.0
    print(f"[DRIFT] Collapse check: variance={var:.6f} threshold={SCORE_VARIANCE_THRESHOLD}")
    if var < SCORE_VARIANCE_THRESHOLD:
        return True, f"score_variance={var:.6f} < threshold={SCORE_VARIANCE_THRESHOLD} (model collapse)"
    return False, f"variance={var:.6f} (ok)"


def check_latency_drift(latencies: list[float]) -> tuple[bool, str]:
    """Flag if average inference latency is dangerously high."""
    if not latencies:
        return False, "no_data"
    avg = statistics.mean(latencies)
    print(f"[DRIFT] Latency check: avg={avg:.2f}ms threshold={LATENCY_DRIFT_MS}ms")
    if avg > LATENCY_DRIFT_MS:
        return True, f"avg_latency={avg:.2f}ms > threshold={LATENCY_DRIFT_MS}ms"
    return False, f"avg_latency={avg:.2f}ms (ok)"


def check_error_rate(error_count: int, total: int) -> tuple[bool, str]:
    """Flag if error rate exceeds acceptable limit."""
    if total == 0:
        return False, "no_traffic"
    rate = (error_count / total) * 100
    print(f"[DRIFT] Error rate check: {rate:.2f}% threshold={ERROR_RATE_THRESHOLD}%")
    if rate > ERROR_RATE_THRESHOLD:
        return True, f"error_rate={rate:.2f}% > threshold={ERROR_RATE_THRESHOLD}%"
    return False, f"error_rate={rate:.2f}% (ok)"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 55)
    print("   IEEE MLOps — Automated Drift Detection")
    print("=" * 55)
    print(f"[DRIFT] Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f"[DRIFT] Rolling window: last {ROLLING_WINDOW} predictions\n")

    # ── Load data ────────────────────────────────────────────────────────────
    records    = load_recent_metrics(METRICS_FILE, ROLLING_WINDOW)
    err_count  = count_errors(ERROR_FILE)
    total_reqs = len(records) + err_count

    scores    = [r["predicted_score"] for r in records if "predicted_score" in r]
    latencies = [r["latency_ms"]      for r in records if "latency_ms"      in r]

    print(f"[DRIFT] Loaded {len(records)} metric records  |  {err_count} errors")

    if len(records) < MIN_SAMPLES_REQUIRED:
        print(f"\n[DRIFT] ⚠️  Insufficient data ({len(records)} < {MIN_SAMPLES_REQUIRED} required).")
        print("[DRIFT] Skipping drift evaluation — not enough traffic yet.")
        report = {
            "evaluated_at": datetime.utcnow().isoformat() + "Z",
            "retrain_needed": False,
            "reason": "insufficient_data",
            "details": {
                "sample_count": len(records),
                "min_required": MIN_SAMPLES_REQUIRED,
            },
        }
        write_report(report)
        return 0

    # ── Run all drift checks ─────────────────────────────────────────────────
    checks = []

    drift_score,    reason_score    = check_score_drift(scores)
    drift_collapse, reason_collapse = check_model_collapse(scores)
    drift_latency,  reason_latency  = check_latency_drift(latencies)
    drift_errors,   reason_errors   = check_error_rate(err_count, total_reqs)

    checks = [
        ("score_drift",    drift_score,    reason_score),
        ("model_collapse", drift_collapse, reason_collapse),
        ("latency_drift",  drift_latency,  reason_latency),
        ("error_rate",     drift_errors,   reason_errors),
    ]

    triggered = [(name, reason) for name, triggered, reason in checks if triggered]
    retrain_needed = len(triggered) > 0

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "─" * 55)
    print(f"  DRIFT SUMMARY  |  {len(triggered)} issue(s) detected")
    print("─" * 55)
    for name, _, reason in checks:
        status = "🔴 DRIFT" if any(n == name for n, _ in triggered) else "✅  OK  "
        print(f"  {status}  {name:<18} {reason}")

    if retrain_needed:
        print("\n[DRIFT] 🚨 DRIFT DETECTED — retraining will be triggered.")
        for name, reason in triggered:
            print(f"         └─ {name}: {reason}")
    else:
        print("\n[DRIFT] ✅  No drift detected — model performance is stable.")

    print("─" * 55 + "\n")

    # ── Write report ─────────────────────────────────────────────────────────
    report = {
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "retrain_needed": retrain_needed,
        "reason": [r for _, r in triggered] if triggered else ["no_drift"],
        "triggered_checks": [n for n, _ in triggered],
        "stats": {
            "sample_count":      len(records),
            "error_count":       err_count,
            "total_requests":    total_reqs,
            "avg_predicted_score": round(statistics.mean(scores), 4)  if scores    else None,
            "score_variance":      round(statistics.variance(scores), 6) if len(scores)>1 else None,
            "avg_latency_ms":      round(statistics.mean(latencies), 2) if latencies else None,
            "error_rate_pct":      round((err_count / total_reqs) * 100, 2) if total_reqs else 0.0,
        },
        "thresholds": {
            "score_drift_threshold":    SCORE_DRIFT_THRESHOLD,
            "latency_drift_ms":         LATENCY_DRIFT_MS,
            "error_rate_threshold_pct": ERROR_RATE_THRESHOLD,
            "score_variance_threshold": SCORE_VARIANCE_THRESHOLD,
        },
        "check_results": {
            name: {"drifted": drifted, "detail": reason}
            for name, drifted, reason in checks
        },
    }
    write_report(report)

    # Exit code drives GitHub Actions conditional
    return 1 if retrain_needed else 0


if __name__ == "__main__":
    sys.exit(main())
