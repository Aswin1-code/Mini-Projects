import pandas as pd
import numpy as np
import os


# ============================================================
# STEP 3 — VALID-ONLY DATA AUGMENTATION
# ============================================================

print("\n" + "=" * 70)
print("STEP 3 — VALID-ONLY DATA AUGMENTATION")
print("=" * 70)


# ============================================================
# FILE PATHS
# ============================================================

TRAIN_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\v2_#2_Split_Dataset\validation_train_v2.csv"
)

OUTPUT_FOLDER = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\v2_#3_Augmented_Dataset"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "validation_train_augmented_v2.csv"
)


# ============================================================
# ML FEATURES
# ============================================================

ACCEL_FEATURES = [
    "ax",
    "ay",
    "az"
]

GYRO_FEATURES = [
    "gx",
    "gy",
    "gz"
]

OTHER_FEATURES = [
    "speed",
    "impact",
    "duration"
]

REQUIRED_FEATURES = (
    ACCEL_FEATURES +
    GYRO_FEATURES +
    OTHER_FEATURES
)

TARGET_COLUMN = "validity"


# ============================================================
# AUGMENTATION SETTINGS
# ============================================================

AUGMENTATIONS_PER_VALID = 2

ACCEL_NOISE_STD = 0.02
GYRO_NOISE_STD = 0.02
SPEED_NOISE_STD = 0.015
IMPACT_NOISE_STD = 0.015
DURATION_NOISE_STD = 0.02

RANDOM_SEED = 42


# ============================================================
# LOAD TRAINING DATA
# ============================================================

print("\n📂 Loading training dataset...")

df = pd.read_csv(TRAIN_FILE)

df.columns = df.columns.str.strip()

print(f"Training rows loaded : {len(df)}")


# ============================================================
# VALIDATE DATASET
# ============================================================

print("\n" + "-" * 70)
print("CHECKING DATASET")
print("-" * 70)

if TARGET_COLUMN not in df.columns:
    raise Exception(
        f"❌ Target column '{TARGET_COLUMN}' not found."
    )

missing_features = [
    feature
    for feature in REQUIRED_FEATURES
    if feature not in df.columns
]

if missing_features:
    raise Exception(
        f"❌ Missing required features: {missing_features}"
    )

print("✅ Target column found.")
print("✅ All 9 ML features found.")


# ============================================================
# CHECK MISSING VALUES
# ============================================================

missing_values = df[
    REQUIRED_FEATURES + [TARGET_COLUMN]
].isnull().sum()

print("\nMissing values:")
print(missing_values)

if missing_values.sum() > 0:
    raise Exception(
        "❌ Missing values detected. "
        "Fix the training dataset before augmentation."
    )

print("\n✅ No missing values.")


# ============================================================
# ORIGINAL CLASS DISTRIBUTION
# ============================================================

print("\n" + "-" * 70)
print("ORIGINAL TRAINING DISTRIBUTION")
print("-" * 70)

original_counts = df[TARGET_COLUMN].value_counts()

print(original_counts)

original_valid = (
    df[TARGET_COLUMN] == "VALID"
).sum()

original_invalid = (
    df[TARGET_COLUMN] == "INVALID"
).sum()

print(f"\nVALID   : {original_valid}")
print(f"INVALID : {original_invalid}")
print(f"TOTAL   : {len(df)}")


# ============================================================
# SEPARATE VALID AND INVALID
# ============================================================

valid_df = df[
    df[TARGET_COLUMN] == "VALID"
].copy()

invalid_df = df[
    df[TARGET_COLUMN] == "INVALID"
].copy()

valid_df = valid_df.reset_index(drop=True)
invalid_df = invalid_df.reset_index(drop=True)


print("\n" + "-" * 70)
print("AUGMENTATION SOURCE")
print("-" * 70)

print(f"VALID samples to augment   : {len(valid_df)}")
print(f"INVALID samples untouched  : {len(invalid_df)}")


