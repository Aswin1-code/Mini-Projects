import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, ParameterGrid
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

# =====================================================
# PATHS
# =====================================================

TRAIN_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#3_Augmented_Dataset\validation_train_augmented_v2.csv"

OUTPUT_DIR = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#6_SVM_Tuning"

# =====================================================
# FEATURES
# =====================================================

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

# =====================================================
# LOAD DATA
# =====================================================

print("=" * 70)
print("STEP 6 — SVM HYPERPARAMETER EXPERIMENT")
print("=" * 70)

print("\n📂 Loading augmented training dataset...")

df = pd.read_csv(TRAIN_CSV)

print(f"Total rows : {len(df)}")

# =====================================================
# PREPARE DATA
# =====================================================

X = df[FEATURES]
y = df[TARGET]

print("\nClass distribution:")
print(y.value_counts())

# =====================================================
# INTERNAL VALIDATION SPLIT
# =====================================================

X_train, X_val, y_train, y_val = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nInternal split:")
print(f"Training   : {len(X_train)}")
print(f"Validation : {len(X_val)}")

# =====================================================
# PARAMETER GRID
# =====================================================

param_grid = {
    "C": [0.1, 1, 10, 100],
    "gamma": ["scale", 0.001, 0.01, 0.1, 1],
    "class_weight": [None, "balanced"]
}

grid = list(ParameterGrid(param_grid))

print(f"\n🔍 Total configurations to test : {len(grid)}")

# =====================================================
# RESULTS
# =====================================================

results = []

best_invalid_recall = -1
best_valid_recall = -1
best_model = None
best_params = None

# =====================================================
# EXPERIMENT LOOP
# =====================================================

for i, params in enumerate(grid, start=1):

    model = Pipeline([
        ("scaler", StandardScaler()),
        (
            "svm",
            SVC(
                kernel="rbf",
                C=params["C"],
                gamma=params["gamma"],
                class_weight=params["class_weight"]
            )
        )
    ])

    model.fit(X_train, y_train)

    pred = model.predict(X_val)

    accuracy = accuracy_score(y_val, pred)

    # VALID = positive class
    valid_precision = precision_score(
        y_val,
        pred,
        pos_label="VALID",
        zero_division=0
    )

    valid_recall = recall_score(
        y_val,
        pred,
        pos_label="VALID",
        zero_division=0
    )

    valid_f1 = f1_score(
        y_val,
        pred,
        pos_label="VALID",
        zero_division=0
    )

    # INVALID = negative class
    invalid_precision = precision_score(
        y_val,
        pred,
        pos_label="INVALID",
        zero_division=0
    )

    invalid_recall = recall_score(
        y_val,
        pred,
        pos_label="INVALID",
        zero_division=0
    )

    invalid_f1 = f1_score(
        y_val,
        pred,
        pos_label="INVALID",
        zero_division=0
    )

    # Confusion matrix
    cm = confusion_matrix(
        y_val,
        pred,
        labels=["INVALID", "VALID"]
    )

    invalid_to_valid = cm[0, 1]
    valid_to_invalid = cm[1, 0]

    results.append({
        "C": params["C"],
        "gamma": params["gamma"],
        "class_weight": params["class_weight"],

        "accuracy": accuracy,

        "INVALID_precision": invalid_precision,
        "INVALID_recall": invalid_recall,
        "INVALID_f1": invalid_f1,

        "VALID_precision": valid_precision,
        "VALID_recall": valid_recall,
        "VALID_f1": valid_f1,

        "INVALID_to_VALID": invalid_to_valid,
        "VALID_to_INVALID": valid_to_invalid
    })

    # -------------------------------------------------
    # PRIORITY:
    # 1. INVALID recall
    # 2. VALID recall
    # 3. Accuracy
    # -------------------------------------------------

    if (
        invalid_recall > best_invalid_recall
        or (
            invalid_recall == best_invalid_recall
            and valid_recall > best_valid_recall
        )
    ):
        best_invalid_recall = invalid_recall
        best_valid_recall = valid_recall

        best_model = model
        best_params = params

    print(
        f"[{i:02d}/{len(grid)}] "
        f"C={params['C']:<5} "
        f"gamma={str(params['gamma']):<7} "
        f"weight={str(params['class_weight']):<8} | "
        f"ACC={accuracy:.4f} | "
        f"INV_REC={invalid_recall:.4f} | "
        f"VAL_REC={valid_recall:.4f} | "
        f"INV→VAL={invalid_to_valid}"
    )

# =====================================================
# RESULTS DATAFRAME
# =====================================================

results_df = pd.DataFrame(results)

# Sort primarily by:
# 1. INVALID recall
# 2. VALID recall
# 3. Accuracy

results_df = results_df.sort_values(
    by=[
        "INVALID_recall",
        "VALID_recall",
        "accuracy"
    ],
    ascending=False
)

# =====================================================
# CREATE OUTPUT DIRECTORY
# =====================================================

import os

os.makedirs(OUTPUT_DIR, exist_ok=True)

RESULTS_CSV = os.path.join(
    OUTPUT_DIR,
    "svm_hyperparameter_results_v2.csv"
)

results_df.to_csv(
    RESULTS_CSV,
    index=False
)

# =====================================================
# DISPLAY TOP RESULTS
# =====================================================

print("\n")
print("=" * 70)
print("TOP 10 CONFIGURATIONS")
print("=" * 70)

print(
    results_df.head(10).to_string(index=False)
)

# =====================================================
# BEST MODEL
# =====================================================

print("\n")
print("=" * 70)
print("BEST CONFIGURATION")
print("=" * 70)

print(f"C            : {best_params['C']}")
print(f"gamma        : {best_params['gamma']}")
print(f"class_weight : {best_params['class_weight']}")

# =====================================================
# BEST MODEL CONFUSION MATRIX
# =====================================================

best_pred = best_model.predict(X_val)

best_cm = confusion_matrix(
    y_val,
    best_pred,
    labels=["INVALID", "VALID"]
)

print("\nConfusion Matrix:")
print("                 Predicted")
print("              INVALID   VALID")
print(
    f"Actual INVALID   {best_cm[0,0]:3d}       {best_cm[0,1]:3d}"
)
print(
    f"Actual VALID     {best_cm[1,0]:3d}       {best_cm[1,1]:3d}"
)

print("\n")
print("=" * 70)
print("BEST MODEL METRICS")
print("=" * 70)

print(
    f"Accuracy           : "
    f"{accuracy_score(y_val, best_pred):.4f}"
)

print(
    f"INVALID Recall     : "
    f"{recall_score(y_val, best_pred, pos_label='INVALID'):.4f}"
)

print(
    f"VALID Recall       : "
    f"{recall_score(y_val, best_pred, pos_label='VALID'):.4f}"
)

print(
    f"INVALID → VALID    : "
    f"{best_cm[0,1]}"
)

print(
    f"VALID → INVALID    : "
    f"{best_cm[1,0]}"
)

print("\n")
print("=" * 70)
print("RESULT FILE")
print("=" * 70)

print(RESULTS_CSV)

print("\n")
print("=" * 70)
print("STEP 6 COMPLETED ✅")
print("=" * 70)