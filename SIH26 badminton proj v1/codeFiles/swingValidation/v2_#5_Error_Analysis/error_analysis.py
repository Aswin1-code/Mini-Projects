import pandas as pd
import numpy as np
import os


# ============================================================
# STEP 5 — SVM ERROR ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("STEP 5 — SVM ERROR ANALYSIS")
print("=" * 70)


# ============================================================
# FILE PATHS
# ============================================================

VALIDATION_PREDICTIONS_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\v2_#4_Baseline_SVM\baseline_validation_predictions_v2.csv"
)

TRAIN_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\v2_#3_Augmented_Dataset\validation_train_augmented_v2.csv"
)

OUTPUT_FOLDER = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\v2_#5_Error_Analysis"
)


# ============================================================
# OUTPUT FILES
# ============================================================

INVALID_AS_VALID_FILE = os.path.join(
    OUTPUT_FOLDER,
    "invalid_predicted_as_valid_v2.csv"
)

VALID_AS_INVALID_FILE = os.path.join(
    OUTPUT_FOLDER,
    "valid_predicted_as_invalid_v2.csv"
)

ALL_ERRORS_FILE = os.path.join(
    OUTPUT_FOLDER,
    "all_validation_errors_v2.csv"
)

FEATURE_STATS_FILE = os.path.join(
    OUTPUT_FOLDER,
    "feature_distribution_comparison_v2.csv"
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

ACTUAL_COLUMN = "actual_validity"
PREDICTED_COLUMN = "predicted_validity"


# ============================================================
# LOAD VALIDATION PREDICTIONS
# ============================================================

print("\n📂 Loading validation predictions...")

pred_df = pd.read_csv(
    VALIDATION_PREDICTIONS_FILE
)

print(
    f"Validation rows loaded : {len(pred_df)}"
)


# ============================================================
# CHECK COLUMNS
# ============================================================

print("\n" + "-" * 70)
print("CHECKING PREDICTION DATA")
print("-" * 70)

required_columns = (
    FEATURES
    +
    [
        ACTUAL_COLUMN,
        PREDICTED_COLUMN
    ]
)

missing_columns = [
    col
    for col in required_columns
    if col not in pred_df.columns
]

if missing_columns:

    raise Exception(
        f"❌ Missing columns: {missing_columns}"
    )

print("✅ All required columns found.")


# ============================================================
# IDENTIFY ERRORS
# ============================================================

print("\n" + "=" * 70)
print("IDENTIFYING MISCLASSIFICATIONS")
print("=" * 70)


# INVALID predicted as VALID
invalid_as_valid = pred_df[
    (pred_df[ACTUAL_COLUMN] == "INVALID")
    &
    (pred_df[PREDICTED_COLUMN] == "VALID")
].copy()


# VALID predicted as INVALID
valid_as_invalid = pred_df[
    (pred_df[ACTUAL_COLUMN] == "VALID")
    &
    (pred_df[PREDICTED_COLUMN] == "INVALID")
].copy()


# All errors
all_errors = pred_df[
    pred_df[ACTUAL_COLUMN]
    !=
    pred_df[PREDICTED_COLUMN]
].copy()


print(
    f"\nINVALID → VALID : "
    f"{len(invalid_as_valid)}"
)

print(
    f"VALID → INVALID : "
    f"{len(valid_as_invalid)}"
)

print(
    f"TOTAL ERRORS    : "
    f"{len(all_errors)}"
)


# ============================================================
# DISPLAY INVALID → VALID
# ============================================================

print("\n" + "=" * 70)
print("HARD NEGATIVES — INVALID PREDICTED AS VALID")
print("=" * 70)

if len(invalid_as_valid) == 0:

    print("\n🎉 No INVALID → VALID errors.")

else:

    print(
        "\nThese are the most important errors "
        "for our swing-validation gate:"
    )

    print(
        invalid_as_valid[
            FEATURES
            +
            [
                ACTUAL_COLUMN,
                PREDICTED_COLUMN
            ]
        ].to_string(index=False)
    )


# ============================================================
# DISPLAY VALID → INVALID
# ============================================================

print("\n" + "=" * 70)
print("FALSE NEGATIVES — VALID PREDICTED AS INVALID")
print("=" * 70)

if len(valid_as_invalid) == 0:

    print("\n🎉 No VALID → INVALID errors.")

else:

    print(
        valid_as_invalid[
            FEATURES
            +
            [
                ACTUAL_COLUMN,
                PREDICTED_COLUMN
            ]
        ].to_string(index=False)
    )


# ============================================================
# FEATURE RANGE ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("FEATURE DISTRIBUTION ANALYSIS")
print("=" * 70)

train_df = pd.read_csv(
    TRAIN_FILE
)

train_df.columns = train_df.columns.str.strip()


# ------------------------------------------------------------
# Create statistics
# ------------------------------------------------------------

stats_rows = []


for feature in FEATURES:

    valid_values = train_df[
        train_df["validity"] == "VALID"
    ][feature]

    invalid_values = train_df[
        train_df["validity"] == "INVALID"
    ][feature]

    error_values = invalid_as_valid[feature]


    stats_rows.append({

        "feature": feature,

        "VALID_mean":
            valid_values.mean(),

        "VALID_std":
            valid_values.std(),

        "VALID_min":
            valid_values.min(),

        "VALID_max":
            valid_values.max(),

        "INVALID_mean":
            invalid_values.mean(),

        "INVALID_std":
            invalid_values.std(),

        "INVALID_min":
            invalid_values.min(),

        "INVALID_max":
            invalid_values.max(),

        "INVALID_AS_VALID_mean":
            error_values.mean()
            if len(error_values) > 0
            else np.nan,

        "INVALID_AS_VALID_min":
            error_values.min()
            if len(error_values) > 0
            else np.nan,

        "INVALID_AS_VALID_max":
            error_values.max()
            if len(error_values) > 0
            else np.nan

    })


stats_df = pd.DataFrame(
    stats_rows
)


# ============================================================
# PRINT FEATURE STATISTICS
# ============================================================

print("\n")

print(
    stats_df.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


# ============================================================
# SAVE ERROR FILES
# ============================================================

invalid_as_valid.to_csv(
    INVALID_AS_VALID_FILE,
    index=False
)

valid_as_invalid.to_csv(
    VALID_AS_INVALID_FILE,
    index=False
)

all_errors.to_csv(
    ALL_ERRORS_FILE,
    index=False
)

stats_df.to_csv(
    FEATURE_STATS_FILE,
    index=False
)


# ============================================================
# PRINT SAVED FILES
# ============================================================

print("\n" + "=" * 70)
print("ERROR ANALYSIS FILES SAVED")
print("=" * 70)

print("\n❌ INVALID → VALID:")
print(INVALID_AS_VALID_FILE)

print("\n❌ VALID → INVALID:")
print(VALID_AS_INVALID_FILE)

print("\n❌ ALL ERRORS:")
print(ALL_ERRORS_FILE)

print("\n📊 FEATURE STATISTICS:")
print(FEATURE_STATS_FILE)


# ============================================================
# IMPORTANT INTERPRETATION
# ============================================================

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)

if len(invalid_as_valid) > 0:

    print("""
⚠ INVALID → VALID errors exist.

This means some INVALID swings occupy a feature
region that looks similar to VALID swings.

These samples should be treated as HARD NEGATIVES.

We will inspect them before deciding whether:
    • hyperparameter tuning is useful
    • class weighting should change
    • additional feature engineering is needed
    • more representative training data is required
""")

else:

    print("""
✅ No INVALID → VALID errors found in this validation split.
""")


# ============================================================
# FINAL STATUS
# ============================================================

print("\n" + "=" * 70)
print("STEP 5 COMPLETED ✅")
print("=" * 70)