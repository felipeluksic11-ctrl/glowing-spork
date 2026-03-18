#!/usr/bin/env python3
"""
Analista de Rentas — ML Rental Estimation Agent
- Fetches rental_comparables from Supabase
- Trains a GradientBoosting model on rental data
- Pre-computes rental estimates for each development + unit combination
- Calculates financial metrics (ROI, IRR, cap rate, yield, breakeven)
- Upserts results to rental_ml_estimates and development_financials tables
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import warnings
from datetime import date
from functools import partial
from pathlib import Path

print = partial(print, flush=True)
warnings.filterwarnings("ignore", category=FutureWarning)

# --- Dependencies ---
try:
    import joblib
    import numpy as np
    import numpy_financial as npf
    import pandas as pd
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import train_test_split
except ImportError:
    subprocess.run(
        [sys.executable, "-m", "pip", "install",
         "pandas", "scikit-learn", "numpy-financial", "joblib", "requests"],
        check=True,
    )
    import joblib
    import numpy as np
    import numpy_financial as npf
    import pandas as pd
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import train_test_split

import requests

# --- Config ---
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
MODEL_PATH = OUTPUT_DIR / "rental_model.pkl"
TODAY = date.today().isoformat()
MODEL_VERSION = f"gbr_v1_{TODAY}"

# Operating expense ratio (maintenance, management, vacancy, taxes)
EXPENSE_RATIO = 0.25

# Supabase config — env vars first (CI), fallback to .env.local (local dev)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
if not SUPABASE_URL:
    ENV_PATH = BASE_DIR / "propyte-web" / ".env.local"
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("NEXT_PUBLIC_SUPABASE_URL="):
                SUPABASE_URL = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("SUPABASE_SERVICE_ROLE_KEY="):
                SUPABASE_KEY = line.split("=", 1)[1].strip().strip('"')

# Valid property types and cities for encoding
PROPERTY_TYPES = [
    "departamento", "penthouse", "casa", "townhouse",
    "studio", "terreno", "macrolote", "local_comercial",
]
CITIES = [
    "Cancun", "Playa del Carmen", "Tulum", "Merida",
    "Puerto Morelos", "Cozumel", "Bacalar",
]


# ================================================================
# SUPABASE HELPERS
# ================================================================

def supabase_fetch(table: str, select: str = "*", filters: str = "") -> list[dict]:
    """Fetch rows from Supabase REST API with pagination."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(f"  [SUPA] No credentials, cannot fetch {table}")
        return []

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    all_rows = []
    offset = 0
    limit = 1000

    while True:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}&limit={limit}&offset={offset}"
        if filters:
            url += f"&{filters}"

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"  [SUPA] Error fetching {table}: {resp.status_code} {resp.text[:200]}")
                break
            rows = resp.json()
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < limit:
                break
            offset += limit
        except Exception as e:
            print(f"  [SUPA] Error fetching {table}: {e}")
            break

    return all_rows