# ============================================================
# RANDOM NUMBER GENERATOR
# ============================================================

rng = np.random.default_rng(RANDOM_SEED)


# ============================================================
# CREATE AUGMENTED VALID SAMPLES
# ============================================================

print("\n" + "=" * 70)
print("GENERATING AUGMENTED VALID SAMPLES")
print("=" * 70)

augmented_rows = []


for index, row in valid_df.iterrows():

    # --------------------------------------------------------
    # Keep original VALID sample
    # --------------------------------------------------------

    for aug_number in range(
        AUGMENTATIONS_PER_VALID
    ):

        new_row = row.copy()

        # ----------------------------------------------------
        # Add small noise to acceleration
        # ----------------------------------------------------

        for feature in ACCEL_FEATURES:

            new_row[feature] = (
                float(row[feature])
                +
                rng.normal(
                    loc=0.0,
                    scale=ACCEL_NOISE_STD
                )
            )

        # ----------------------------------------------------
        # Add small noise to gyroscope
        # ----------------------------------------------------

        for feature in GYRO_FEATURES:

            new_row[feature] = (
                float(row[feature])
                +
                rng.normal(
                    loc=0.0,
                    scale=GYRO_NOISE_STD
                )
            )

        # ----------------------------------------------------
        # Add noise to speed
        # ----------------------------------------------------

        new_row["speed"] = (
            float(row["speed"])
            +
            rng.normal(
                loc=0.0,
                scale=SPEED_NOISE_STD
            )
        )

        # ----------------------------------------------------
        # Add noise to impact
        # ----------------------------------------------------

        new_row["impact"] = (
            float(row["impact"])
            +
            rng.normal(
                loc=0.0,
                scale=IMPACT_NOISE_STD
            )
        )

        # ----------------------------------------------------
        # Add noise to duration
        # ----------------------------------------------------

        new_row["duration"] = (
            float(row["duration"])
            +
            rng.normal(
                loc=0.0,
                scale=DURATION_NOISE_STD
            )
        )

        # ----------------------------------------------------
        # Prevent physically invalid negative values
        # ----------------------------------------------------

        new_row["speed"] = max(
            0.0,
            new_row["speed"]
        )

        new_row["impact"] = max(
            0.0,
            new_row["impact"]
        )

        new_row["duration"] = max(
            0.01,
            new_row["duration"]
        )

        # ----------------------------------------------------
        # Keep label explicitly VALID
        # ----------------------------------------------------

        new_row[TARGET_COLUMN] = "VALID"

        # ----------------------------------------------------
        # Timestamp is not used for augmentation
        # ----------------------------------------------------

        if "timestamp" in new_row.index:
            new_row["timestamp"] = row["timestamp"]

        augmented_rows.append(new_row)


# ============================================================
# CONVERT AUGMENTED DATA TO DATAFRAME
# ============================================================

augmented_valid_df = pd.DataFrame(
    augmented_rows
)

augmented_valid_df = augmented_valid_df.reset_index(
    drop=True
)


print(
    f"\nGenerated augmented VALID samples : "
    f"{len(augmented_valid_df)}"
)


# ============================================================
# COMBINE ORIGINAL + AUGMENTED
# ============================================================

print("\n" + "=" * 70)
print("BUILDING FINAL AUGMENTED TRAINING DATASET")
print("=" * 70)

# Original VALID samples
# + synthetic VALID samples
# + original INVALID samples

final_train_df = pd.concat(
    [
        valid_df,
        augmented_valid_df,
        invalid_df
    ],
    ignore_index=True
)


# ============================================================
# SHUFFLE DATASET
# ============================================================

final_train_df = final_train_df.sample(
    frac=1.0,
    random_state=RANDOM_SEED
).reset_index(drop=True)


# ============================================================
# FINAL CLASS DISTRIBUTION
# ============================================================

print("\n" + "-" * 70)
print("FINAL AUGMENTED DISTRIBUTION")
print("-" * 70)

