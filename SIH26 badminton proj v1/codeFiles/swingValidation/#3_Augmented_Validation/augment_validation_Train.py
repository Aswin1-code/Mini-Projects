import pandas as pd
import numpy as np
import os

# ============================================================
# STEP 3 — VALIDATION TRAINING DATA AUGMENTATION
# ============================================================
#
# PURPOSE:
#   Increase the diversity of VALID training samples.
#
# IMPORTANT:
#   - Only TRAINING data is used.
#   - TEST data is NOT touched.
#   - INVALID samples are kept unchanged.
#   - We do NOT simply duplicate rows.
#
# ============================================================


# ============================================================
# FILE PATHS
# ============================================================

TRAIN_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\dataset_swingValidation\#2_Split_validation"
    r"\validation_train.csv"
)

OUTPUT_DIR = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\dataset_swingValidation\#3_Augmented_validation"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "validation_train_augmented.csv"
)


# ============================================================
# RANDOM SEED
# ============================================================

np.random.seed(42)


# ============================================================
# FEATURES USED BY SWING VALIDATION MODEL
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
# AUGMENTATION SETTINGS
# ============================================================

# Number of augmented versions generated for each VALID sample.

AUGMENTATIONS_PER_VALID = 2


# Small realistic variation percentages.
#
# These are deliberately conservative.
# We don't want to create unrealistic badminton swings.

NOISE_PERCENT = {
    "ax": 0.02,
    "ay": 0.02,
    "az": 0.02,

    "gx": 0.02,
    "gy": 0.02,
    "gz": 0.02,

    "speed": 0.015,
    "impact": 0.015,
    "duration": 0.02
}


# ============================================================
# LOAD TRAINING DATA
# ============================================================

print("\n==============================================")
print("STEP 3 — VALID TRAINING DATA AUGMENTATION")
print("==============================================")

print("\nLoading training dataset...")

df = pd.read_csv(TRAIN_FILE)

print("Original training shape:", df.shape)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = FEATURES + [TARGET]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"\nERROR: Missing columns:\n{missing_columns}"
    )


# ============================================================
# CLEAN NUMERIC FEATURES
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
# SHOW ORIGINAL CLASS DISTRIBUTION
# ============================================================

print("\n----------------------------------------------")
print("ORIGINAL TRAINING DISTRIBUTION")
print("----------------------------------------------")

print(
    df[TARGET]
    .value_counts()
    .to_string()
)


# ============================================================
# SEPARATE VALID AND INVALID
# ============================================================

valid_df = df[
    df[TARGET].astype(str).str.upper() == "VALID"
].copy()

invalid_df = df[
    df[TARGET].astype(str).str.upper() == "INVALID"
].copy()


print("\nVALID samples   :", len(valid_df))
print("INVALID samples :", len(invalid_df))


# ============================================================
# FUNCTION: AUGMENT ONE VALID SAMPLE
# ============================================================

def augment_sample(row):
    """
    Create one realistic variation of a VALID swing.

    Each feature receives small Gaussian noise.

    Example:
        speed = 8.20

    may become:

        8.18
        8.23

    The label remains VALID.
    """

    new_row = row.copy()

    for feature in FEATURES:

        original_value = float(row[feature])

        # Absolute noise magnitude based on feature value.
        #
        # abs(value) + 1e-6 prevents zero-value problems.

        noise_scale = (
            abs(original_value)
            * NOISE_PERCENT[feature]
        )

        noise = np.random.normal(
            loc=0.0,
            scale=noise_scale
        )

        new_value = original_value + noise

        # ----------------------------------------------------
        # Physical sanity protection
        # ----------------------------------------------------

        # Duration cannot be negative.
        if feature == "duration":
            new_value = max(new_value, 0.01)

        # Speed and impact cannot be negative.
        if feature in ["speed", "impact"]:
            new_value = max(new_value, 0.0)

        new_row[feature] = new_value

    # Keep label unchanged.
    new_row[TARGET] = "VALID"

    return new_row


# ============================================================
# GENERATE AUGMENTED VALID SAMPLES
# ============================================================

print("\n----------------------------------------------")
print("GENERATING AUGMENTED VALID SAMPLES")
print("----------------------------------------------")

augmented_rows = []

for _, row in valid_df.iterrows():

    for _ in range(AUGMENTATIONS_PER_VALID):

        augmented_row = augment_sample(row)

        augmented_rows.append(
            augmented_row
        )


augmented_valid_df = pd.DataFrame(
    augmented_rows
)


print(
    "Generated augmented VALID samples:",
    len(augmented_valid_df)
)


# ============================================================
# COMBINE DATA
# ============================================================

# Original VALID samples
# +
# Augmented VALID samples
# +
# Original INVALID samples

final_df = pd.concat(
    [
        valid_df,
        augmented_valid_df,
        invalid_df
    ],
    ignore_index=True
)


# ============================================================
# REMOVE EXACT DUPLICATES
# ============================================================

before_duplicates = len(final_df)

final_df = final_df.drop_duplicates(
    subset=FEATURES + [TARGET]
).reset_index(drop=True)

duplicates_removed = (
    before_duplicates - len(final_df)
)


# ============================================================
# SHUFFLE DATASET
# ============================================================

final_df = final_df.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# SAVE DATASET
# ============================================================

final_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# FINAL REPORT
# ============================================================

print("\n==============================================")
print("AUGMENTATION COMPLETE")
print("==============================================")

print("\nOriginal VALID       :", len(valid_df))
print("Augmented VALID      :", len(augmented_valid_df))
print("Original INVALID     :", len(invalid_df))
print("Duplicates removed   :", duplicates_removed)

print("\n----------------------------------------------")
print("FINAL TRAINING DATA")
print("----------------------------------------------")

valid_count = (
    final_df[TARGET]
    .astype(str)
    .str.upper()
    .eq("VALID")
    .sum()
)

invalid_count = (
    final_df[TARGET]
    .astype(str)
    .str.upper()
    .eq("INVALID")
    .sum()
)

print("VALID   :", valid_count)
print("INVALID :", invalid_count)
print("TOTAL   :", len(final_df))

print("\n----------------------------------------------")
print("CLASS DISTRIBUTION")
print("----------------------------------------------")

print(
    final_df[TARGET]
    .value_counts()
    .to_string()
)

print("\n----------------------------------------------")
print("SAVED FILE")
print("----------------------------------------------")

print(OUTPUT_FILE)

print("\n==============================================")
print("STEP 3 FINISHED")
print("==============================================\n")