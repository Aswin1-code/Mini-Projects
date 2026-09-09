import pandas as pd
import numpy as np
import os
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
# STEP 4 — BASELINE SVM TRAINING + VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("STEP 4 — BASELINE SVM TRAINING + VALIDATION")
print("=" * 70)


# ============================================================
# FILE PATHS
# ============================================================

TRAIN_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\v2_#3_Augmented_Dataset\validation_train_augmented_v2.csv"
)

OUTPUT_FOLDER = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\v2_#4_Baseline_SVM"
)

MODEL_FILE = os.path.join(
    OUTPUT_FOLDER,
    "swing_validation_model_baseline_v2.pkl"
)

VALIDATION_RESULTS_FILE = os.path.join(
    OUTPUT_FOLDER,
    "baseline_validation_predictions_v2.csv"
)


# ============================================================
# ML FEATURES
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
# LOAD DATA
# ============================================================

print("\n📂 Loading augmented training dataset...")

df = pd.read_csv(TRAIN_FILE)

df.columns = df.columns.str.strip()

print(f"Rows loaded : {len(df)}")


# ============================================================
# CHECK DATA
# ============================================================

print("\n" + "-" * 70)
print("DATASET CHECK")
print("-" * 70)

missing_features = [
    feature
    for feature in FEATURES
    if feature not in df.columns
]

if missing_features:
    raise Exception(
        f"❌ Missing features: {missing_features}"
    )

if TARGET not in df.columns:
    raise Exception(
        f"❌ Missing target column: {TARGET}"
    )

print("✅ All 9 features found.")
print("✅ Target column found.")


# ============================================================
# CHECK MISSING VALUES
# ============================================================

missing = df[
    FEATURES + [TARGET]
].isnull().sum()

print("\nMissing values:")
print(missing)

if missing.sum() > 0:
    raise Exception(
        "❌ Missing values detected."
    )

print("\n✅ No missing values.")


# ============================================================
# CLASS DISTRIBUTION
# ============================================================

print("\n" + "-" * 70)
print("CLASS DISTRIBUTION")
print("-" * 70)

print(
    df[TARGET].value_counts()
)


# ============================================================
# PREPARE X AND y
# ============================================================

X = df[FEATURES].copy()
y = df[TARGET].copy()


# ============================================================
# INTERNAL VALIDATION SPLIT
# ============================================================

print("\n" + "=" * 70)
print("CREATING INTERNAL VALIDATION SPLIT")
print("=" * 70)

X_train, X_val, y_train, y_val = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y,
    shuffle=True
)

print(f"\nTraining portion   : {len(X_train)}")
print(f"Validation portion : {len(X_val)}")

print("\nTraining distribution:")
print(y_train.value_counts())

print("\nValidation distribution:")
print(y_val.value_counts())


# ============================================================
# BUILD BASELINE SVM
# ============================================================

print("\n" + "=" * 70)
print("BUILDING BASELINE SVM")
print("=" * 70)

model = Pipeline([
    (
        "scaler",
        StandardScaler()
    ),

    (
        "svm",
        SVC(
            kernel="rbf",
            C=10,
            gamma="scale",
            class_weight="balanced"
        )
    )
])


print("\nSVM configuration:")
print("Kernel       : RBF")
print("C            : 10")
print("Gamma        : scale")
print("Class weight : balanced")


# ============================================================
# TRAIN MODEL
# ============================================================

print("\n" + "=" * 70)
print("TRAINING MODEL")
print("=" * 70)

model.fit(
    X_train,
    y_train
)

print("\n✅ SVM training completed.")


# ============================================================
# VALIDATION PREDICTION
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION EVALUATION")
print("=" * 70)

y_pred = model.predict(X_val)


# ============================================================
# ACCURACY
# ============================================================

accuracy = accuracy_score(
    y_val,
    y_pred
)

print(
    f"\n🔥 Validation Accuracy : "
    f"{accuracy * 100:.2f}%"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\n" + "-" * 70)
print("CLASSIFICATION REPORT")
print("-" * 70)

print(
    classification_report(
        y_val,
        y_pred,
        labels=["INVALID", "VALID"],
        digits=4,
        zero_division=0
    )
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    y_val,
    y_pred,
    labels=["INVALID", "VALID"]
)

print("\n" + "-" * 70)
print("CONFUSION MATRIX")
print("-" * 70)

print(
    "                 Predicted"
)

print(
    "                 INVALID   VALID"
)

print(
    f"Actual INVALID   {cm[0][0]:8d} {cm[0][1]:7d}"
)

print(
    f"Actual VALID     {cm[1][0]:8d} {cm[1][1]:7d}"
)


# ============================================================
# EXPLICIT ERROR COUNTS
# ============================================================

invalid_as_valid = cm[0][1]
valid_as_invalid = cm[1][0]

invalid_rejection = (
    cm[0][0] / cm[0].sum()
    if cm[0].sum() > 0
    else 0
)

valid_detection = (
    cm[1][1] / cm[1].sum()
    if cm[1].sum() > 0
    else 0
)


print("\n" + "-" * 70)
print("VALIDATION ERROR ANALYSIS")
print("-" * 70)

print(
    f"INVALID → VALID : "
    f"{invalid_as_valid}"
)

print(
    f"VALID → INVALID : "
    f"{valid_as_invalid}"
)

print(
    f"\nINVALID rejection : "
    f"{invalid_rejection * 100:.2f}%"
)

print(
    f"VALID detection   : "
    f"{valid_detection * 100:.2f}%"
)


# ============================================================
# SAVE VALIDATION PREDICTIONS
# ============================================================

validation_output = X_val.copy()

validation_output["actual_validity"] = y_val.values
validation_output["predicted_validity"] = y_pred

validation_output["correct"] = (
    validation_output["actual_validity"]
    ==
    validation_output["predicted_validity"]
)

validation_output = validation_output.reset_index(
    drop=True
)


# ============================================================
# CREATE OUTPUT FOLDER
# ============================================================

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


# ============================================================
# SAVE MODEL
# ============================================================

print("\n" + "=" * 70)
print("SAVING BASELINE MODEL")
print("=" * 70)

joblib.dump(
    model,
    MODEL_FILE
)

print("\n✅ Model saved:")
print(MODEL_FILE)


# ============================================================
# SAVE VALIDATION RESULTS
# ============================================================

validation_output.to_csv(
    VALIDATION_RESULTS_FILE,
    index=False
)

print("\n✅ Validation predictions saved:")
print(VALIDATION_RESULTS_FILE)


# ============================================================
# RELOAD MODEL TEST
# ============================================================

print("\n" + "=" * 70)
print("MODEL RELOAD VERIFICATION")
print("=" * 70)

loaded_model = joblib.load(
    MODEL_FILE
)

test_predictions = loaded_model.predict(
    X_val.iloc[:5]
)

print(
    "\nFirst 5 predictions after reload:"
)

print(test_predictions)

print(
    "\n✅ Saved model can be successfully reloaded."
)


# ============================================================
# FINAL STATUS
# ============================================================

print("\n" + "=" * 70)
print("STEP 4 COMPLETED ✅")
print("=" * 70)

print("""
CURRENT PIPELINE

508 MASTER
   │
   ├── 406 TRAIN
   │      │
   │      └── VALID augmentation
   │              │
   │              ▼
   │          550 TRAINING DATA
   │              │
   │              ▼
   │          BASELINE SVM
   │
   └── 102 FINAL TEST
          │
          └── 🔒 UNTOUCHED

IMPORTANT:
The 102-row final test dataset was NOT used.
It remains reserved for final evaluation.
""")