final_counts = final_train_df[
    TARGET_COLUMN
].value_counts()

print(final_counts)

final_valid = (
    final_train_df[TARGET_COLUMN] == "VALID"
).sum()

final_invalid = (
    final_train_df[TARGET_COLUMN] == "INVALID"
).sum()

final_total = len(final_train_df)

print(f"\nVALID   : {final_valid}")
print(f"INVALID : {final_invalid}")
print(f"TOTAL   : {final_total}")


# ============================================================
# VERIFY EXPECTED COUNTS
# ============================================================

print("\n" + "-" * 70)
print("VERIFYING EXPECTED COUNTS")
print("-" * 70)

expected_valid = (
    original_valid
    +
    original_valid * AUGMENTATIONS_PER_VALID
)

expected_invalid = original_invalid

expected_total = (
    expected_valid +
    expected_invalid
)

print(f"Expected VALID   : {expected_valid}")
print(f"Actual VALID     : {final_valid}")

print(f"\nExpected INVALID : {expected_invalid}")
print(f"Actual INVALID   : {final_invalid}")

print(f"\nExpected TOTAL   : {expected_total}")
print(f"Actual TOTAL     : {final_total}")


if (
    final_valid == expected_valid
    and
    final_invalid == expected_invalid
    and
    final_total == expected_total
):

    print("\n✅ AUGMENTATION COUNT VERIFIED.")

else:

    raise Exception(
        "❌ Augmentation count does not match expected values."
    )


# ============================================================
# CHECK MISSING VALUES AFTER AUGMENTATION
# ============================================================

print("\n" + "-" * 70)
print("CHECKING AUGMENTED DATA QUALITY")
print("-" * 70)

final_missing = final_train_df[
    REQUIRED_FEATURES + [TARGET_COLUMN]
].isnull().sum()

print("\nMissing values:")
print(final_missing)

if final_missing.sum() == 0:
    print("\n✅ No missing values after augmentation.")

else:
    raise Exception(
        "❌ Missing values detected after augmentation."
    )


# ============================================================
# CHECK DUPLICATES
# ============================================================

duplicate_count = final_train_df.duplicated().sum()

print(
    f"\nDuplicate rows : {duplicate_count}"
)

if duplicate_count == 0:

    print("✅ No exact duplicate rows.")

else:

    print(
        "⚠ Duplicate rows detected."
    )


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


# ============================================================
# SAVE AUGMENTED DATASET
# ============================================================

print("\n" + "=" * 70)
print("SAVING AUGMENTED TRAINING DATASET")
print("=" * 70)

final_train_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n✅ Augmented training dataset saved:")
print(OUTPUT_FILE)


# ============================================================
# RELOAD AND VERIFY
# ============================================================

print("\n" + "=" * 70)
print("FINAL FILE VERIFICATION")
print("=" * 70)

saved_df = pd.read_csv(
    OUTPUT_FILE
)

print(
    f"\nRows loaded from saved file : "
    f"{len(saved_df)}"
)

print("\nClass distribution:")

print(
    saved_df[TARGET_COLUMN].value_counts()
)


# ============================================================
# FINAL STATUS
# ============================================================

print("\n" + "=" * 70)
print("STEP 3 COMPLETED ✅")
print("=" * 70)

print("\nTraining pipeline so far:")

print("""
508 MASTER DATA
      │
      ├── 406 TRAIN
      │      ├── 72 VALID
      │      └── 334 INVALID
      │
      └── 102 FINAL TEST
             ├── 18 VALID
             └── 84 INVALID

406 TRAIN
      │
      ├── Original VALID     = 72
      ├── Augmented VALID    = 144
      │
      └── Final VALID        = 216
               +
          INVALID            = 334
               │
               ▼
      AUGMENTED TRAIN = 550
""")

print("\n⚠ IMPORTANT:")
print("The 102-row final test dataset was NOT touched.")
print("Only VALID samples from the training set were augmented.")
print("The INVALID training samples remain unchanged.")