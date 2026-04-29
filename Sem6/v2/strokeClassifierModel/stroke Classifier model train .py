import pandas as pd
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# =====================================================
# 🏸 BADMINTON STROKE CLASSIFICATION MODEL TRAINER
# =====================================================

print("\n==============================================")
print("🏸 BADMINTON STROKE CLASSIFICATION ML TRAINER")
print("==============================================")

# =====================================================
# FILE PATHS
# =====================================================

DATASET_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\strokeClassifierModel\stroke_data\badminton_stroke_dataset_realistic_new.csv"

MODEL_SAVE_PATH = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\strokeClassifierModel\stroke classifier pkl\stroke_model.pkl"

# =====================================================
# LOAD DATA
# =====================================================

print("\n🏸 Loading dataset...")

df = pd.read_csv(DATASET_FILE)

print("Shape:", df.shape)

print("\nColumns:", df.columns)

# =====================================================
# AUTO DETECT LABEL COLUMN
# =====================================================

if "stroke" in df.columns:
    TARGET = "stroke"
elif "stroke_label" in df.columns:
    TARGET = "stroke_label"
else:
    raise Exception("No stroke label column found!")

# =====================================================
# FEATURES
# =====================================================

FEATURES = [
    "ax","ay","az",
    "gx","gy","gz",
    "speed","impact","duration",
    "acc_mag","gyro_mag",
    "peak_acc","peak_gyro",
    "power","efficiency","energy"
]

# remove missing safely
df = df.dropna()

X = df[FEATURES]
y = df[TARGET]

# =====================================================
# SPLIT
# =====================================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

# =====================================================
# MODEL
# =====================================================

print("\n🔥 Training model...")

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=15,
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

# =====================================================
# SAVE MODEL
# =====================================================

joblib.dump({
    "model": model,
    "features": FEATURES,
    "label": TARGET
}, MODEL_SAVE_PATH)

print("\n✅ Model saved:", MODEL_SAVE_PATH)