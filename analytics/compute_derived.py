#!/usr/bin/env python3
"""
Compute Derived Metrics — Zone Intelligence Scores, RevPAR, Price-to-Rent ratios
Reads from airdna_metrics, rental_comparables, development_financials
Writes to zone_scores table
"""

from __future__ import annotations

import os
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

# Add parent to path for shared helpers
sys.path.insert(0, str(Path(__file__).parent.parent))
from analista_rentas import supabase_fetch, supabase_upsert, SUPABASE_URL, SUPABASE_KEY

# Zone score weights
WEIGHTS = {
    "yield": 0.30,
    "occupancy": 0.25,
    "adr_growth": 0.20,
    "supply_pressure": 0.15,
    "liquidity": 0.10,
}

# Cancun submarket → zone mapping (mirrors calculator.ts)
SUBMARKET_TO_ZONE = {
    "smz_4": "Zona Hotelera",
    "sm_2a": "Puerto Cancún",
    "smz_16": "Puerto Cancún",
    "sm_2": "Centro",
    "sm_23": "Supermanzana 11-17",
    "sm_24": "Arbolada",
    "smz_25": "Aqua / Cumbres",
    "sm_27": "Lagos del Sol",
    "sm_28": "Alfredo V. Bonfil",
    "sm_32": "Las Torres",
    "sm_63": "Isla Dorada",
    "sm_69": "Residencial Río",
    "sm_72": "Selvamar",
    "smz_35": "Palmaris",
    "sm_64": "Campestre",
}

CITY_TO_MARKET = {
    "Cancun": "cancun",
    "Playa del Carmen": "playa_del_carmen",
    "Tulum": "tulum",
    "Merida": "merida",
    "Puerto Morelos": "puerto_morelos",
    "Cozumel": "cozumel",
    "Bacalar": "bacalar",
}


def normalize_min_max(values: pd.Series) -> pd.Series:
    """Normalize values to 0-100 scale using min-max."""
    vmin, vmax = values.min(), values.max()
    if vmax == vmin:
        return pd.Series(50.0, index=values.index)
    return ((values - vmin) / (vmax - vmin)) * 100


