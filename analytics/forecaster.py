#!/usr/bin/env python3
"""
Time Series Forecaster — AutoARIMA forecasting for occupancy, ADR, RevPAR
Reads from airdna_metrics, writes to metric_forecasts
"""

from __future__ import annotations

import sys
from datetime import date
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

try:
    from statsforecast import StatsForecast
    from statsforecast.models import AutoARIMA, AutoETS
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "statsforecast"], check=True)
    from statsforecast import StatsForecast
    from statsforecast.models import AutoARIMA, AutoETS

sys.path.insert(0, str(Path(__file__).parent.parent))
from analista_rentas import supabase_fetch, supabase_upsert, SUPABASE_URL, SUPABASE_KEY

FORECAST_HORIZON = 6  # months ahead
CONFIDENCE_LEVEL = 90
MIN_OBSERVATIONS = 8  # minimum data points to attempt forecasting


def fetch_time_series(market: str, submarket: str | None, section: str, chart: str, metric_name: str) -> pd.DataFrame:
    """Fetch historical time series from airdna_metrics."""
    filters = (
        f"market=eq.{market}&section=eq.{section}&chart=eq.{chart}"
        f"&metric_name=eq.{metric_name}&order=metric_date.asc"
    )
    if submarket:
        filters += f"&submarket=eq.{submarket}"
    else:
        filters += "&submarket=is.null"

    rows = supabase_fetch("airdna_metrics", select="metric_date,metric_value", filters=filters)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["metric_date"] = pd.to_datetime(df["metric_date"])
    df = df.dropna(subset=["metric_value"])
    df = df.drop_duplicates("metric_date").sort_values("metric_date")
    return df


def forecast_series(
    df: pd.DataFrame,
    market: str,
    submarket: str | None,
    metric_name: str,
) -> list[dict]:
    """Run AutoARIMA forecast on a time series. Returns forecast rows."""
    if len(df) < MIN_OBSERVATIONS:
        return []

    # Prepare for statsforecast: needs columns unique_id, ds, y
    ts_df = pd.DataFrame({
        "unique_id": f"{market}_{submarket or 'market'}_{metric_name}",
        "ds": df["metric_date"],
        "y": df["metric_value"].astype(float),
    })

    # Choose model based on data length
    if len(ts_df) >= 12:
        models = [AutoARIMA(season_length=12)]
        model_type = "AutoARIMA"
    else:
        models = [AutoETS(season_length=1)]
        model_type = "AutoETS"

    try:
        sf = StatsForecast(models=models, freq="MS", n_jobs=1)
        forecast = sf.forecast(df=ts_df, h=FORECAST_HORIZON, level=[CONFIDENCE_LEVEL])
    except Exception as e:
        print(f"    Forecast failed for {market}/{submarket}/{metric_name}: {e}")
        return []

    # Parse forecast results
    results = []
    forecast_df = forecast.reset_index()

    # Find columns: model prediction, lo, hi
    # Columns are like: unique_id, ds, AutoARIMA, AutoARIMA-lo-90, AutoARIMA-hi-90
    non_meta = [c for c in forecast_df.columns if c not in ("unique_id", "ds")]
    col_pred = [c for c in non_meta if "lo" not in c.lower() and "hi" not in c.lower()]
    col_lo = [c for c in non_meta if "lo" in c.lower()]
    col_hi = [c for c in non_meta if "hi" in c.lower()]

    pred_col = col_pred[0] if col_pred else non_meta[0]

    for _, row in forecast_df.iterrows():
        ds = row["ds"]
        date_str = ds.strftime("%Y-%m-%d") if hasattr(ds, "strftime") else str(ds)[:10]
        results.append({
            "market": market,
            "submarket": submarket,
            "metric_name": metric_name,
            "forecast_date": date_str,
            "predicted_value": round(float(row[pred_col]), 2),
            "ci_lower": round(float(row[col_lo[0]]), 2) if col_lo else None,
            "ci_upper": round(float(row[col_hi[0]]), 2) if col_hi else None,
            "model_type": model_type,
        })

    return results


def run_forecasts(market: str, submarkets: list[str | None]) -> list[dict]:
    """Run forecasts for all metric/submarket combinations."""
    all_forecasts = []

    # Metrics to forecast
    targets = [
        ("occupancy", "chart_1", "occupancy"),
        ("rates", "chart_1", "daily_rate"),
    ]

    for submarket in submarkets:
        sub_label = submarket or "market-level"
        for section, chart, metric_name in targets:
            df = fetch_time_series(market, submarket, section, chart, metric_name)
            if df.empty:
                continue

            print(f"    Forecasting {metric_name} for {sub_label} ({len(df)} points)...")
            forecasts = forecast_series(df, market, submarket, metric_name)
            all_forecasts.extend(forecasts)

            # Also compute RevPAR forecast if we have both occupancy and ADR
            if metric_name == "occupancy":
                adr_df = fetch_time_series(market, submarket, "rates", "chart_1", "daily_rate")
                if not adr_df.empty and len(df) >= MIN_OBSERVATIONS and len(adr_df) >= MIN_OBSERVATIONS:
                    # Merge on date and compute RevPAR
                    merged = df.merge(adr_df, on="metric_date", suffixes=("_occ", "_adr"))
                    if len(merged) >= MIN_OBSERVATIONS:
                        merged["metric_value"] = merged["metric_value_occ"] / 100 * merged["metric_value_adr"]
                        revpar_forecasts = forecast_series(merged[["metric_date", "metric_value"]], market, submarket, "revpar")
                        all_forecasts.extend(revpar_forecasts)

    return all_forecasts


def get_submarkets(market: str) -> list[str]:
    """Get list of submarkets for a market from airdna_metrics."""
    rows = supabase_fetch(
        "airdna_metrics",
        select="submarket",
        filters=f"market=eq.{market}&submarket=not.is.null&limit=1000",
    )
    if not rows:
        return []
    return list({r["submarket"] for r in rows if r.get("submarket")})


def main():
    print("=" * 60)
    print("Propyte Analytics — Time Series Forecaster")
    print(f"Date: {date.today().isoformat()}")
    print(f"Horizon: {FORECAST_HORIZON} months | CI: {CONFIDENCE_LEVEL}%")
    print("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials not configured")
        sys.exit(1)

    markets = ["cancun", "playa_del_carmen", "tulum", "merida"]
    all_forecasts = []

    for market in markets:
        print(f"\n[{market.upper()}]")
        submarkets = get_submarkets(market)
        print(f"  Found {len(submarkets)} submarkets")

        # Forecast market-level + each submarket
        forecasts = run_forecasts(market, [None] + submarkets)
        all_forecasts.extend(forecasts)
        print(f"  Generated {len(forecasts)} forecast points")

    if all_forecasts:
        print(f"\n[UPSERT] Uploading {len(all_forecasts)} forecasts...")
        ok = supabase_upsert("metric_forecasts", all_forecasts)
        print(f"  metric_forecasts: {'OK' if ok else 'FAILED'}")
    else:
        print("\nNo forecasts generated")

    print("\nDone!")


if __name__ == "__main__":
    main()
