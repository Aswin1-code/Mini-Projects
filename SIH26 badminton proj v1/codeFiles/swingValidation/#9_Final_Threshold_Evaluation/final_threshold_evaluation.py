import pandas as pd
import numpy as np
import joblib
import os
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    classification_report
)

# =====================================================
# FILE PATHS
# =====================================================

# =====================================================
# FILE PATHS
# =====================================================

BASE_DIR = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation"

TEST_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#2_Split_validation\validation_test.csv"

BASELINE_MODEL = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#4_SVM_Training_Evaluation\swing_validation_model.pkl"

TUNED_MODEL = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#6_SVM_hyperParameter_Tuning\swing_validation_model_tuned.pkl"

THRESHOLD_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#8_Conservative_Threshold_Tuning\optimal_svm_threshold.txt"
OUTPUT_DIR = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#9_Final_Threshold_Evaluation"

os.makedirs(OUTPUT_DIR, exist_ok=True)

PREDICTIONS_CSV = os.path.join(
    OUTPUT_DIR,
    "final_threshold_predictions.csv"
)

RESULTS_CSV = os.path.join(
    OUTPUT_DIR,
    "final_threshold_comparison.csv"
)

# =====================================================
# LOAD TEST DATA
# =====================================================

df = pd.read_csv(TEST_CSV)

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

X_test = df[FEATURES]
y_test = df["validity"]

print("\n==============================================")
print("STEP 9 - FINAL THRESHOLD EVALUATION")
print("==============================================")

print("\nTest dataset:")
print(f"Total samples : {len(df)}")
print(f"VALID         : {(y_test == 'VALID').sum()}")
print(f"INVALID       : {(y_test == 'INVALID').sum()}")

# =====================================================
# LOAD MODELS
# =====================================================

baseline_model = joblib.load(BASELINE_MODEL)
tuned_model = joblib.load(TUNED_MODEL)

# =====================================================
# BASELINE PREDICTION
# =====================================================

baseline_pred = baseline_model.predict(X_test)

# =====================================================
# LOAD OPTIMAL THRESHOLD
# =====================================================

with open(THRESHOLD_FILE, "r") as f:
    threshold = float(f.read().strip())

print(f"\nOptimal threshold from Step 8: {threshold}")

# =====================================================
# TUNED MODEL + THRESHOLD
# =====================================================

scores = tuned_model.decision_function(X_test)

classes = tuned_model.named_steps["svm"].classes_

# Make sure higher score always means VALID
if list(classes).index("VALID") == 1:
    valid_scores = scores
else:
    valid_scores = -scores

threshold_pred = np.where(
    valid_scores >= threshold,
    "VALID",
    "INVALID"
)

# =====================================================
# METRIC FUNCTION
# =====================================================

def calculate_metrics(y_true, y_pred):

    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=["INVALID", "VALID"]
    )

    tn, fp, fn, tp = cm.ravel()

    accuracy = accuracy_score(y_true, y_pred)

    invalid_rejection = tn / (tn + fp) if (tn + fp) else 0

    valid_detection = tp / (tp + fn) if (tp + fn) else 0

    return {
        "Accuracy": accuracy,
        "INVALID_rejection": invalid_rejection,
        "INVALID_to_VALID": fp,
        "VALID_detection": valid_detection,
        "VALID_to_INVALID": fn,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "TP": tp
    }

# =====================================================
# CALCULATE RESULTS
# =====================================================

baseline_metrics = calculate_metrics(
    y_test,
    baseline_pred
)

threshold_metrics = calculate_metrics(
    y_test,
    threshold_pred
)

# =====================================================
# PRINT BASELINE
# =====================================================

print("\n==============================================")
print("BASELINE SVM")
print("==============================================")

print(f"Accuracy           : {baseline_metrics['Accuracy'] * 100:.2f}%")
print(f"INVALID rejection  : {baseline_metrics['INVALID_rejection'] * 100:.2f}%")
print(f"INVALID → VALID    : {baseline_metrics['INVALID_to_VALID']}")
print(f"VALID detection    : {baseline_metrics['VALID_detection'] * 100:.2f}%")
print(f"VALID → INVALID    : {baseline_metrics['VALID_to_INVALID']}")

print("\nConfusion Matrix:")
print(
    f"                 Pred INVALID    Pred VALID\n"
    f"Actual INVALID       {baseline_metrics['TN']:>5}          {baseline_metrics['FP']:>5}\n"
    f"Actual VALID         {baseline_metrics['FN']:>5}          {baseline_metrics['TP']:>5}"
)

# =====================================================
# PRINT THRESHOLD RESULTS
# =====================================================

print("\n==============================================")
print("TUNED SVM + THRESHOLD")
print("==============================================")

print(f"Threshold used      : {threshold}")
print(f"Accuracy             : {threshold_metrics['Accuracy'] * 100:.2f}%")
print(f"INVALID rejection    : {threshold_metrics['INVALID_rejection'] * 100:.2f}%")
print(f"INVALID → VALID      : {threshold_metrics['INVALID_to_VALID']}")
print(f"VALID detection      : {threshold_metrics['VALID_detection'] * 100:.2f}%")
print(f"VALID → INVALID      : {threshold_metrics['VALID_to_INVALID']}")

print("\nConfusion Matrix:")
print(
    f"                 Pred INVALID    Pred VALID\n"
    f"Actual INVALID       {threshold_metrics['TN']:>5}          {threshold_metrics['FP']:>5}\n"
    f"Actual VALID         {threshold_metrics['FN']:>5}          {threshold_metrics['TP']:>5}"
)

# =====================================================
# CLASSIFICATION REPORT
# =====================================================

print("\n==============================================")
print("CLASSIFICATION REPORT")
print("==============================================")

print(
    classification_report(
        y_test,
        threshold_pred,
        labels=["INVALID", "VALID"]
    )
)

# =====================================================
# SAVE PREDICTIONS
# =====================================================

output_df = df.copy()

output_df["baseline_prediction"] = baseline_pred
output_df["valid_score"] = valid_scores
output_df["threshold_prediction"] = threshold_pred

output_df.to_csv(
    PREDICTIONS_CSV,
    index=False
)

# =====================================================
# SAVE COMPARISON
# =====================================================

results = pd.DataFrame([
    {
        "Model": "Baseline SVM",
        **baseline_metrics
    },
    {
        "Model": "Tuned SVM + Threshold -0.1",
        **threshold_metrics
    }
])

results.to_csv(
    RESULTS_CSV,
    index=False
)

# =====================================================
# FINAL DECISION
# =====================================================

print("\n==============================================")
print("FINAL DECISION")
print("==============================================")

if (
    threshold_metrics["INVALID_to_VALID"]
    < baseline_metrics["INVALID_to_VALID"]
):
    print("✅ Threshold improved INVALID rejection.")
    print("👉 Use tuned SVM + threshold in the dashboard.")

elif (
    threshold_metrics["INVALID_to_VALID"]
    == baseline_metrics["INVALID_to_VALID"]
):
    print("⚠️ Threshold did not improve INVALID rejection.")
    print("👉 Keep the tuned SVM without forcing the threshold.")

else:
    print("❌ Threshold made INVALID rejection worse.")
    print("👉 Keep the normal tuned SVM.")

print("\nFiles saved:")
print(PREDICTIONS_CSV)
print(RESULTS_CSV)

print("\n==============================================")
print("STEP 9 COMPLETE")
print("==============================================")