#!/usr/bin/env python3
"""
Data Quality Monitor — Automated checks for data freshness, completeness, and consistency
Writes results to data_quality_checks and market_alerts tables
"""

from __future__ import annotations

import json
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

# Thresholds
MAX_DAYS_STALE_RENTALS = 10
MAX_DAYS_STALE_AIRDNA = 20
MIN_COMPARABLES_PER_ZONE = 10
MAX_NULL_RATE = 0.20  # 20%
PRICE_IQR_MULTIPLIER = 3


def check_rental_freshness() -> dict:
    """Check if rental data is fresh."""
    rows = supabase_fetch(
        "rental_comparables",
        select="scraped_at",
        filters="order=scraped_at.desc&limit=1",
    )
    if not rows:
        return {"check_name": "rental_freshness", "status": "fail",
                "details": {"message": "No rental data found", "days_stale": None}}

    latest = rows[0].get("scraped_at", "")
    if not latest:
        return {"check_name": "rental_freshness", "status": "fail",
                "details": {"message": "No scraped_at date", "days_stale": None}}

    days_stale = (date.today() - date.fromisoformat(latest[:10])).days
    status = "pass" if days_stale <= MAX_DAYS_STALE_RENTALS else "warn" if days_stale <= MAX_DAYS_STALE_RENTALS * 2 else "fail"

    return {
        "check_name": "rental_freshness",
        "status": status,
        "details": {"latest_scrape": latest[:10], "days_stale": days_stale, "threshold": MAX_DAYS_STALE_RENTALS},
    }


def check_airdna_freshness() -> dict:
    """Check if AirDNA data is fresh."""
    rows = supabase_fetch(
        "airdna_metrics",
        select="scraped_at",
        filters="order=scraped_at.desc&limit=1",
    )
    if not rows:
        return {"check_name": "airdna_freshness", "status": "fail",
                "details": {"message": "No AirDNA data found"}}

    latest = rows[0].get("scraped_at", "")
    days_stale = (date.today() - date.fromisoformat(latest[:10])).days if latest else 999
    status = "pass" if days_stale <= MAX_DAYS_STALE_AIRDNA else "warn" if days_stale <= MAX_DAYS_STALE_AIRDNA * 2 else "fail"

    return {
        "check_name": "airdna_freshness",
        "status": status,
        "details": {"latest_scrape": latest[:10] if latest else None, "days_stale": days_stale, "threshold": MAX_DAYS_STALE_AIRDNA},
    }


def check_zone_coverage() -> dict:
    """Check if all major zones have sufficient comparables."""
    rows = supabase_fetch(
        "rental_comparables",
        select="city,zone",
        filters="active=eq.true",
    )
    if not rows:
        return {"check_name": "zone_coverage", "status": "fail",
                "details": {"message": "No active comparables"}}

    df = pd.DataFrame(rows)
    zone_counts = df.groupby(["city", "zone"]).size().reset_index(name="count")
    low_coverage = zone_counts[zone_counts["count"] < MIN_COMPARABLES_PER_ZONE]

    status = "pass" if low_coverage.empty else "warn"
    details = {
        "total_zones": len(zone_counts),
        "zones_below_threshold": len(low_coverage),
        "threshold": MIN_COMPARABLES_PER_ZONE,
    }
    if not low_coverage.empty:
        details["low_zones"] = [
            {"city": r["city"], "zone": r["zone"], "count": int(r["count"])}
            for _, r in low_coverage.head(10).iterrows()
        ]

    return {"check_name": "zone_coverage", "status": status, "details": details}


def check_price_outliers() -> dict:
    """Check for extreme price outliers in rental data."""
    rows = supabase_fetch(
        "rental_comparables",
        select="city,zone,monthly_rent_mxn",
        filters="active=eq.true&monthly_rent_mxn=gte.1000",
    )
    if not rows:
        return {"check_name": "price_outliers", "status": "pass", "details": {"message": "No data"}}

    df = pd.DataFrame(rows)
    total = len(df)
    outlier_count = 0
    outlier_zones = []

    for (city, zone), grp in df.groupby(["city", "zone"]):
        if len(grp) < 10:
            continue
        q1 = grp["monthly_rent_mxn"].quantile(0.25)
        q3 = grp["monthly_rent_mxn"].quantile(0.75)
        iqr = q3 - q1
        outliers = grp[(grp["monthly_rent_mxn"] > q3 + PRICE_IQR_MULTIPLIER * iqr) |
                       (grp["monthly_rent_mxn"] < q1 - PRICE_IQR_MULTIPLIER * iqr)]
        if len(outliers) > 0:
            outlier_count += len(outliers)
            outlier_zones.append({"city": city, "zone": zone, "outliers": len(outliers), "total": len(grp)})

    outlier_rate = outlier_count / total if total > 0 else 0
    status = "pass" if outlier_rate < 0.05 else "warn" if outlier_rate < 0.10 else "fail"

    return {
        "check_name": "price_outliers",
        "status": status,
        "details": {
            "total_listings": total,
            "outlier_count": outlier_count,
            "outlier_rate_pct": round(outlier_rate * 100, 2),
            "top_zones": outlier_zones[:5],
        },
    }


