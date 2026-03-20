#!/usr/bin/env python3
"""
Anomaly Detector — Z-score based detection of unusual market movements
Detects: occupancy drops, ADR spikes, supply shocks, rental price outliers
Writes alerts to market_alerts table
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

sys.path.insert(0, str(Path(__file__).parent.parent))
from analista_rentas import supabase_fetch, supabase_upsert, SUPABASE_URL, SUPABASE_KEY
from analytics.compute_derived import SUBMARKET_TO_ZONE, CITY_TO_MARKET

Z_THRESHOLD = 2.5
ROLLING_WINDOW = 3  # months


def detect_airdna_anomalies(market: str) -> list[dict]:
    """Detect anomalies in AirDNA time series data."""
    alerts = []

    targets = [
        ("occupancy", "chart_1", "occupancy", "Ocupación"),
        ("rates", "chart_1", "daily_rate", "ADR"),
    ]

    for section, chart, metric_name, label in targets:
        # Fetch market-level and submarket-level data
        rows = supabase_fetch(
            "airdna_metrics",
            select="submarket,metric_value,metric_date",
            filters=(
                f"market=eq.{market}&section=eq.{section}&chart=eq.{chart}"
                f"&metric_name=eq.{metric_name}&order=metric_date.asc"
            ),
        )
        if not rows:
            continue

        df = pd.DataFrame(rows)
        df["metric_date"] = pd.to_datetime(df["metric_date"])
        df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")

        # Check per submarket
        groups = df.groupby("submarket", dropna=False)
        for sub, grp in groups:
            grp = grp.sort_values("metric_date").dropna(subset=["metric_value"])
            if len(grp) < ROLLING_WINDOW + 1:
                continue

            series = grp["metric_value"]
            rolling_mean = series.rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean()
            rolling_std = series.rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).std()

            # Check last data point
            last_idx = series.index[-1]
            last_val = series.iloc[-1]
            mean_val = rolling_mean.iloc[-1] if pd.notna(rolling_mean.iloc[-1]) else series.mean()
            std_val = rolling_std.iloc[-1] if pd.notna(rolling_std.iloc[-1]) else series.std()

            if std_val > 0:
                z_score = abs((last_val - mean_val) / std_val)
                if z_score >= Z_THRESHOLD:
                    deviation_pct = round((last_val - mean_val) / mean_val * 100, 1)
                    zone = SUBMARKET_TO_ZONE.get(sub, sub) if sub else "Market"
                    direction = "subió" if last_val > mean_val else "bajó"
                    severity = "critical" if z_score >= 3.5 else "warning"

                    alerts.append({
                        "alert_type": "anomaly",
                        "city": _market_to_city(market),
                        "zone": zone,
                        "market": market,
                        "submarket": sub,
                        "metric_name": metric_name,
                        "current_value": round(float(last_val), 2),
                        "expected_value": round(float(mean_val), 2),
                        "deviation_pct": deviation_pct,
                        "severity": severity,
                        "message": f"{label} en {zone} {direction} {abs(deviation_pct):.1f}% vs promedio reciente (z={z_score:.1f})",
                    })

    return alerts


def detect_rental_outliers(city: str) -> list[dict]:
    """Detect rental price outliers using IQR method per zone."""
    rows = supabase_fetch(
        "rental_comparables",
        select="zone,monthly_rent_mxn,source_portal",
        filters=f"city=eq.{city}&active=eq.true&monthly_rent_mxn=gte.5000",
    )
    if not rows:
        return []

    df = pd.DataFrame(rows)
    alerts = []

    for zone, grp in df.groupby("zone"):
        if len(grp) < 10:
            continue

        q1 = grp["monthly_rent_mxn"].quantile(0.25)
        q3 = grp["monthly_rent_mxn"].quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + 3 * iqr
        lower_bound = q1 - 3 * iqr

        outliers_high = grp[grp["monthly_rent_mxn"] > upper_bound]
        outliers_low = grp[grp["monthly_rent_mxn"] < lower_bound]

        n_outliers = len(outliers_high) + len(outliers_low)
        if n_outliers > 0:
            alerts.append({
                "alert_type": "anomaly",
                "city": city,
                "zone": zone,
                "market": None,
                "submarket": None,
                "metric_name": "rental_price",
                "current_value": float(grp["monthly_rent_mxn"].median()),
                "expected_value": float((q1 + q3) / 2),
                "deviation_pct": round(n_outliers / len(grp) * 100, 1),
                "severity": "info",
                "message": f"{n_outliers} listings con precio atípico en {zone} ({n_outliers/len(grp)*100:.0f}% del total)",
            })

    return alerts


def detect_supply_changes(market: str) -> list[dict]:
    """Detect significant changes in supply (listing count)."""
    rows = supabase_fetch(
        "airdna_metrics",
        select="submarket,metric_name,metric_value,metric_date",
        filters=(
            f"market=eq.{market}&section=eq.listings&chart=eq.chart_1"
            f"&order=metric_date.asc"
        ),
    )
    if not rows:
        return []

    df = pd.DataFrame(rows)
    df["metric_date"] = pd.to_datetime(df["metric_date"])
    df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")

    alerts = []

    # Sum all bedroom types per date per submarket to get total listings
    totals = df.groupby(["submarket", "metric_date"]).agg(
        total=("metric_value", "sum")
    ).reset_index().sort_values(["submarket", "metric_date"])

    for sub, grp in totals.groupby("submarket", dropna=False):
        if len(grp) < 3:
            continue

        # Check MoM change
        current = grp.iloc[-1]["total"]
        previous = grp.iloc[-2]["total"]
        if previous > 0:
            change_pct = (current - previous) / previous * 100
            if abs(change_pct) >= 15:
                zone = SUBMARKET_TO_ZONE.get(sub, sub) if sub else "Market"
                direction = "aumentó" if change_pct > 0 else "disminuyó"
                severity = "warning" if abs(change_pct) >= 25 else "info"

                alerts.append({
                    "alert_type": "supply_shock",
                    "city": _market_to_city(market),
                    "zone": zone,
                    "market": market,
                    "submarket": sub,
                    "metric_name": "active_listings",
                    "current_value": float(current),
                    "expected_value": float(previous),
                    "deviation_pct": round(change_pct, 1),
                    "severity": severity,
                    "message": f"Oferta en {zone} {direction} {abs(change_pct):.0f}% MoM ({int(previous)} → {int(current)} listings)",
                })

    return alerts


def _market_to_city(market: str) -> str:
    """Reverse lookup: market slug → city name."""
    for city, m in CITY_TO_MARKET.items():
        if m == market:
            return city
    return market.replace("_", " ").title()


def main():
    print("=" * 60)
    print("Propyte Analytics — Anomaly Detector")
    print(f"Date: {date.today().isoformat()}")
    print(f"Z-score threshold: {Z_THRESHOLD} | Rolling window: {ROLLING_WINDOW} months")
    print("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials not configured")
        sys.exit(1)

    all_alerts = []

    for city, market in CITY_TO_MARKET.items():
        print(f"\n[{city.upper()}]")

        # AirDNA anomalies
        airdna_alerts = detect_airdna_anomalies(market)
        print(f"  AirDNA anomalies: {len(airdna_alerts)}")
        all_alerts.extend(airdna_alerts)

        # Rental price outliers
        rental_alerts = detect_rental_outliers(city)
        print(f"  Rental outliers: {len(rental_alerts)}")
        all_alerts.extend(rental_alerts)

        # Supply changes
        supply_alerts = detect_supply_changes(market)
        print(f"  Supply changes: {len(supply_alerts)}")
        all_alerts.extend(supply_alerts)

    if all_alerts:
        print(f"\n[UPSERT] Uploading {len(all_alerts)} alerts...")
        ok = supabase_upsert("market_alerts", all_alerts)
        print(f"  market_alerts: {'OK' if ok else 'FAILED'}")

        # Summary
        for sev in ["critical", "warning", "info"]:
            count = sum(1 for a in all_alerts if a["severity"] == sev)
            if count > 0:
                print(f"  {sev}: {count}")
    else:
        print("\nNo anomalies detected")

    print("\nDone!")


if __name__ == "__main__":
    main()
