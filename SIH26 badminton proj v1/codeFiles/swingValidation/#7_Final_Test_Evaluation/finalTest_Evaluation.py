import pandas as pd
import joblib
import os

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


# =====================================================
# FILE PATHS
# =====================================================

TEST_FILE = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#2_Split_Validation\validation_test.csv"
)

BASELINE_MODEL_FILE = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#4_SVM_Training_Evaluation\swing_validation_model.pkl"
)

TUNED_MODEL_FILE = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#6_SVM_hyperParameter_Tuning\svm_hyperParameter_tuning.py"
)

OUTPUT_DIR = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#7_Final_Test_Evaluation"
)

RESULTS_FILE = os.path.join(
    OUTPUT_DIR,
    "final_model_comparison.csv"
)

PREDICTIONS_FILE = os.path.join(
    OUTPUT_DIR,
    "final_test_predictions.csv"
)


# =====================================================
# CREATE OUTPUT DIRECTORY
# =====================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)


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
# LOAD TEST DATA
# =====================================================

print("\n=====================================================")
print(" STEP 7 - FINAL TEST EVALUATION")
print("=====================================================\n")

df = pd.read_csv(TEST_FILE)

print("Test dataset shape:", df.shape)

print("\nTest class distribution:")
print(df[TARGET].value_counts())


# =====================================================
# PREPARE DATA
# =====================================================

X = df[FEATURES].apply(pd.to_numeric, errors="coerce")
y = df[TARGET].astype(str).str.upper().str.strip()

valid_rows = X.notna().all(axis=1) & y.notna()

X = X.loc[valid_rows]
y = y.loc[valid_rows]

original_test = df.loc[valid_rows].copy()


# =====================================================
# LOAD MODELS
# =====================================================

print("\nLoading models...")

baseline_model = joblib.load(
    BASELINE_MODEL_FILE
)

tuned_model = joblib.load(
    TUNED_MODEL_FILE
)

print("Baseline model loaded.")
print("Tuned model loaded.")


# =====================================================
# PREDICTIONS
# =====================================================

baseline_predictions = baseline_model.predict(X)

tuned_predictions = tuned_model.predict(X)


# =====================================================
# EVALUATION FUNCTION
# =====================================================

def evaluate_model(name, y_true, predictions):

    print("\n=====================================================")
    print(f" {name}")
    print("=====================================================\n")

    # -------------------------------------------------
    # Accuracy
    # -------------------------------------------------

    accuracy = accuracy_score(
        y_true,
        predictions
    )

    # -------------------------------------------------
    # Confusion Matrix
    # -------------------------------------------------

    cm = confusion_matrix(
        y_true,
        predictions,
        labels=["INVALID", "VALID"]
    )

    invalid_correct = cm[0][0]
    invalid_wrong = cm[0][1]

    valid_wrong = cm[1][0]
    valid_correct = cm[1][1]

    # -------------------------------------------------
    # Rates
    # -------------------------------------------------

    invalid_rejection_rate = (
        invalid_correct /
        (invalid_correct + invalid_wrong)
        if (invalid_correct + invalid_wrong) > 0
        else 0
    )

    invalid_false_positive_rate = (
        invalid_wrong /
        (invalid_correct + invalid_wrong)
        if (invalid_correct + invalid_wrong) > 0
        else 0
    )

    valid_detection_rate = (
        valid_correct /
        (valid_correct + valid_wrong)
        if (valid_correct + valid_wrong) > 0
        else 0
    )

    # -------------------------------------------------
    # Print
    # -------------------------------------------------

    print(
        "Accuracy:",
        round(accuracy * 100, 2),
        "%"
    )

    print(
        "INVALID rejection:",
        round(invalid_rejection_rate * 100, 2),
        "%"
    )

    print(
        "INVALID → VALID:",
        invalid_wrong,
        "out of",
        invalid_correct + invalid_wrong
    )

    print(
        "INVALID false-positive rate:",
        round(invalid_false_positive_rate * 100, 2),
        "%"
    )

    print(
        "VALID detection:",
        round(valid_detection_rate * 100, 2),
        "%"
    )

    print(
        "VALID → INVALID:",
        valid_wrong,
        "out of",
        valid_correct + valid_wrong
    )

    print("\nConfusion Matrix")
    print("Rows = Actual")
    print("Columns = Predicted")
    print()
    print("                 Predicted")
    print("              INVALID   VALID")
    print(
        f"Actual INVALID   {invalid_correct:3d}      {invalid_wrong:3d}"
    )
    print(
        f"Actual VALID     {valid_wrong:3d}      {valid_correct:3d}"
    )

    print("\nClassification Report:\n")

    print(
        classification_report(
            y_true,
            predictions,
            labels=["INVALID", "VALID"],
            zero_division=0
        )
    )

    return {
        "model": name,
        "accuracy": accuracy,
        "invalid_rejection": invalid_rejection_rate,
        "invalid_false_positive_rate": invalid_false_positive_rate,
        "invalid_wrong_as_valid": invalid_wrong,
        "valid_detection": valid_detection_rate,
        "valid_wrong_as_invalid": valid_wrong
    }


