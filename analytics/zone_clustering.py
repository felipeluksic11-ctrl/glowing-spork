#!/usr/bin/env python3
"""
Zone Clustering — KMeans clustering of zones by investment profile
Reads from zone_scores, writes cluster_label back to zone_scores
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
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pandas", "numpy", "scikit-learn"], check=True)
    import numpy as np
    import pandas as pd
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from analista_rentas import supabase_fetch, SUPABASE_URL, SUPABASE_KEY

N_CLUSTERS = 4

CLUSTER_LABELS = {
    0: "Premium Vacation",
    1: "High-Yield Residential",
    2: "Emerging Growth",
    3: "Value Opportunity",
}

# Features for clustering
CLUSTER_FEATURES = [
    "median_occupancy",
    "median_adr",
    "revpar",
    "yield_component",
    "supply_pressure_component",
    "active_listings",
]


def fetch_latest_zone_scores() -> pd.DataFrame:
    """Fetch latest zone scores."""
    rows = supabase_fetch(
        "zone_scores",
        select="id,city,zone,score,median_occupancy,median_adr,revpar,"
               "yield_component,supply_pressure_component,active_listings,"
               "median_rent,price_to_rent_ratio",
        filters="order=computed_at.desc&limit=500",
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Keep latest per zone
    df = df.drop_duplicates(subset=["city", "zone"], keep="first")
    return df


def assign_cluster_labels(df: pd.DataFrame, labels: np.ndarray) -> dict[int, str]:
    """Assign meaningful labels to clusters based on centroid characteristics."""
    label_map = {}

    for cluster_id in range(N_CLUSTERS):
        mask = labels == cluster_id
        cluster = df[mask]
        if cluster.empty:
            label_map[cluster_id] = f"Cluster {cluster_id}"
            continue

        avg_occ = cluster["median_occupancy"].mean() if "median_occupancy" in cluster else 0
        avg_adr = cluster["median_adr"].mean() if "median_adr" in cluster else 0
        avg_yield = cluster["yield_component"].mean() if "yield_component" in cluster else 50
        avg_supply = cluster["supply_pressure_component"].mean() if "supply_pressure_component" in cluster else 50

        # Heuristic labeling based on cluster characteristics
        if avg_occ > 60 and avg_adr > 2000:
            label_map[cluster_id] = "Premium Vacation"
        elif avg_yield > 60:
            label_map[cluster_id] = "High-Yield Residential"
        elif avg_supply > 60:
            label_map[cluster_id] = "Emerging Growth"
        else:
            label_map[cluster_id] = "Value Opportunity"

    # Deduplicate labels
    used = set()
    available = list(CLUSTER_LABELS.values())
    for k, v in label_map.items():
        if v in used:
            for alt in available:
                if alt not in used:
                    label_map[k] = alt
                    break
        used.add(label_map[k])

    return label_map


def run_clustering(df: pd.DataFrame) -> pd.DataFrame:
    """Run KMeans clustering on zone scores."""
    if len(df) < N_CLUSTERS:
        print(f"  Not enough zones ({len(df)}) for {N_CLUSTERS} clusters")
        df["cluster_label"] = "Uncategorized"
        return df

    # Prepare features
    feature_cols = [c for c in CLUSTER_FEATURES if c in df.columns]
    X = df[feature_cols].fillna(0).values

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Fit KMeans
    actual_k = min(N_CLUSTERS, len(df))
    kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    # Assign meaningful labels
    label_map = assign_cluster_labels(df, labels)
    df["cluster_label"] = [label_map.get(l, f"Cluster {l}") for l in labels]

    return df


def update_cluster_labels(df: pd.DataFrame):
    """Update cluster_label in zone_scores table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    updated = 0
    for _, row in df.iterrows():
        if pd.isna(row.get("id")):
            continue
        url = f"{SUPABASE_URL}/rest/v1/zone_scores?id=eq.{int(row['id'])}"
        resp = requests.patch(
            url,
            json={"cluster_label": row["cluster_label"]},
            headers=headers,
            timeout=10,
        )
        if resp.status_code in (200, 204):
            updated += 1

    print(f"  Updated {updated} zone_scores with cluster labels")


def main():
    print("=" * 60)
    print("Propyte Analytics — Zone Clustering")
    print(f"Date: {date.today().isoformat()}")
    print(f"Clusters: {N_CLUSTERS}")
    print("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials not configured")
        sys.exit(1)

    df = fetch_latest_zone_scores()
    if df.empty:
        print("No zone scores found. Run compute_derived.py first.")
        sys.exit(0)

    print(f"\nLoaded {len(df)} zones from zone_scores")

    # Run clustering
    df = run_clustering(df)

    # Print results
    print("\nCluster assignments:")
    for label in df["cluster_label"].unique():
        zones = df[df["cluster_label"] == label]["zone"].tolist()
        print(f"  {label}: {', '.join(zones)}")

    # Update in DB
    update_cluster_labels(df)

    print("\nDone!")


if __name__ == "__main__":
    main()