def check_null_rates() -> dict:
    """Check null rates in critical columns."""
    rows = supabase_fetch(
        "rental_comparables",
        select="area_m2,bedrooms,zone,monthly_rent_mxn",
        filters="active=eq.true&limit=5000",
    )
    if not rows:
        return {"check_name": "null_rates", "status": "pass", "details": {"message": "No data"}}

    df = pd.DataFrame(rows)
    null_rates = {}
    for col in ["area_m2", "bedrooms", "zone", "monthly_rent_mxn"]:
        null_rate = df[col].isna().mean() if col in df.columns else 1.0
        null_rates[col] = round(null_rate * 100, 2)

    max_null = max(null_rates.values())
    status = "pass" if max_null <= MAX_NULL_RATE * 100 else "warn"

    return {
        "check_name": "null_rates",
        "status": status,
        "details": {"null_rates_pct": null_rates, "threshold_pct": MAX_NULL_RATE * 100},
    }


def check_model_staleness() -> dict:
    """Check if ML models are up to date."""
    rows = supabase_fetch(
        "model_performance_log",
        select="model_name,training_date",
        filters="order=training_date.desc&limit=10",
    )
    if not rows:
        return {"check_name": "model_staleness", "status": "warn",
                "details": {"message": "No model performance data"}}

    df = pd.DataFrame(rows)
    latest = df.drop_duplicates("model_name", keep="first")

    stale_models = []
    for _, row in latest.iterrows():
        training_date = row.get("training_date")
        if training_date:
            days = (date.today() - date.fromisoformat(training_date)).days
            if days > 14:
                stale_models.append({"model": row["model_name"], "days_since": days})

    status = "pass" if not stale_models else "warn"
    return {
        "check_name": "model_staleness",
        "status": status,
        "details": {"stale_models": stale_models, "models_checked": len(latest)},
    }


def main():
    print("=" * 60)
    print("Propyte Analytics — Data Quality Monitor")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials not configured")
        sys.exit(1)

    checks = [
        check_rental_freshness,
        check_airdna_freshness,
        check_zone_coverage,
        check_price_outliers,
        check_null_rates,
        check_model_staleness,
    ]

    results = []
    for check_fn in checks:
        print(f"\n  Running {check_fn.__name__}...")
        result = check_fn()
        emoji_map = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
        print(f"    [{emoji_map[result['status']]}] {result['check_name']}")
        if result.get("details"):
            for k, v in result["details"].items():
                if not isinstance(v, (list, dict)):
                    print(f"      {k}: {v}")
        results.append(result)

    # Upload results
    if results:
        print(f"\n[UPSERT] Uploading {len(results)} quality check results...")
        ok = supabase_upsert("data_quality_checks", results)
        print(f"  data_quality_checks: {'OK' if ok else 'FAILED'}")

    # Generate alerts for failures
    alerts = []
    for r in results:
        if r["status"] in ("warn", "fail"):
            alerts.append({
                "alert_type": "data_quality",
                "metric_name": r["check_name"],
                "severity": "warning" if r["status"] == "warn" else "critical",
                "message": f"Data quality check '{r['check_name']}' {r['status']}: {json.dumps(r.get('details', {}), default=str)[:200]}",
            })

    if alerts:
        supabase_upsert("market_alerts", alerts)
        print(f"  Generated {len(alerts)} data quality alerts")

    # Summary
    pass_count = sum(1 for r in results if r["status"] == "pass")
    warn_count = sum(1 for r in results if r["status"] == "warn")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    print(f"\n  Summary: {pass_count} pass, {warn_count} warn, {fail_count} fail")

    print("\nDone!")


if __name__ == "__main__":
    main()