# =====================================================
# EVALUATE BASELINE
# =====================================================

baseline_results = evaluate_model(
    "BASELINE MODEL - STEP 4",
    y,
    baseline_predictions
)


# =====================================================
# EVALUATE TUNED
# =====================================================

tuned_results = evaluate_model(
    "TUNED MODEL - STEP 6",
    y,
    tuned_predictions
)


# =====================================================
# COMPARISON
# =====================================================

results_df = pd.DataFrame([
    baseline_results,
    tuned_results
])

results_df.to_csv(
    RESULTS_FILE,
    index=False
)


# =====================================================
# SAVE PREDICTIONS
# =====================================================

prediction_df = original_test.copy()

prediction_df["baseline_prediction"] = baseline_predictions
prediction_df["tuned_prediction"] = tuned_predictions

prediction_df["baseline_correct"] = (
    prediction_df[TARGET] ==
    prediction_df["baseline_prediction"]
)

prediction_df["tuned_correct"] = (
    prediction_df[TARGET] ==
    prediction_df["tuned_prediction"]
)

prediction_df.to_csv(
    PREDICTIONS_FILE,
    index=False
)


# =====================================================
# FINAL COMPARISON
# =====================================================

print("\n=====================================================")
print(" FINAL MODEL COMPARISON")
print("=====================================================\n")

print(
    results_df[
        [
            "model",
            "accuracy",
            "invalid_rejection",
            "invalid_false_positive_rate",
            "invalid_wrong_as_valid",
            "valid_detection",
            "valid_wrong_as_invalid"
        ]
    ].to_string(index=False)
)


# =====================================================
# DECISION
# =====================================================

baseline_fp = baseline_results["invalid_wrong_as_valid"]
tuned_fp = tuned_results["invalid_wrong_as_valid"]

print("\n=====================================================")
print(" MODEL DECISION")
print("=====================================================\n")

if tuned_fp < baseline_fp:

    print("🔥 TUNED MODEL IS BETTER")
    print(
        f"INVALID → VALID reduced "
        f"from {baseline_fp} to {tuned_fp}"
    )

elif tuned_fp == baseline_fp:

    print("⚠️ SAME INVALID → VALID COUNT")
    print(
        "Tuning did not reduce false positives."
    )

else:

    print("⚠️ BASELINE MODEL IS BETTER")
    print(
        f"Tuned model increased "
        f"INVALID → VALID from {baseline_fp} to {tuned_fp}"
    )


print("\nResults saved to:")
print(RESULTS_FILE)

print("\nDetailed predictions saved to:")
print(PREDICTIONS_FILE)

print("\n=====================================================")
print(" STEP 7 COMPLETED")
print("=====================================================\n")