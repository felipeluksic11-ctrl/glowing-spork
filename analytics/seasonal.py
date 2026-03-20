#!/usr/bin/env python3
"""
Seasonal Decomposition — Extract monthly seasonal factors from AirDNA time series
Writes multiplicative seasonal indices per market/submarket/metric to seasonal_indices table
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
    from statsmodels.tsa.seasonal import seasonal_decompose
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pandas", "numpy", "statsmodels"], check=True)
    import numpy as np
    import pandas as pd
    from statsmodels.tsa.seasonal import seasonal_decompose

sys.path.insert(0, str(Path(__file__).parent.parent))
from analista_rentas import supabase_fetch, supabase_upsert, SUPABASE_URL, SUPABASE_KEY

MIN_MONTHS = 12  # Need at least 12 months for seasonal decomposition


def fetch_monthly_series(market: str, submarket: str | None, section: str, chart: str, metric_name: str) -> pd.Series:
    """Fetch monthly time series as a pandas Series with DatetimeIndex."""
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
        return pd.Series(dtype=float)

    df = pd.DataFrame(rows)
    df["metric_date"] = pd.to_datetime(df["metric_date"])
    df = df.dropna(subset=["metric_value"]).drop_duplicates("metric_date").sort_values("metric_date")
    df = df.set_index("metric_date")
    df.index.freq = "MS"

    return df["metric_value"].astype(float)


def decompose_seasonal(series: pd.Series) -> dict[int, float] | None:
    """Decompose series and return monthly seasonal factors (1-12)."""
    if len(series) < MIN_MONTHS:
        return None

    try:
        # Use multiplicative model — seasonal factors as multipliers
        result = seasonal_decompose(series, model="multiplicative", period=12, extrapolate_trend="freq")
        seasonal = result.seasonal

        # Average seasonal factor per month across all years
        monthly = {}
        for month in range(1, 13):
            vals = seasonal[seasonal.index.month == month]
            if len(vals) > 0:
                monthly[month] = round(float(vals.mean()), 4)
            else:
                monthly[month] = 1.0

        return monthly
    except Exception as e:
        print(f"    Decomposition failed: {e}")
        return None


def compute_seasonal_indices(market: str, submarkets: list[str | None]) -> list[dict]:
    """Compute seasonal indices for all metric/submarket combinations."""
    all_indices = []

    targets = [
        ("occupancy", "chart_1", "occupancy"),
        ("rates", "chart_1", "daily_rate"),
    ]

    for submarket in submarkets:
        sub_label = submarket or "market-level"
        for section, chart, metric_name in targets:
            series = fetch_monthly_series(market, submarket, section, chart, metric_name)
            if series.empty or len(series) < MIN_MONTHS:
                continue

            print(f"    Decomposing {metric_name} for {sub_label} ({len(series)} months)...")
            monthly = decompose_seasonal(series)
            if not monthly:
                continue

            for month, factor in monthly.items():
                all_indices.append({
                    "market": market,
                    "submarket": submarket,
                    "metric_name": metric_name,
                    "month": month,
                    "seasonal_factor": factor,
                })

    return all_indices


def get_submarkets(market: str) -> list[str]:
    """Get list of submarkets for a market."""
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
    print("Propyte Analytics — Seasonal Decomposition")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials not configured")
        sys.exit(1)

    markets = ["cancun", "playa_del_carmen", "tulum", "merida"]
    all_indices = []

    for market in markets:
        print(f"\n[{market.upper()}]")
        submarkets = get_submarkets(market)
        print(f"  Found {len(submarkets)} submarkets")

        indices = compute_seasonal_indices(market, [None] + submarkets)
        all_indices.extend(indices)
        print(f"  Computed {len(indices)} seasonal indices")

    if all_indices:
        print(f"\n[UPSERT] Uploading {len(all_indices)} seasonal indices...")
        ok = supabase_upsert("seasonal_indices", all_indices)
        print(f"  seasonal_indices: {'OK' if ok else 'FAILED'}")
    else:
        print("\nNo seasonal indices computed")

    print("\nDone!")


if __name__ == "__main__":
    main()
