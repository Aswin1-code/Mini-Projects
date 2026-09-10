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
    recall_score,
    f1_score
)

# =====================================================
# PATHS
# =====================================================

TRAIN_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#3_Augmented_Dataset\validation_train_augmented_v2.csv"

TEST_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#2_Split_Dataset\validation_test_v2.csv"

OUTPUT_DIR = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#7_Final_Evaluation"

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
# CREATE OUTPUT DIRECTORY
# =====================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =====================================================
# HEADER
# =====================================================

print("=" * 70)
print("STEP 7 — FINAL UNTOUCHED TEST EVALUATION")
print("=" * 70)

# =====================================================
# LOAD DATA
# =====================================================

print("\n📂 Loading augmented training dataset...")

train_df = pd.read_csv(TRAIN_CSV)

print(f"Training rows : {len(train_df)}")

print("\n📂 Loading FINAL untouched test dataset...")

test_df = pd.read_csv(TEST_CSV)

print(f"Test rows     : {len(test_df)}")

# =====================================================
# CLASS DISTRIBUTION
# =====================================================

print("\n" + "-" * 70)
print("CLASS DISTRIBUTION")
print("-" * 70)

print("\nTraining:")
print(train_df[TARGET].value_counts())

print("\nFinal Test:")
print(test_df[TARGET].value_counts())

# =====================================================
# PREPARE DATA
# =====================================================

X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]

# =====================================================
# BUILD FINAL MODEL
# =====================================================

print("\n" + "-" * 70)
print("BUILDING FINAL SVM")
print("-" * 70)

print("\nParameters:")
print("Kernel        : RBF")
print("C             : 1")
print("Gamma         : 1")
print("Class Weight  : None")
print("Scaler        : StandardScaler")

model = Pipeline([
    ("scaler", StandardScaler()),
    (
        "svm",
        SVC(
            kernel="rbf",
            C=1,
            gamma=1,
            class_weight=None
        )
    )
])

# =====================================================
# TRAIN
# =====================================================

print("\n🧠 Training on ALL 550 augmented training samples...")

model.fit(X_train, y_train)

print("✅ Training completed.")

# =====================================================
# FINAL PREDICTION
# =====================================================

print("\n🔍 Evaluating on untouched 102-row test set...")

y_pred = model.predict(X_test)

# =====================================================
# ACCURACY
# =====================================================

accuracy = accuracy_score(y_test, y_pred)

print("\n" + "=" * 70)
print("FINAL TEST ACCURACY")
print("=" * 70)

print(f"\n🔥 Accuracy : {accuracy:.4f}")
print(f"🔥 Accuracy : {accuracy * 100:.2f}%")

# =====================================================
# CLASSIFICATION REPORT
# =====================================================

print("\n" + "=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        y_test,
        y_pred,
        labels=["INVALID", "VALID"],
        digits=4
    )
)

# =====================================================
# CONFUSION MATRIX
# =====================================================

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=["INVALID", "VALID"]
)

print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

print("\n                 Predicted")
print("              INVALID   VALID")
print(
    f"Actual INVALID   {cm[0,0]:3d}       {cm[0,1]:3d}"
)
print(
    f"Actual VALID     {cm[1,0]:3d}       {cm[1,1]:3d}"
)

# =====================================================
# IMPORTANT GATEKEEPER METRICS
# =====================================================

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

invalid_precision = precision_score(
    y_test,
    y_pred,
    pos_label="INVALID",
    zero_division=0
)

valid_precision = precision_score(
    y_test,
    y_pred,
    pos_label="VALID",
    zero_division=0
)

invalid_f1 = f1_score(
    y_test,
    y_pred,
    pos_label="INVALID"
)

valid_f1 = f1_score(
    y_test,
    y_pred,
    pos_label="VALID"
)

invalid_to_valid = cm[0, 1]
valid_to_invalid = cm[1, 0]

print("\n" + "=" * 70)
print("SWING VALIDATION GATE METRICS")
print("=" * 70)

print(f"\nINVALID Precision : {invalid_precision:.4f}")
print(f"INVALID Recall    : {invalid_recall:.4f}")
print(f"INVALID F1        : {invalid_f1:.4f}")

print(f"\nVALID Precision   : {valid_precision:.4f}")
print(f"VALID Recall      : {valid_recall:.4f}")
print(f"VALID F1          : {valid_f1:.4f}")

print("\n" + "-" * 70)

print(f"INVALID → VALID   : {invalid_to_valid}")
print(f"VALID → INVALID   : {valid_to_invalid}")

# =====================================================
# SAVE PREDICTIONS
# =====================================================

predictions_df = test_df.copy()

predictions_df["predicted_validity"] = y_pred

PREDICTION_FILE = os.path.join(
    OUTPUT_DIR,
    "final_test_predictions_v2.csv"
)

predictions_df.to_csv(
    PREDICTION_FILE,
    index=False
)

# =====================================================
# SAVE MODEL
# =====================================================

MODEL_FILE = os.path.join(
    OUTPUT_DIR,
    "swing_validation_model_final_v2.pkl"
)

joblib.dump(model, MODEL_FILE)

# =====================================================
# SAVE SUMMARY
# =====================================================

summary = pd.DataFrame([{
    "model": "RBF SVM",
    "C": 1,
    "gamma": 1,
    "class_weight": "None",

    "train_samples": len(train_df),
    "test_samples": len(test_df),

    "accuracy": accuracy,

    "INVALID_precision": invalid_precision,
    "INVALID_recall": invalid_recall,
    "INVALID_f1": invalid_f1,

    "VALID_precision": valid_precision,
    "VALID_recall": valid_recall,
    "VALID_f1": valid_f1,

    "INVALID_to_VALID": invalid_to_valid,
    "VALID_to_INVALID": valid_to_invalid
}])

SUMMARY_FILE = os.path.join(
    OUTPUT_DIR,
    "final_evaluation_summary_v2.csv"
)

summary.to_csv(
    SUMMARY_FILE,
    index=False
)

# =====================================================
# FINAL OUTPUT
# =====================================================

print("\n" + "=" * 70)
print("FILES SAVED")
print("=" * 70)

print("\n📄 Predictions:")
print(PREDICTION_FILE)

print("\n🤖 Final Model:")
print(MODEL_FILE)

print("\n📊 Summary:")
print(SUMMARY_FILE)

print("\n" + "=" * 70)
print("STEP 7 COMPLETED ✅")
print("=" * 70)