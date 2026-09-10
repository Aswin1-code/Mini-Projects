import pandas as pd
import os

# ============================================================
# CONFIGURATION
# ============================================================

DATASET_FOLDER = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\sih\swingValidation\dataset_swingValidation"

OUTPUT_FILE = os.path.join(
    DATASET_FOLDER,
    "combined_validation_dataset.csv"
)

# ------------------------------------------------------------
# Original files
# Change filenames here if yours are different
# ------------------------------------------------------------

FILES = {
    "VALID_WEAK":   "valid_weak.csv",
    "VALID_MEDIUM": "valid_medium.csv",
    "VALID_STRONG": "valid_strong.csv",

    "INVALID_WEAK":   "invalid_weak.csv",
    "INVALID_MEDIUM": "invalid_medium.csv",
    "INVALID_STRONG": "invalid_strong.csv"
}

# ============================================================
# LOAD DATASETS
# ============================================================

datasets = {}

for label, filename in FILES.items():

    filepath = os.path.join(DATASET_FOLDER, filename)

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        raise FileNotFoundError(filepath)

    df = pd.read_csv(filepath)

    datasets[label] = df

    print(f"{label:20s} → {len(df)} samples")


# ============================================================
# CHECK REQUIRED COLUMN
# ============================================================

required_columns = [
    "sno",
    "timestamp",
    "swing_count",
    "ax",
    "ay",
    "az",
    "gx",
    "gy",
    "gz",
    "speed",
    "impact",
    "duration",
    "validity",
    "stroke_type",
    "intensity"
]

for name, df in datasets.items():

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        print(f"\n❌ {name} is missing columns:")
        print(missing)
        raise ValueError("Column mismatch found.")


# ============================================================
# FIND BALANCED SAMPLE COUNT
# ============================================================

# We need the same number from:
#
# VALID   → WEAK / MEDIUM / STRONG
# INVALID → WEAK / MEDIUM / STRONG
#
# The smallest group decides the final count.

minimum_count = min(
    len(df)
    for df in datasets.values()
)

print("\n==========================================")
print("BALANCING DATASET")
print("==========================================")

print(f"Smallest available group = {minimum_count}")


# ============================================================
# SELECT BALANCED SAMPLES
# ============================================================

balanced_parts = []

for name, df in datasets.items():

    # Randomly select the same number from every group.
    #
    # random_state makes the selection reproducible.
    selected = df.sample(
        n=minimum_count,
        random_state=42
    ).copy()

    balanced_parts.append(selected)

    print(
        f"{name:20s} → selected {len(selected)} samples"
    )


# ============================================================
# COMBINE EVERYTHING
# ============================================================

combined_df = pd.concat(
    balanced_parts,
    ignore_index=True
)


# ============================================================
# SHUFFLE FINAL DATASET
# ============================================================

combined_df = combined_df.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)


# ============================================================
# SAVE
# ============================================================

combined_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# FINAL REPORT
# ============================================================

print("\n==========================================")
print("FINAL DATASET")
print("==========================================")

print(f"Total samples : {len(combined_df)}")

print("\nValidity distribution:")
print(
    combined_df["validity"]
    .value_counts()
)

print("\nIntensity distribution:")
print(
    combined_df["intensity"]
    .value_counts()
)

print("\nValidity + Intensity:")
print(
    pd.crosstab(
        combined_df["validity"],
        combined_df["intensity"]
    )
)

print("\n==========================================")
print("DATASET CREATED SUCCESSFULLY")
print("==========================================")

print(f"\nSaved to:")
print(OUTPUT_FILE)