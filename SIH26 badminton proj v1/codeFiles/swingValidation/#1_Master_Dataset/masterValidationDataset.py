import pandas as pd
import os

# =====================================================
# PATHS
# =====================================================

BASE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\dataset_swingValidation"

VALID_FILES = [
    os.path.join(BASE, "valid_weak.csv"),
    os.path.join(BASE, "valid_medium.csv"),
    os.path.join(BASE, "valid_strong.csv")
]

INVALID_FILES = [
    os.path.join(BASE, "invalid_weak.csv"),
    os.path.join(BASE, "invalid_medium.csv"),
    os.path.join(BASE, "invalid_strong.csv")
]

OUTPUT_FILE = os.path.join(BASE, "master_validation_dataset.csv")

FEATURES = [
    "ax", "ay", "az",
    "gx", "gy", "gz",
    "speed", "impact", "duration"
]

# =====================================================
# LOAD VALID DATA
# =====================================================

valid_list = []

for file in VALID_FILES:
    df = pd.read_csv(file)

    df["validity"] = "VALID"

    valid_list.append(df)

    print(f"VALID loaded: {os.path.basename(file)} -> {len(df)} rows")

# =====================================================
# LOAD INVALID DATA
# =====================================================

invalid_list = []

for file in INVALID_FILES:
    df = pd.read_csv(file)

    df["validity"] = "INVALID"

    invalid_list.append(df)

    print(f"INVALID loaded: {os.path.basename(file)} -> {len(df)} rows")

# =====================================================
# COMBINE
# =====================================================

valid_df = pd.concat(valid_list, ignore_index=True)
invalid_df = pd.concat(invalid_list, ignore_index=True)

df = pd.concat(
    [valid_df, invalid_df],
    ignore_index=True
)

# =====================================================
# KEEP REQUIRED FEATURES + LABEL
# =====================================================

df = df[FEATURES + ["validity"]]

# Convert numeric columns
for col in FEATURES:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Remove missing values
before = len(df)

df = df.dropna().reset_index(drop=True)

removed_missing = before - len(df)

# Remove exact duplicate rows
before = len(df)

df = df.drop_duplicates().reset_index(drop=True)

removed_duplicates = before - len(df)

# =====================================================
# SAVE
# =====================================================

df.to_csv(OUTPUT_FILE, index=False)

# =====================================================
# SUMMARY
# =====================================================

print("\n==============================================")
print("MASTER VALIDATION DATASET")
print("==============================================")

print(f"VALID   : {(df['validity'] == 'VALID').sum()}")
print(f"INVALID : {(df['validity'] == 'INVALID').sum()}")
print(f"TOTAL   : {len(df)}")

print(f"\nMissing rows removed   : {removed_missing}")
print(f"Duplicate rows removed: {removed_duplicates}")

print("\nFeatures used:")
for feature in FEATURES:
    print(" -", feature)

print("\nSaved to:")
print(OUTPUT_FILE)

print("\n==============================================")