def supabase_upsert(table: str, rows: list[dict], batch_size: int = 100) -> bool:
    """Upsert rows to Supabase in batches."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(f"  [SUPA] No credentials, skipping upsert to {table}")
        return False

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    success = True

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            resp = requests.post(url, json=batch, headers=headers, timeout=30)
            if resp.status_code not in (200, 201):
                print(f"  [SUPA] Error upserting {table} batch {i // batch_size}: {resp.status_code} {resp.text[:200]}")
                success = False
        except Exception as e:
            print(f"  [SUPA] Error upserting {table}: {e}")
            success = False

    return success


# ================================================================
# DATA FETCHING
# ================================================================

def fetch_rental_data() -> pd.DataFrame:
    """Fetch rental_comparables from Supabase."""
    print("[1/9] Fetching rental comparables from Supabase...")
    rows = supabase_fetch("rental_comparables", filters="active=eq.true")
    if not rows:
        print("  No rental data found. Trying local CSV fallback...")
        csv_path = OUTPUT_DIR / "rental_comparables.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            print(f"  Loaded {len(df)} rows from CSV fallback")
            return df
        print("  ERROR: No rental data available")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    print(f"  Fetched {len(df)} active rental listings")
    return df


def fetch_developments() -> pd.DataFrame:
    """Fetch published developments from Supabase."""
    print("[6/9] Fetching developments from Supabase...")
    rows = supabase_fetch(
        "developments",
        select="id,slug,name,city,zone,property_types,price_min_mxn,price_max_mxn,"
               "financing_down_payment,financing_months,financing_interest,roi_appreciation",
        filters="deleted_at=is.null",
    )
    if not rows:
        print("  No developments found")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    print(f"  Fetched {len(df)} developments")
    return df


def fetch_units() -> pd.DataFrame:
    """Fetch units from Supabase."""
    rows = supabase_fetch(
        "units",
        select="id,development_id,bedrooms,bathrooms,area_m2,price_mxn,typology",
    )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


# ================================================================
# PREPROCESSING
# ================================================================

def preprocess(df: pd.DataFrame) -> tuple:
    """
    Preprocess rental data for ML training.
    Returns (X, y, feature_names, zone_encoder, area_medians).
    """
    print("[2/9] Preprocessing data...")

    # Drop invalid rows
    df = df[df["monthly_rent_mxn"].notna() & (df["monthly_rent_mxn"] > 0)].copy()

    # Normalize city names
    city_map = {
        "cancún": "Cancun", "cancun": "Cancun",
        "playa del carmen": "Playa del Carmen",
        "tulum": "Tulum", "tulúm": "Tulum",
        "mérida": "Merida", "merida": "Merida",
        "puerto morelos": "Puerto Morelos",
        "cozumel": "Cozumel",
        "bacalar": "Bacalar",
    }
    df["city"] = df["city"].str.strip().str.lower().map(city_map).fillna(df["city"])

    # Impute area_m2: median per (city, property_type, bedrooms)
    area_medians = {}
    for (city, ptype, beds), grp in df.groupby(["city", "property_type", "bedrooms"]):
        med = grp["area_m2"].median()
        if pd.notna(med):
            area_medians[(city, ptype, beds)] = med

    # Fallback medians: city + property_type
    area_medians_fallback = {}
    for (city, ptype), grp in df.groupby(["city", "property_type"]):
        med = grp["area_m2"].median()
        if pd.notna(med):
            area_medians_fallback[(city, ptype)] = med

    def impute_area(row):
        if pd.notna(row["area_m2"]) and row["area_m2"] > 0:
            return row["area_m2"]
        key = (row["city"], row["property_type"], row.get("bedrooms"))
        if key in area_medians:
            return area_medians[key]
        key2 = (row["city"], row["property_type"])
        return area_medians_fallback.get(key2, 60.0)  # global fallback

    df["area_m2"] = df.apply(impute_area, axis=1)

    # Fill missing bedrooms with mode per city+type, or 2
    beds_mode = df.groupby(["city", "property_type"])["bedrooms"].agg(
        lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 2
    )
    df["bedrooms"] = df.apply(
        lambda r: r["bedrooms"] if pd.notna(r["bedrooms"]) else
        beds_mode.get((r["city"], r["property_type"]), 2),
        axis=1,
    )
    df["bathrooms"] = df["bathrooms"].fillna(df["bedrooms"])  # reasonable proxy

    # Target encoding for zone (mean rent per zone)
    zone_means = df.groupby("zone")["monthly_rent_mxn"].mean()
    global_mean_rent = df["monthly_rent_mxn"].mean()
    zone_encoder = zone_means.to_dict()
    df["zone_encoded"] = df["zone"].map(zone_encoder).fillna(global_mean_rent)

    # One-hot encode property_type and city
    for pt in PROPERTY_TYPES:
        df[f"pt_{pt}"] = (df["property_type"] == pt).astype(int)
    for city in CITIES:
        df[f"city_{city}"] = (df["city"] == city).astype(int)

    # Binary features
    df["is_vacacional"] = (df["rental_type"] == "vacacional").astype(int)
    df["is_furnished"] = df["is_furnished"].fillna(False).astype(int)

    # Feature columns
    feature_cols = (
        ["bedrooms", "bathrooms", "area_m2", "zone_encoded", "is_vacacional", "is_furnished"]
        + [f"pt_{pt}" for pt in PROPERTY_TYPES]
        + [f"city_{city}" for city in CITIES]
    )

    X = df[feature_cols].values
    y = np.log1p(df["monthly_rent_mxn"].values)  # log-transform target

    print(f"  Features: {len(feature_cols)}, Samples: {len(X)}")
    print(f"  area_m2 coverage: {(df['area_m2'] > 0).mean():.1%}")

    return X, y, feature_cols, zone_encoder, area_medians, area_medians_fallback


# ================================================================
# MODEL TRAINING
# ================================================================

def train_model(X, y, feature_cols):
    """Train GradientBoosting model and evaluate."""
    print("[3/9] Training GradientBoosting model...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42,
    )

    model = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.1,
        min_samples_leaf=10,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae_log = mean_absolute_error(y_test, y_pred)

    # Convert back from log scale for interpretable metrics
    y_test_mxn = np.expm1(y_test)
    y_pred_mxn = np.expm1(y_pred)
    mae_mxn = mean_absolute_error(y_test_mxn, y_pred_mxn)
    mape = np.mean(np.abs((y_test_mxn - y_pred_mxn) / y_test_mxn)) * 100

    print(f"  R² = {r2:.4f}")
    print(f"  MAE = ${mae_mxn:,.0f} MXN")
    print(f"  MAPE = {mape:.1f}%")

    # Feature importance
    print("[4/9] Feature importance (top 10):")
    importances = sorted(
        zip(feature_cols, model.feature_importances_),
        key=lambda x: x[1], reverse=True,
    )
    for feat, imp in importances[:10]:
        print(f"  {feat}: {imp:.4f}")

    # Save model
    print("[5/9] Saving model...")
    joblib.dump({"model": model, "features": feature_cols, "r2": r2}, MODEL_PATH)
    print(f"  Saved to {MODEL_PATH}")

    return model, r2


# ================================================================
# PREDICTION & FINANCIAL CALCULATIONS
# ================================================================

def build_feature_vector(
    city: str,
    zone: str | None,
    unit_type: str,
    bedrooms: int,
    area_m2: float,
    rental_type: str,
    is_furnished: bool,
    zone_encoder: dict,
    feature_cols: list,
) -> np.ndarray:
    """Build a feature vector for prediction."""
    global_mean = np.mean(list(zone_encoder.values())) if zone_encoder else 15000

    features = {
        "bedrooms": bedrooms,
        "bathrooms": max(1, bedrooms),  # estimate
        "area_m2": area_m2,
        "zone_encoded": zone_encoder.get(zone, global_mean),
        "is_vacacional": 1 if rental_type == "vacacional" else 0,
        "is_furnished": 1 if is_furnished else 0,
    }
    for pt in PROPERTY_TYPES:
        features[f"pt_{pt}"] = 1 if unit_type == pt else 0
    for c in CITIES:
        features[f"city_{c}"] = 1 if city == c else 0

    return np.array([[features.get(f, 0) for f in feature_cols]])


def calculate_monthly_payment(price: float, down_pct: float, months: int, annual_rate: float) -> float:
    """Calculate monthly mortgage payment."""
    principal = price * (1 - down_pct / 100)
    if months == 0 or principal <= 0:
        return 0
    if annual_rate == 0:
        return principal / months
    monthly_rate = annual_rate / 100 / 12
    payment = (principal * monthly_rate * (1 + monthly_rate) ** months) / \
              ((1 + monthly_rate) ** months - 1)
    return payment


def calculate_irr(down_payment: float, annual_net_flow: float, sale_proceeds: float, years: int) -> float | None:
    """Calculate IRR using numpy_financial."""
    if down_payment <= 0 or years <= 0:
        return None
    cash_flows = [-down_payment] + [annual_net_flow] * (years - 1) + [annual_net_flow + sale_proceeds]
    try:
        irr = npf.irr(cash_flows)
        if np.isnan(irr) or np.isinf(irr):
            return None
        return round(irr * 100, 2)  # as percentage
    except Exception:
        return None


def predict_for_developments(
    model, feature_cols, r2, zone_encoder,
    area_medians, area_medians_fallback,
    developments: pd.DataFrame, units: pd.DataFrame,
) -> tuple[list[dict], list[dict]]:
    """
    Generate ML estimates and financial metrics for each development.
    Returns (ml_estimates, financials).
    """
    print("[7/9] Generating predictions for developments...")

    # Count zone samples for confidence
    zone_sample_counts = {}
    for zone, count in zone_encoder.items():
        zone_sample_counts[zone] = 1  # will be updated below

    ml_estimates = []
    financials = []

    for _, dev in developments.iterrows():
        dev_id = dev["id"]
        city = dev.get("city", "")
        zone = dev.get("zone")
        price_min = dev.get("price_min_mxn") or 0
        price_max = dev.get("price_max_mxn") or 0
        representative_price = price_min if price_min > 0 else price_max
        if representative_price <= 0:
            continue

        property_types = dev.get("property_types") or ["departamento"]
        if isinstance(property_types, str):
            try:
                property_types = json.loads(property_types)
            except Exception:
                property_types = ["departamento"]

        down_pct = dev.get("financing_down_payment") or 30
        financing_months_raw = dev.get("financing_months") or [120]
        if isinstance(financing_months_raw, str):
            try:
                financing_months_raw = json.loads(financing_months_raw)
            except Exception:
                financing_months_raw = [120]
        financing_months = financing_months_raw[0] if financing_months_raw else 120
        interest_rate = dev.get("financing_interest") or 12
        appreciation = dev.get("roi_appreciation") or 8

        # Get unit combinations for this development
        dev_units = units[units["development_id"] == dev_id] if not units.empty else pd.DataFrame()
        if not dev_units.empty:
            combos = dev_units.groupby(["typology", "bedrooms"]).first().reset_index()
            combos = [(row.get("typology", "departamento"), row.get("bedrooms", 2), row.get("area_m2"))
                       for _, row in combos.iterrows()]
        else:
            # Generate default combos from property_types
            combos = []
            for pt in property_types:
                for beds in [1, 2, 3]:
                    combos.append((pt, beds, None))

        best_rent_res = 0
        best_rent_vac = 0

        for unit_type, bedrooms, unit_area in combos:
            if pd.isna(bedrooms) or bedrooms is None:
                bedrooms = 2
            bedrooms = int(bedrooms)
            unit_type = unit_type or "departamento"

            # Get area estimate
            if unit_area and not pd.isna(unit_area) and unit_area > 0:
                area = float(unit_area)
            else:
                area = area_medians.get((city, unit_type, bedrooms),
                       area_medians_fallback.get((city, unit_type), 60.0))

            # Predict residencial
            vec_res = build_feature_vector(
                city, zone, unit_type, bedrooms, area,
                "residencial", False, zone_encoder, feature_cols,
            )
            pred_res = int(round(np.expm1(model.predict(vec_res)[0]) / 100) * 100)
            pred_res = max(pred_res, 3000)  # minimum sanity check

            # Predict vacacional
            vec_vac = build_feature_vector(
                city, zone, unit_type, bedrooms, area,
                "vacacional", True, zone_encoder, feature_cols,
            )
            pred_vac = int(round(np.expm1(model.predict(vec_vac)[0]) / 100) * 100)
            pred_vac = max(pred_vac, 5000)

            # Confidence score
            zone_count = zone_sample_counts.get(zone, 0)
            confidence = round(r2 * min(1.0, zone_count / 10), 2) if zone else round(r2 * 0.3, 2)
            confidence = max(0.1, min(confidence, 0.99))

            ml_estimates.append({
                "development_id": dev_id,
                "unit_type": unit_type,
                "bedrooms": bedrooms,
                "estimated_rent_residencial": pred_res,
                "estimated_rent_vacacional": pred_vac,
                "confidence_score": confidence,
                "model_version": MODEL_VERSION,
            })

            if pred_res > best_rent_res:
                best_rent_res = pred_res
                best_rent_vac = pred_vac

        # --- Financial metrics for the development ---
        if best_rent_res <= 0:
            continue

        annual_rent = best_rent_res * 12
        annual_rent_net = annual_rent * (1 - EXPENSE_RATIO)
        down_payment = representative_price * (down_pct / 100)

        monthly_payment = calculate_monthly_payment(
            representative_price, down_pct, financing_months, interest_rate
        )
        monthly_net = (best_rent_res * (1 - EXPENSE_RATIO)) - monthly_payment
        annual_net_flow = monthly_net * 12

        rent_yield_gross = round((annual_rent / representative_price) * 100, 2)
        rent_yield_net = round((annual_rent_net / representative_price) * 100, 2)
        cap_rate = rent_yield_net
        cash_on_cash = round((annual_net_flow / down_payment) * 100, 2) if down_payment > 0 else 0

        breakeven = math.ceil(down_payment / monthly_net) if monthly_net > 0 else None
        if breakeven and breakeven > 600:
            breakeven = None

        # IRR calculations
        sale_5yr = representative_price * (1 + appreciation / 100) ** 5
        remaining_5yr = max(0, representative_price * (1 - down_pct / 100) - (monthly_payment * 60))
        irr_5yr = calculate_irr(down_payment, annual_net_flow, sale_5yr - remaining_5yr, 5)

        sale_10yr = representative_price * (1 + appreciation / 100) ** 10
        remaining_10yr = max(0, representative_price * (1 - down_pct / 100) - (monthly_payment * 120))
        irr_10yr = calculate_irr(down_payment, annual_net_flow, sale_10yr - remaining_10yr, 10)

        roi_annual = round(((annual_net_flow + (sale_5yr - representative_price) / 5) / down_payment) * 100, 2) if down_payment > 0 else 0

        financials.append({
            "development_id": dev_id,
            "roi_annual_pct": roi_annual,
            "irr_5yr": irr_5yr,
            "irr_10yr": irr_10yr,
            "cash_on_cash_pct": cash_on_cash,
            "breakeven_months": breakeven,
            "monthly_net_flow": int(monthly_net),
            "cap_rate": cap_rate,
            "rent_yield_gross": rent_yield_gross,
            "rent_yield_net": rent_yield_net,
            "estimated_rent_residencial": best_rent_res,
            "estimated_rent_vacacional": best_rent_vac,
            "model_version": MODEL_VERSION,
        })

    print(f"  Generated {len(ml_estimates)} unit estimates for {len(financials)} developments")
    return ml_estimates, financials


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 60)
    print(f"Analista de Rentas — ML Rental Estimation Agent")
    print(f"Date: {TODAY} | Model: {MODEL_VERSION}")
    print("=" * 60)

    # 1. Fetch data
    df = fetch_rental_data()
    if df.empty or len(df) < 50:
        print("ERROR: Not enough rental data to train model")
        sys.exit(1)

    # 2. Preprocess
    X, y, feature_cols, zone_encoder, area_medians, area_medians_fallback = preprocess(df)

    # 3-5. Train model
    model, r2 = train_model(X, y, feature_cols)

    if r2 < 0.3:
        print(f"WARNING: Model R² = {r2:.4f} is very low. Results may be unreliable.")

    # 6. Fetch developments
    developments = fetch_developments()
    units = fetch_units()

    if developments.empty:
        print("No developments found. Exiting.")
        sys.exit(0)

    # 7. Generate predictions
    ml_estimates, financials = predict_for_developments(
        model, feature_cols, r2, zone_encoder,
        area_medians, area_medians_fallback,
        developments, units,
    )

    # 8. Upsert to Supabase
    print("[8/9] Upserting results to Supabase...")
    if ml_estimates:
        ok1 = supabase_upsert("rental_ml_estimates", ml_estimates)
        print(f"  rental_ml_estimates: {'OK' if ok1 else 'FAILED'} ({len(ml_estimates)} rows)")
    if financials:
        ok2 = supabase_upsert("development_financials", financials)
        print(f"  development_financials: {'OK' if ok2 else 'FAILED'} ({len(financials)} rows)")

    # 9. Summary
    print("[9/9] Summary:")
    print(f"  Model R²: {r2:.4f}")
    print(f"  Developments processed: {len(financials)}")
    print(f"  Unit estimates generated: {len(ml_estimates)}")
    print(f"  Model saved: {MODEL_PATH}")
    print("=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
