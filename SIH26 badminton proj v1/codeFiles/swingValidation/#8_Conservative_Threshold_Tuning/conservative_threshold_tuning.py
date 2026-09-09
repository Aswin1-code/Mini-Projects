import pandas as pd
import numpy as np
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix


# =====================================================
# FILE PATHS
# =====================================================

TRAIN_FILE = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#3_Augmented_Validation\validation_train_augmented.csv"
)

MODEL_FILE = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#6_SVM_hyperParameter_Tuning\swing_validation_model_tuned.pkl"
)

OUTPUT_DIR = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\#8_Conservative_Threshold_Tuning"
)

THRESHOLD_FILE = os.path.join(
    OUTPUT_DIR,
    "optimal_svm_threshold.txt"
)


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

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# =====================================================
# LOAD DATA
# =====================================================

print("\n=====================================================")
print(" STEP 8 - CONSERVATIVE SVM THRESHOLD TUNING")
print("=====================================================\n")

df = pd.read_csv(TRAIN_FILE)

X = df[FEATURES].apply(
    pd.to_numeric,
    errors="coerce"
)

y = (
    df[TARGET]
    .astype(str)
    .str.upper()
    .str.strip()
)

valid_rows = (
    X.notna().all(axis=1) &
    y.notna()
)

X = X.loc[valid_rows]
y = y.loc[valid_rows]


print("Dataset shape:", X.shape)

print("\nClass distribution:")
print(y.value_counts())


# =====================================================
# LOAD MODEL
# =====================================================

print("\nLoading tuned SVM...")

model = joblib.load(
    MODEL_FILE
)

print("Tuned SVM loaded successfully.")


# =====================================================
# CREATE VALIDATION SPLIT
# =====================================================
#
# IMPORTANT:
# The final 78-row test set is NOT touched.
#
# We create a validation set from the training data.
#

X_train, X_val, y_train, y_val = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining portion:", X_train.shape)
print("Validation portion:", X_val.shape)

print("\nValidation distribution:")
print(y_val.value_counts())


# =====================================================
# TRAIN MODEL ON TRAINING PORTION
# =====================================================

print("\nTraining temporary validation model...")

model.fit(
    X_train,
    y_train
)

print("Training completed.")


# =====================================================
# GET SVM DECISION SCORES
# =====================================================

decision_scores = model.decision_function(
    X_val
)


# =====================================================
# CHECK CLASS ORDER
# =====================================================

print("\nSVM classes:")
print(model.named_steps["svm"].classes_)


# =====================================================
# FIND WHICH SCORE DIRECTION MEANS VALID
# =====================================================

classes = model.named_steps["svm"].classes_

valid_index = list(classes).index("VALID")

# For binary SVC, positive decision score normally
# corresponds to classes_[1].
#
# To make this robust, determine direction explicitly.

if valid_index == 1:
    valid_scores = decision_scores
else:
    valid_scores = -decision_scores


# =====================================================
# THRESHOLD SEARCH
# =====================================================

print("\nSearching conservative thresholds...")

thresholds = np.arange(
    -1.5,
    2.01,
    0.05
)

best_threshold = None
best_invalid_rejection = -1
best_valid_recall = -1
best_score = -1


for threshold in thresholds:

    predictions = np.where(
        valid_scores >= threshold,
        "VALID",
        "INVALID"
    )

    cm = confusion_matrix(
        y_val,
        predictions,
        labels=["INVALID", "VALID"]
    )

    invalid_correct = cm[0][0]
    invalid_wrong = cm[0][1]

    valid_wrong = cm[1][0]
    valid_correct = cm[1][1]

    invalid_total = (
        invalid_correct +
        invalid_wrong
    )

    valid_total = (
        valid_correct +
        valid_wrong
    )

    invalid_rejection = (
        invalid_correct /
        invalid_total
        if invalid_total > 0
        else 0
    )

    valid_recall = (
        valid_correct /
        valid_total
        if valid_total > 0
        else 0
    )

    # -------------------------------------------------
    # We strongly prioritize INVALID rejection.
    #
    # But we don't want VALID detection to collapse.
    # -------------------------------------------------

    if valid_recall >= 0.80:

        score = (
            0.70 * invalid_rejection +
            0.30 * valid_recall
        )

        if score > best_score:

            best_score = score
            best_threshold = threshold
            best_invalid_rejection = invalid_rejection
            best_valid_recall = valid_recall


# =====================================================
# DISPLAY RESULT
# =====================================================

print("\n=====================================================")
print(" BEST CONSERVATIVE THRESHOLD")
print("=====================================================\n")

print(
    "Threshold:",
    round(best_threshold, 3)
)

print(
    "INVALID rejection:",
    round(best_invalid_rejection * 100, 2),
    "%"
)

print(
    "VALID detection:",
    round(best_valid_recall * 100, 2),
    "%"
)

print(
    "Validation score:",
    round(best_score * 100, 2),
    "%"
)


# =====================================================
# SAVE THRESHOLD
# =====================================================

with open(
    THRESHOLD_FILE,
    "w"
) as f:

    f.write(
        str(best_threshold)
    )


print("\nThreshold saved to:")
print(THRESHOLD_FILE)


# =====================================================
# COMPLETE
# =====================================================

print("\n=====================================================")
print(" STEP 8 COMPLETED")
print("=====================================================\n")

print(
    "IMPORTANT: The final 78-row test set was NOT used."
)

print(
    "The threshold will be evaluated on the final test set in Step 9."
)