"""
train_model.py
==============
ASD Toddler Screening — Model Training Script
Run this once to produce asd_model.pkl and model_metadata.json.

Usage:
    python train_model.py

Outputs:
    asd_model.pkl         — Serialized XGBoost classifier
    model_metadata.json   — Feature order, version, training stats
"""

import os
import json
import warnings
import joblib
import kagglehub
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
MODEL_OUTPUT_PATH = "asd_model1.pkl"
# METADATA_OUTPUT_PATH = "model_metadata.json"
METADATA_OUTPUT_PATH = "model_card1.json"
RANDOM_STATE = 42
TEST_SIZE = 0.20
# Age_Mons is EXCLUDED intentionally so the inference API does not require it.
# The Streamlit / FastAPI intake form does not collect exact age in months.
# If you later add that field to the form, add "Age_Mons" back here and retrain.
INCLUDE_AGE_MONS = False


# ─────────────────────────────────────────────
# STEP 1 — LOAD DATA
# ─────────────────────────────────────────────
def load_dataset() -> pd.DataFrame:
    print(">>> Downloading Toddler ASD dataset from Kaggle...")
    path = kagglehub.dataset_download("fabdelja/autism-screening-for-toddlers")

    csv_files = [f for f in os.listdir(path) if f.endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"No CSV file found in {path}")

    exact_path = os.path.join(path, csv_files[0])
    print(f"    Found: {csv_files[0]}")
    df = pd.read_csv(exact_path)
    print(f"    Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    return df


# ─────────────────────────────────────────────
# STEP 2 — PREPROCESS
# ─────────────────────────────────────────────
def preprocess(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """
    Returns (X, y, feature_cols) with deterministic column ordering.
    Column order is saved to metadata so inference always matches training.
    """
    # --- Target column ---
    # Dynamically locate it (handles both 'Class/ASD Traits ' and 'Class/ASD')
    target_candidates = [c for c in df.columns if "class" in c.lower() or "asd" in c.lower()]
    if not target_candidates:
        raise ValueError(f"Cannot find a target column. Columns: {df.columns.tolist()}")
    target_col = target_candidates[-1]
    print(f"    Target column: '{target_col}'")

    if df[target_col].dtype == "object":
        df["Target"] = df[target_col].apply(
            lambda x: 1 if str(x).strip().lower() == "yes" else 0
        )
    else:
        df["Target"] = df[target_col].astype(int)

    # --- Feature columns ---
    # A1–A10: always present
    behavioral_cols = sorted(
        [c for c in df.columns if c.startswith("A") and c[1:].isdigit()],
        key=lambda c: int(c[1:]),
    )
    if len(behavioral_cols) != 10:
        raise ValueError(f"Expected 10 A-columns, found: {behavioral_cols}")

    optional_cols = []
    if INCLUDE_AGE_MONS and "Age_Mons" in df.columns:
        optional_cols.append("Age_Mons")
    if "Sex" in df.columns:
        optional_cols.append("Sex")

    # DETERMINISTIC ORDER — critical for inference column alignment
    feature_cols = behavioral_cols + optional_cols
    print(f"    Features ({len(feature_cols)}): {feature_cols}")

    X = df[feature_cols].copy()

    # --- Encode Sex ---
    if "Sex" in X.columns:
        X["Sex"] = X["Sex"].apply(
            lambda x: 1 if str(x).strip().lower() in {"m", "male", "males"} else 0
        )

    # --- Encode Age_Mons (fill missing with median if used) ---
    if "Age_Mons" in X.columns:
        median_age = X["Age_Mons"].median()
        X["Age_Mons"] = X["Age_Mons"].fillna(median_age).astype(float)

    # --- Validate A1–A10 are strictly binary ---
    for col in behavioral_cols:
        unique_vals = set(X[col].dropna().unique())
        if not unique_vals.issubset({0, 1}):
            raise ValueError(
                f"Column {col} contains non-binary values: {unique_vals}"
            )

    y = df["Target"]
    print(f"    Class distribution: {y.value_counts().to_dict()}")
    return X, y, feature_cols


# ─────────────────────────────────────────────
# STEP 3 — TRAIN
# ─────────────────────────────────────────────
def train(X: pd.DataFrame, y: pd.Series) -> tuple[xgb.XGBClassifier, dict]:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    print(f"\n    Train size: {len(X_train)} | Test size: {len(X_test)}")
    print("    Training XGBoost...")

    model = xgb.XGBClassifier(
        eval_metric="logloss",
        random_state=RANDOM_STATE,
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    # --- Evaluation ---
    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, preds)
    auc = roc_auc_score(y_test, proba)

    print(f"\n    ✅ Accuracy : {accuracy * 100:.2f}%")
    print(f"    ✅ ROC-AUC  : {auc:.4f}")
    print("\n    Classification Report:")
    print(classification_report(y_test, preds))

    metrics = {
        "accuracy": round(float(accuracy), 4),
        "roc_auc": round(float(auc), 4),
        "test_size": len(X_test),
        "train_size": len(X_train),
    }
    return model, metrics


# ─────────────────────────────────────────────
# STEP 4 — SAVE
# ─────────────────────────────────────────────
def save_artifacts(
    model: xgb.XGBClassifier,
    feature_cols: list[str],
    metrics: dict,
) -> None:
    # Model
    joblib.dump(model, MODEL_OUTPUT_PATH)
    print(f"\n    ✅ Model saved → {MODEL_OUTPUT_PATH}")

    # Metadata — consumed by FastAPI / Streamlit at inference time
    metadata = {
        "feature_cols": feature_cols,          # EXACT order used during training
        "model_file": MODEL_OUTPUT_PATH,
        "joblib_version": joblib.__version__,
        "xgboost_version": xgb.__version__,
        "training_metrics": metrics,
        "binary_features": [c for c in feature_cols if c.startswith("A")],
        "categorical_features": {
            "Sex": {"0": "Female", "1": "Male"},
        },
        "include_age_mons": INCLUDE_AGE_MONS,
    }
    with open(METADATA_OUTPUT_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"    ✅ Metadata saved → {METADATA_OUTPUT_PATH}")
    print(f"\n    Feature order locked in: {feature_cols}")


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("   ASD TODDLER SCREENING — MODEL TRAINING")
    print("=" * 60)

    print("\n[1/4] Loading dataset...")
    df = load_dataset()

    print("\n[2/4] Preprocessing...")
    X, y, feature_cols = preprocess(df)

    print("\n[3/4] Training model...")
    model, metrics = train(X, y)

    print("\n[4/4] Saving artifacts...")
    save_artifacts(model, feature_cols, metrics)

    print("\n" + "=" * 60)
    print("   TRAINING COMPLETE")
    print("=" * 60)

    