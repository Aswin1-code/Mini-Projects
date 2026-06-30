import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from xgboost import XGBClassifier

# =====================================================
# 🏸 BADMINTON STROKE CLASSIFICATION - V3 (XGBOOST)
# =====================================================

print("\n==============================================")
print("🏸 BADMINTON STROKE CLASSIFICATION V3 TRAINER")
print("==============================================")

# =====================================================
# FILE PATHS
# =====================================================

DATASET_FILE = r"your_dataset.csv"

MODEL_SAVE_PATH = r"stroke_xgboost_v3.pkl"

# =====================================================
# LOAD DATA
# =====================================================

print("\n📦 Loading dataset...")

df = pd.read_csv(DATASET_FILE)

df = df.dropna()

print("Shape:", df.shape)

# =====================================================
# LABEL COLUMN
# =====================================================

TARGET = "stroke"

if TARGET not in df.columns:
    raise Exception("❌ stroke label column not found")

# =====================================================
# ================= FEATURE ENGINEERING =================
# =====================================================

print("\n🧠 Engineering features...")

eps = 1e-6

# ---------------- CORE FEATURES ----------------
df["peak_acc"] = df["peak_acc"]
df["peak_gyro"] = df["peak_gyro"]
df["duration"] = df["duration"]
df["acc_mag"] = df["acc_mag_mean"]
df["gyro_mag"] = df["gyro_mag_mean"]

# ---------------- ENGINEERED FEATURES ----------------

# ⚡ Explosiveness
df["SPI"] = df["peak_gyro"] * np.log(1 + np.abs(df["peak_acc"]))
df["explosive_energy"] = df["peak_acc"] * df["peak_gyro"] * df["duration"]
df["impact_ratio"] = df["peak_acc"] / (df["peak_gyro"] + eps)

# 🏎 Efficiency
df["acc_efficiency"] = df["peak_acc"] / (df["duration"] + eps)
df["gyro_efficiency"] = df["peak_gyro"] / (df["duration"] + eps)
df["control_index"] = df["acc_mag"] / (df["gyro_mag"] + eps)

# 🎯 Burst features
df["burst_acc"] = df["peak_acc"] / (df["acc_mag"] + eps)
df["burst_gyro"] = df["peak_gyro"] / (df["gyro_mag"] + eps)

# 🧠 Shape / stability
df["shape_ratio"] = (df["peak_gyro"] * df["duration"]) / (df["peak_acc"] + eps)
df["aggression"] = (df["peak_acc"] + df["peak_gyro"]) * df["duration"]
df["smoothness"] = (df["acc_mag"] + df["gyro_mag"]) / (df["peak_acc"] + df["peak_gyro"] + eps)

# =====================================================
# FINAL FEATURE SET (LOCKED V3)
# =====================================================

FEATURES = [
    "peak_acc",
    "peak_gyro",
    "duration",
    "acc_mag",
    "gyro_mag",

    "SPI",
    "explosive_energy",
    "impact_ratio",

    "acc_efficiency",
    "gyro_efficiency",
    "control_index",

    "burst_acc",
    "burst_gyro",

    "shape_ratio",
    "aggression",
    "smoothness"
]

X = df[FEATURES]
y = df[TARGET]

# =====================================================
# TRAIN TEST SPLIT
# =====================================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

# =====================================================
# XGBOOST MODEL
# =====================================================

print("\n🔥 Training XGBoost model...")

model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.9,
    colsample_bytree=0.9,
    objective="multi:softprob",
    num_class=4,
    eval_metric="mlogloss",
    random_state=42
)

model.fit(X_train, y_train)

# =====================================================
# EVALUATION
# =====================================================

y_pred = model.predict(X_test)

print("\n===================================")
print("🎯 RESULTS")
print("===================================")

print("Accuracy:", accuracy_score(y_test, y_pred))

print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))

print("\nConfusion Matrix:\n")
print(confusion_matrix(y_test, y_pred))

# =====================================================
# SAVE MODEL
# =====================================================

joblib.dump({
    "model": model,
    "features": FEATURES,
    "label": TARGET
}, MODEL_SAVE_PATH)

print("\n✅ Model saved at:", MODEL_SAVE_PATH)