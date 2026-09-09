import pandas as pd
import numpy as np
import os
import joblib

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score
)


# ============================================================
# STEP 4 — TRAIN + EVALUATE SWING VALIDATION SVM
# ============================================================


# ============================================================
# FILE PATHS
# ============================================================

TRAIN_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#3_Augmented_validation\validation_train_augmented.csv"
)

TEST_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#2_Split_validation\validation_test.csv"
)

MODEL_DIR = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\ML_model_swingValidation"
)

MODEL_FILE = os.path.join(
    MODEL_DIR,
    "swing_validation_model.pkl"
)


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
# START
# ============================================================

print("\n==============================================")
print("STEP 4 — SWING VALIDATION SVM")
print("==============================================")


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading training data...")

train_df = pd.read_csv(TRAIN_FILE)

print("Training shape:", train_df.shape)

print("\nLoading test data...")

test_df = pd.read_csv(TEST_FILE)

print("Test shape:", test_df.shape)


# ============================================================
# CHECK COLUMNS
# ============================================================

required_columns = FEATURES + [TARGET]

for col in required_columns:

    if col not in train_df.columns:
        raise ValueError(
            f"Training dataset missing column: {col}"
        )

    if col not in test_df.columns:
        raise ValueError(
            f"Test dataset missing column: {col}"
        )


# ============================================================
# CLEAN DATA
# ============================================================

for col in FEATURES:

    train_df[col] = pd.to_numeric(
        train_df[col],
        errors="coerce"
    )

    test_df[col] = pd.to_numeric(
        test_df[col],
        errors="coerce"
    )


train_df = train_df.dropna(
    subset=FEATURES + [TARGET]
).copy()

test_df = test_df.dropna(
    subset=FEATURES + [TARGET]
).copy()


# ============================================================
# NORMALIZE LABELS
# ============================================================

train_df[TARGET] = (
    train_df[TARGET]
    .astype(str)
    .str.upper()
    .str.strip()
)

test_df[TARGET] = (
    test_df[TARGET]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# PREPARE X AND Y
# ============================================================

X_train = train_df[FEATURES]

y_train = train_df[TARGET]

X_test = test_df[FEATURES]

y_test = test_df[TARGET]


# ============================================================
# SHOW DATA DISTRIBUTION
# ============================================================

print("\n----------------------------------------------")
print("TRAINING DISTRIBUTION")
print("----------------------------------------------")

print(
    y_train.value_counts().to_string()
)


print("\n----------------------------------------------")
print("TEST DISTRIBUTION")
print("----------------------------------------------")

print(
    y_test.value_counts().to_string()
)


# ============================================================
# CREATE SVM PIPELINE
# ============================================================

print("\n----------------------------------------------")
print("CREATING SVM MODEL")
print("----------------------------------------------")

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


# ============================================================
# TRAIN
# ============================================================

print("\nTraining SVM...")

model.fit(
    X_train,
    y_train
)

print("Training completed.")


# ============================================================
# PREDICTION
# ============================================================

print("\nGenerating predictions...")

y_pred = model.predict(
    X_test
)


# ============================================================
# ACCURACY
# ============================================================

accuracy = accuracy_score(
    y_test,
    y_pred
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=["INVALID", "VALID"]
)

tn, fp, fn, tp = cm.ravel()


# ============================================================
# INVALID REJECTION PERFORMANCE
# ============================================================

invalid_recall = recall_score(
    y_test,
    y_pred,
    pos_label="INVALID"
)

valid_recall = recall_score(
    y_test,
    y_pred,
    pos_label="VALID"
)

valid_precision = precision_score(
    y_test,
    y_pred,
    pos_label="VALID",
    zero_division=0
)


# ============================================================
# FALSE POSITIVE RATE
# ============================================================

# Actual INVALID → predicted VALID

false_positive_rate = (
    fp / (fp + tn)
    if (fp + tn) > 0
    else 0
)


# ============================================================
# RESULTS
# ============================================================

print("\n==============================================")
print("MODEL RESULTS")
print("==============================================")


print(
    f"\nAccuracy : {accuracy * 100:.2f}%"
)


print(
    f"\nVALID Recall : {valid_recall * 100:.2f}%"
)


print(
    f"INVALID Recall : {invalid_recall * 100:.2f}%"
)


print(
    f"VALID Precision : {valid_precision * 100:.2f}%"
)


print(
    f"INVALID → VALID rate : "
    f"{false_positive_rate * 100:.2f}%"
)


# ============================================================
# MOST IMPORTANT RESULT
# ============================================================

print("\n----------------------------------------------")
print("❗ INVALID → VALID ANALYSIS")
print("----------------------------------------------")

print(
    f"Actual INVALID test samples : {tn + fp}"
)

print(
    f"Correctly rejected as INVALID : {tn}"
)

print(
    f"❌ Incorrectly accepted as VALID : {fp}"
)


print(
    f"\nINVALID rejection rate : "
    f"{tn / (tn + fp) * 100:.2f}%"
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

print("\n----------------------------------------------")
print("CONFUSION MATRIX")
print("----------------------------------------------")

print(
    "\n                Predicted"
)

print(
    "              INVALID   VALID"
)

print(
    f"Actual INVALID   {tn:3d}      {fp:3d}"
)

print(
    f"Actual VALID     {fn:3d}      {tp:3d}"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\n----------------------------------------------")
print("CLASSIFICATION REPORT")
print("----------------------------------------------")

print(
    classification_report(
        y_test,
        y_pred,
        labels=["INVALID", "VALID"],
        zero_division=0
    )
)


# ============================================================
# SAVE MODEL
# ============================================================

print("\n----------------------------------------------")
print("SAVING MODEL")
print("----------------------------------------------")

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

joblib.dump(
    model,
    MODEL_FILE
)


print(
    "\nModel saved successfully:"
)

print(
    MODEL_FILE
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n==============================================")
print("STEP 4 FINISHED")
print("==============================================")

print(
    f"\nTraining samples : {len(train_df)}"
)

print(
    f"Test samples     : {len(test_df)}"
)

print(
    f"Accuracy         : {accuracy * 100:.2f}%"
)

print(
    f"VALID recall     : {valid_recall * 100:.2f}%"
)

print(
    f"INVALID recall   : {invalid_recall * 100:.2f}%"
)

print(
    f"INVALID → VALID  : {fp} samples"
)

print("\n==============================================\n")