import pandas as pd
import joblib
import os

# ============================================================
# STEP 5 — ERROR ANALYSIS / HARD-NEGATIVE ANALYSIS
# ============================================================

# ============================================================
# FILE PATHS
# ============================================================

TEST_FILE = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#2_Split_validation\validation_test.csv"
)

MODEL_FILE = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#4_SVM_Training_Evaluation\v2_swing_validation_model.pkl"
)

OUTPUT_DIR = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\#5_Error_Analysis"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "invalid_predicted_as_valid.csv"
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
print("STEP 5 — ERROR / HARD-NEGATIVE ANALYSIS")
print("==============================================")


# ============================================================
# LOAD TEST DATA
# ============================================================

print("\nLoading test dataset...")

df = pd.read_csv(TEST_FILE)

print("Test shape:", df.shape)


# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading trained SVM model...")

model = joblib.load(MODEL_FILE)

print("Model loaded successfully.")


# ============================================================
# CLEAN FEATURES
# ============================================================

for col in FEATURES:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

df = df.dropna(
    subset=FEATURES + [TARGET]
).copy()


# ============================================================
# NORMALIZE TARGET
# ============================================================

df[TARGET] = (
    df[TARGET]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# PREDICT
# ============================================================

print("\nGenerating predictions...")

X = df[FEATURES]

df["predicted_validity"] = model.predict(X)


# ============================================================
# FIND FALSE POSITIVES
# ============================================================
#
# Actual INVALID
# but predicted VALID
#
# These are the samples we are most interested in.
# ============================================================

false_positives = df[
    (df[TARGET] == "INVALID") &
    (df["predicted_validity"] == "VALID")
].copy()


# ============================================================
# FIND FALSE NEGATIVES
# ============================================================
#
# Actual VALID
# but predicted INVALID
# ============================================================

false_negatives = df[
    (df[TARGET] == "VALID") &
    (df["predicted_validity"] == "INVALID")
].copy()


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# SAVE FALSE POSITIVES
# ============================================================

false_positives.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# DISPLAY FALSE POSITIVES
# ============================================================

print("\n==============================================")
print("❌ INVALID → VALID ANALYSIS")
print("==============================================")

print(
    "\nNumber of INVALID samples wrongly accepted as VALID:",
    len(false_positives)
)


if len(false_positives) > 0:

    print("\nThese are the hard-negative samples:\n")

    display_columns = [
        TARGET,
        "predicted_validity"
    ] + FEATURES

    print(
        false_positives[
            display_columns
        ].to_string(index=False)
    )

else:

    print(
        "\n🎉 No INVALID samples were predicted as VALID!"
    )


# ============================================================
# DISPLAY FALSE NEGATIVES
# ============================================================

print("\n==============================================")
print("VALID → INVALID ANALYSIS")
print("==============================================")

print(
    "\nNumber of VALID samples wrongly rejected:",
    len(false_negatives)
)


if len(false_negatives) > 0:

    print("\nThese VALID samples were rejected:\n")

    display_columns = [
        TARGET,
        "predicted_validity"
    ] + FEATURES

    print(
        false_negatives[
            display_columns
        ].to_string(index=False)
    )


# ============================================================
# FEATURE STATISTICS
# ============================================================

print("\n==============================================")
print("HARD-NEGATIVE FEATURE STATISTICS")
print("==============================================")


if len(false_positives) > 0:

    print(
        "\nAverage values of INVALID samples "
        "that were wrongly predicted as VALID:\n"
    )

    print(
        false_positives[
            FEATURES
        ].mean().to_string()
    )


# ============================================================
# COMPARE WITH ALL INVALID TEST DATA
# ============================================================

invalid_test = df[
    df[TARGET] == "INVALID"
].copy()


if len(invalid_test) > 0:

    print(
        "\n----------------------------------------------"
    )

    print(
        "ALL INVALID TEST DATA — AVERAGE FEATURES"
    )

    print(
        "----------------------------------------------"
    )

    print(
        invalid_test[
            FEATURES
        ].mean().to_string()
    )


# ============================================================
# SAVE COMPLETE TEST PREDICTIONS
# ============================================================

ALL_PREDICTIONS_FILE = os.path.join(
    OUTPUT_DIR,
    "test_predictions.csv"
)

df.to_csv(
    ALL_PREDICTIONS_FILE,
    index=False
)


# ============================================================
# FINAL OUTPUT
# ============================================================

print("\n==============================================")
print("STEP 5 FINISHED")
print("==============================================")

print(
    "\nHard-negative file saved:"
)

print(
    OUTPUT_FILE
)

print(
    "\nComplete prediction file saved:"
)

print(
    ALL_PREDICTIONS_FILE
)

print("\n==============================================\n")