def fetch_airdna_occupancy(market: str) -> pd.DataFrame:
    """Fetch latest occupancy per submarket."""
    rows = supabase_fetch(
        "airdna_metrics",
        select="submarket,metric_value,metric_date",
        filters=f"market=eq.{market}&section=eq.occupancy&chart=eq.chart_1"
                f"&metric_name=eq.occupancy&submarket=not.is.null"
                f"&order=metric_date.desc&limit=500",
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Take latest per submarket
    df = df.sort_values("metric_date", ascending=False).drop_duplicates("submarket")
    return df.rename(columns={"metric_value": "occupancy"})


def fetch_airdna_adr(market: str) -> pd.DataFrame:
    """Fetch latest and previous ADR per submarket for growth calculation."""
    rows = supabase_fetch(
        "airdna_metrics",
        select="submarket,metric_value,metric_date",
        filters=f"market=eq.{market}&section=eq.rates&chart=eq.chart_1"
                f"&metric_name=eq.daily_rate&submarket=not.is.null"
                f"&order=metric_date.desc&limit=1000",
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values("metric_date", ascending=False)

    results = []
    for sub, grp in df.groupby("submarket"):
        grp = grp.head(2)
        current = grp.iloc[0]["metric_value"] if len(grp) > 0 else None
        previous = grp.iloc[1]["metric_value"] if len(grp) > 1 else None
        growth = ((current - previous) / previous * 100) if current and previous and previous > 0 else 0
        results.append({
            "submarket": sub,
            "adr": current,
            "adr_previous": previous,
            "adr_growth_pct": growth,
        })

    return pd.DataFrame(results)


def fetch_airdna_listings(market: str) -> pd.DataFrame:
    """Fetch latest listing counts per submarket."""
    rows = supabase_fetch(
        "airdna_metrics",
        select="submarket,metric_name,metric_value,metric_date",
        filters=f"market=eq.{market}&section=eq.listings&chart=eq.chart_1"
                f"&submarket=not.is.null&order=metric_date.desc&limit=500",
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Sum all bedroom counts per submarket (latest date)
    df = df.sort_values("metric_date", ascending=False)
    latest_per_sub = df.groupby("submarket")["metric_date"].first().to_dict()

    totals = []
    for sub, latest_date in latest_per_sub.items():
        mask = (df["submarket"] == sub) & (df["metric_date"] == latest_date)
        total = df[mask]["metric_value"].sum()
        totals.append({"submarket": sub, "active_listings": int(total)})

    return pd.DataFrame(totals)


def fetch_rental_medians(city: str) -> pd.DataFrame:
    """Fetch median rent per zone from rental_comparables."""
    rows = supabase_fetch(
        "rental_comparables",
        select="zone,monthly_rent_mxn",
        filters=f"city=eq.{city}&active=eq.true&monthly_rent_mxn=gte.5000&monthly_rent_mxn=lte.500000",
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    medians = df.groupby("zone").agg(
        median_rent=("monthly_rent_mxn", "median"),
        sample_size=("monthly_rent_mxn", "count"),
    ).reset_index()
    return medians


def fetch_development_financials() -> pd.DataFrame:
    """Fetch financial metrics per development."""
    rows = supabase_fetch(
        "development_financials",
        select="development_id,rent_yield_net,rent_yield_net_vac,rent_yield_gross,rent_yield_gross_vac",
    )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def fetch_dev_zones() -> pd.DataFrame:
    """Fetch zone mapping for developments."""
    rows = supabase_fetch(
        "developments",
        select="id,city,zone,price_min_mxn",
        filters="deleted_at=is.null",
    )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def compute_zone_scores(city: str, market: str) -> list[dict]:
    """Compute Zone Intelligence Scores for all zones in a city/market."""
    print(f"\n  Computing zone scores for {city} (market: {market})...")

    # Fetch all data sources
    occ_df = fetch_airdna_occupancy(market)
    adr_df = fetch_airdna_adr(market)
    listings_df = fetch_airdna_listings(market)
    rental_df = fetch_rental_medians(city)
    fin_df = fetch_development_financials()
    dev_df = fetch_dev_zones()

    if occ_df.empty and adr_df.empty:
        print(f"    No AirDNA data for {market}, skipping")
        return []

    # Build zone-level metrics from submarket data
    zone_metrics = {}

    # Map submarket → zone and aggregate
    for _, row in occ_df.iterrows():
        sub = row["submarket"]
        zone = SUBMARKET_TO_ZONE.get(sub, sub.upper())
        if zone not in zone_metrics:
            zone_metrics[zone] = {"submarket": sub}
        zone_metrics[zone]["occupancy"] = row["occupancy"]

    for _, row in adr_df.iterrows():
        sub = row["submarket"]
        zone = SUBMARKET_TO_ZONE.get(sub, sub.upper())
        if zone not in zone_metrics:
            zone_metrics[zone] = {"submarket": sub}
        zone_metrics[zone]["adr"] = row["adr"]
        zone_metrics[zone]["adr_growth_pct"] = row["adr_growth_pct"]

    for _, row in listings_df.iterrows():
        sub = row["submarket"]
        zone = SUBMARKET_TO_ZONE.get(sub, sub.upper())
        if zone not in zone_metrics:
            zone_metrics[zone] = {"submarket": sub}
        zone_metrics[zone]["active_listings"] = row["active_listings"]

    # Add rental medians
    for _, row in rental_df.iterrows():
        zone = row["zone"]
        if zone in zone_metrics:
            zone_metrics[zone]["median_rent"] = row["median_rent"]
            zone_metrics[zone]["sample_size"] = row["sample_size"]

    # Add yield from development financials
    if not dev_df.empty and not fin_df.empty:
        dev_zone = dev_df[dev_df["city"] == city].copy()
        if not dev_zone.empty:
            merged = dev_zone.merge(fin_df, left_on="id", right_on="development_id", how="inner")
            zone_yields = merged.groupby("zone").agg(
                yield_net=("rent_yield_net", "median"),
                yield_net_vac=("rent_yield_net_vac", "median"),
                median_price=("price_min_mxn", "median"),
            ).to_dict("index")

            for zone, vals in zone_yields.items():
                if zone in zone_metrics:
                    zone_metrics[zone]["yield_net"] = vals.get("yield_net")
                    zone_metrics[zone]["yield_net_vac"] = vals.get("yield_net_vac")
                    zone_metrics[zone]["median_price"] = vals.get("median_price")

    if not zone_metrics:
        print(f"    No zone metrics computed for {city}")
        return []

    # Build DataFrame for normalization
    df = pd.DataFrame.from_dict(zone_metrics, orient="index")
    df.index.name = "zone"
    df = df.reset_index()

    # Compute derived metrics
    if "adr" in df.columns and "occupancy" in df.columns:
        df["revpar"] = df["adr"].fillna(0) * df["occupancy"].fillna(0) / 100
    else:
        df["revpar"] = 0

    if "median_price" in df.columns and "median_rent" in df.columns:
        df["price_to_rent_ratio"] = df.apply(
            lambda r: r["median_price"] / (r["median_rent"] * 12)
            if pd.notna(r.get("median_price")) and pd.notna(r.get("median_rent")) and r["median_rent"] > 0
            else None,
            axis=1,
        )
    else:
        df["price_to_rent_ratio"] = None

    if "yield_net_vac" in df.columns and "yield_net" in df.columns:
        df["yield_spread"] = df["yield_net_vac"].fillna(0) - df["yield_net"].fillna(0)
    else:
        df["yield_spread"] = 0

    if "active_listings" in df.columns and "occupancy" in df.columns:
        df["supply_demand_ratio"] = df.apply(
            lambda r: r["active_listings"] / (r["occupancy"]) if pd.notna(r.get("occupancy")) and r["occupancy"] > 0 else None,
            axis=1,
        )
    else:
        df["supply_demand_ratio"] = None

    # Compute component scores (0-100 normalized)
    components = {}

    if "yield_net" in df.columns and df["yield_net"].notna().sum() > 1:
        components["yield_component"] = normalize_min_max(df["yield_net"].fillna(df["yield_net"].median()))
    else:
        components["yield_component"] = pd.Series(50.0, index=df.index)

    if "occupancy" in df.columns and df["occupancy"].notna().sum() > 1:
        components["occupancy_component"] = normalize_min_max(df["occupancy"].fillna(df["occupancy"].median()))
    else:
        components["occupancy_component"] = pd.Series(50.0, index=df.index)

    if "adr_growth_pct" in df.columns and df["adr_growth_pct"].notna().sum() > 1:
        components["adr_growth_component"] = normalize_min_max(df["adr_growth_pct"].fillna(0))
    else:
        components["adr_growth_component"] = pd.Series(50.0, index=df.index)

    if "active_listings" in df.columns and df["active_listings"].notna().sum() > 1:
        # Invert: fewer listings = less supply pressure = higher score
        components["supply_pressure_component"] = 100 - normalize_min_max(df["active_listings"].fillna(df["active_listings"].median()))
    else:
        components["supply_pressure_component"] = pd.Series(50.0, index=df.index)

    liquidity = df.get("sample_size", pd.Series(0, index=df.index)).fillna(0)
    if liquidity.max() > liquidity.min():
        components["liquidity_component"] = normalize_min_max(liquidity)
    else:
        components["liquidity_component"] = pd.Series(50.0, index=df.index)

    # Composite score
    df["score"] = (
        components["yield_component"] * WEIGHTS["yield"]
        + components["occupancy_component"] * WEIGHTS["occupancy"]
        + components["adr_growth_component"] * WEIGHTS["adr_growth"]
        + components["supply_pressure_component"] * WEIGHTS["supply_pressure"]
        + components["liquidity_component"] * WEIGHTS["liquidity"]
    ).round(1)

    df["yield_component"] = components["yield_component"].round(1)
    df["occupancy_component"] = components["occupancy_component"].round(1)
    df["adr_growth_component"] = components["adr_growth_component"].round(1)
    df["supply_pressure_component"] = components["supply_pressure_component"].round(1)

    # Build output rows
    results = []
    for _, row in df.iterrows():
        results.append({
            "city": city,
            "zone": row["zone"],
            "score": float(row["score"]) if pd.notna(row["score"]) else None,
            "yield_component": float(row["yield_component"]) if pd.notna(row["yield_component"]) else None,
            "occupancy_component": float(row["occupancy_component"]) if pd.notna(row["occupancy_component"]) else None,
            "adr_growth_component": float(row["adr_growth_component"]) if pd.notna(row["adr_growth_component"]) else None,
            "supply_pressure_component": float(row["supply_pressure_component"]) if pd.notna(row["supply_pressure_component"]) else None,
            "revpar": float(row["revpar"]) if pd.notna(row.get("revpar")) else None,
            "price_to_rent_ratio": float(row["price_to_rent_ratio"]) if pd.notna(row.get("price_to_rent_ratio")) else None,
            "yield_spread": float(row["yield_spread"]) if pd.notna(row.get("yield_spread")) else None,
            "supply_demand_ratio": float(row["supply_demand_ratio"]) if pd.notna(row.get("supply_demand_ratio")) else None,
            "active_listings": int(row["active_listings"]) if pd.notna(row.get("active_listings")) else None,
            "median_adr": float(row["adr"]) if pd.notna(row.get("adr")) else None,
            "median_occupancy": float(row["occupancy"]) if pd.notna(row.get("occupancy")) else None,
            "median_rent": float(row["median_rent"]) if pd.notna(row.get("median_rent")) else None,
        })

    print(f"    Computed scores for {len(results)} zones")
    return results


def main():
    print("=" * 60)
    print("Propyte Analytics — Compute Derived Metrics")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials not configured")
        sys.exit(1)

    all_scores = []
    for city, market in CITY_TO_MARKET.items():
        scores = compute_zone_scores(city, market)
        all_scores.extend(scores)

    if all_scores:
        print(f"\n[UPSERT] Uploading {len(all_scores)} zone scores...")
        ok = supabase_upsert("zone_scores", all_scores)
        print(f"  zone_scores: {'OK' if ok else 'FAILED'}")
    else:
        print("\nNo zone scores computed")

    print("\nDone!")


if __name__ == "__main__":
    main()
