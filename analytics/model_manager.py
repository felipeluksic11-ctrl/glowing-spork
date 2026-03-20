#!/usr/bin/env python3
"""
Model Manager — Retrain triggers, performance tracking, feature importance logging
Decides when models should be retrained based on data freshness and performance drift
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from functools import partial
from pathlib import Path

print = partial(print, flush=True)

try:
    import numpy as np
    import pandas as pd
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pandas", "numpy"], check=True)
    import numpy as np
    import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from analista_rentas import supabase_fetch, supabase_upsert, SUPABASE_URL, SUPABASE_KEY

# Retrain thresholds
MAX_DAYS_SINCE_TRAINING = 14
MAX_MAPE_THRESHOLD = 25.0  # %
MIN_NEW_SAMPLES_TRIGGER = 500


def log_model_performance(
    model_name: str,
    model_version: str,
    r2: float,
    mae: float,
    mape: float,
    sample_size: int,
    feature_importances: dict[str, float] | None = None,
):
    """Log model performance metrics to model_performance_log table."""
    today = date.today().isoformat()

    rows = []
    for metric_name, value in [("r2", r2), ("mae", mae), ("mape", mape)]:
        rows.append({
            "model_name": model_name,
            "model_version": model_version,
            "metric_name": metric_name,
            "metric_value": round(value, 4),
            "sample_size": sample_size,
            "training_date": today,
            "feature_importances": feature_importances,
        })

    ok = supabase_upsert("model_performance_log", rows)
    if ok:
        print(f"  Logged performance for {model_name}: R²={r2:.4f}, MAE={mae:.0f}, MAPE={mape:.1f}%")
    return ok


def get_latest_performance(model_name: str) -> dict | None:
    """Get most recent performance metrics for a model."""
    rows = supabase_fetch(
        "model_performance_log",
        select="metric_name,metric_value,training_date,sample_size",
        filters=f"model_name=eq.{model_name}&order=computed_at.desc&limit=10",
    )
    if not rows:
        return None

    result = {"training_date": rows[0].get("training_date"), "sample_size": rows[0].get("sample_size")}
    for row in rows:
        result[row["metric_name"]] = row["metric_value"]
    return result


def count_new_samples_since(training_date: str) -> int:
    """Count new rental_comparables added since last training."""
    rows = supabase_fetch(
        "rental_comparables",
        select="id",
        filters=f"created_at=gte.{training_date}&active=eq.true&limit=1",
    )
    # Supabase REST doesn't return count easily, use a workaround
    rows_all = supabase_fetch(
        "rental_comparables",
        select="id",
        filters=f"created_at=gte.{training_date}&active=eq.true",
    )
    return len(rows_all)


def should_retrain(model_name: str) -> tuple[bool, str]:
    """Determine if a model should be retrained. Returns (should_retrain, reason)."""
    perf = get_latest_performance(model_name)

    if not perf:
        return True, "No performance history found"

    training_date = perf.get("training_date")
    if not training_date:
        return True, "No training date recorded"

    # Check 1: Days since last training
    days_since = (date.today() - date.fromisoformat(training_date)).days
    if days_since > MAX_DAYS_SINCE_TRAINING:
        return True, f"Last trained {days_since} days ago (threshold: {MAX_DAYS_SINCE_TRAINING})"

    # Check 2: MAPE exceeds threshold
    mape = perf.get("mape")
    if mape and mape > MAX_MAPE_THRESHOLD:
        return True, f"MAPE = {mape:.1f}% exceeds threshold ({MAX_MAPE_THRESHOLD}%)"

    # Check 3: Enough new data
    new_samples = count_new_samples_since(training_date)
    if new_samples >= MIN_NEW_SAMPLES_TRIGGER:
        return True, f"{new_samples} new samples since last training (threshold: {MIN_NEW_SAMPLES_TRIGGER})"

    return False, f"No retrain needed (last: {days_since}d ago, MAPE: {mape or 'N/A'}, new: {new_samples})"


def get_performance_history(model_name: str, metric: str = "mape", limit: int = 20) -> pd.DataFrame:
    """Get historical performance for trend analysis."""
    rows = supabase_fetch(
        "model_performance_log",
        select="metric_value,training_date,sample_size",
        filters=f"model_name=eq.{model_name}&metric_name=eq.{metric}&order=training_date.desc&limit={limit}",
    )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def main():
    print("=" * 60)
    print("Propyte Analytics — Model Manager")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials not configured")
        sys.exit(1)

    models = ["rent_residencial", "rent_vacacional"]
    retrain_needed = []

    for model_name in models:
        should, reason = should_retrain(model_name)
        status = "RETRAIN" if should else "OK"
        print(f"\n  [{status}] {model_name}: {reason}")

        if should:
            retrain_needed.append(model_name)

        # Show performance history
        history = get_performance_history(model_name, "mape")
        if not history.empty:
            print(f"    MAPE history (last {len(history)}): {history['metric_value'].tolist()}")

    if retrain_needed:
        print(f"\n  Models needing retrain: {', '.join(retrain_needed)}")
        print("  Run: python analista_rentas.py")
    else:
        print("\n  All models are up to date")

    print("\nDone!")


if __name__ == "__main__":
    main()
