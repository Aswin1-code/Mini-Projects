import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# ============================================================
# FILE PATHS
# ============================================================

DATASET_PATH = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\sih\swingValidation\dataset_swingValidation\Original#_combined_validation_dataset.csv"

MODEL_PATH = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\sih\swingValidation\ML_model_swingValidation\swing_validation_model.pkl"


# ============================================================
# FEATURES
# ============================================================

FEATURES = [
    "ax",
    "ay",
    "az",
    "gx",
    "gy",
    "gz",
    "speed",
    "impact",
    "duration"
]

TARGET = "validity"


# ============================================================
# LOAD DATASET
# ============================================================

print("==========================================")
print("LOADING DATASET")
print("==========================================")

df = pd.read_csv(DATASET_PATH)

print(f"Dataset shape: {df.shape}")

print("\nColumns:")
print(df.columns.tolist())


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = FEATURES + [TARGET]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    print("\n❌ Missing columns:")
    print(missing_columns)
    raise ValueError("Required columns are missing from dataset.")


# ============================================================
# CLEAN TARGET LABEL
# ============================================================

df[TARGET] = (
    df[TARGET]
    .astype(str)
    .str.strip()
    .str.upper()
)


# Keep only VALID and INVALID
df = df[df[TARGET].isin(["VALID", "INVALID"])].copy()


# ============================================================
# CONVERT FEATURES TO NUMERIC
# ============================================================

for feature in FEATURES:

    df[feature] = pd.to_numeric(
        df[feature],
        errors="coerce"
    )


# Remove rows containing missing values
df = df.dropna(
    subset=FEATURES + [TARGET]
).reset_index(drop=True)


# ============================================================
# DISPLAY DATASET INFORMATION
# ============================================================

print("\n==========================================")
print("DATASET INFORMATION")
print("==========================================")

print(f"Total samples: {len(df)}")

print("\nValidity distribution:")
print(df[TARGET].value_counts())


print("\nFeatures used:")
for feature in FEATURES:
    print(" -", feature)


# ============================================================
# INPUT / TARGET
# ============================================================

X = df[FEATURES]

y = df[TARGET]


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


print("\n==========================================")
print("TRAIN / TEST SPLIT")
print("==========================================")

print(f"Training samples: {len(X_train)}")
print(f"Testing samples : {len(X_test)}")


# ============================================================
# SVM PIPELINE
# ============================================================

model = Pipeline([

    # Feature scaling
    (
        "scaler",
        StandardScaler()
    ),

    # SVM classifier
    (
        "svm",
        SVC(
            kernel="rbf",
            C=10,
            gamma="scale"
        )
    )
])


# ============================================================
# TRAIN MODEL
# ============================================================

print("\n==========================================")
print("TRAINING SVM")
print("==========================================")

model.fit(
    X_train,
    y_train
)

print("✅ SVM training completed.")


# ============================================================
# PREDICTION
# ============================================================

y_pred = model.predict(X_test)


# ============================================================
# ACCURACY
# ============================================================

accuracy = accuracy_score(
    y_test,
    y_pred
)

print("\n==========================================")
print("MODEL PERFORMANCE")
print("==========================================")

print(f"\nAccuracy: {accuracy:.4f}")

print(f"Accuracy: {accuracy * 100:.2f}%")


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\n==========================================")
print("CLASSIFICATION REPORT")
print("==========================================")

print(
    classification_report(
        y_test,
        y_pred,
        labels=["INVALID", "VALID"]
    )
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=["INVALID", "VALID"]
)

print("\n==========================================")
print("CONFUSION MATRIX")
print("==========================================")

print("                 Predicted")
print("                 INVALID   VALID")
print(
    f"Actual INVALID     {cm[0][0]:3d}       {cm[0][1]:3d}"
)
print(
    f"Actual VALID       {cm[1][0]:3d}       {cm[1][1]:3d}"
)


# ============================================================
# TRAIN FINAL MODEL ON ALL DATA
# ============================================================

print("\n==========================================")
print("TRAINING FINAL MODEL")
print("==========================================")

model.fit(
    X,
    y
)

print("✅ Final model trained using all 102 samples.")


# ============================================================
# SAVE MODEL
# ============================================================

joblib.dump(
    model,
    MODEL_PATH
)

print("\n==========================================")
print("MODEL SAVED")
print("==========================================")

print("Model file:")
print(MODEL_PATH)

print("\n✅ swing_validation_model.pkl created successfully.")