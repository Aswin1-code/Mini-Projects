import pandas as pd
import os

# ============================================================
# STEP 1 — CREATE CLEAN MASTER VALIDATION DATASET V2
# ============================================================

# ------------------------------------------------------------
# FILE PATHS
# ------------------------------------------------------------

OLD_MASTER_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#1_Master_Dataset\master_validation_dataset.csv"

# 🔴 CHANGE THIS to the actual path of your 118 free-swing CSV
FREE_SWING_FILE = r"C:\Users\aswin\Downloads\data 1\badminton_data 118 freeSwing.csv"

OUTPUT_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#1_Master_Dataset\master_validation_dataset_v2.csv"


# ------------------------------------------------------------
# REQUIRED ML FEATURES
# ------------------------------------------------------------

REQUIRED_FEATURES = [
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


# ============================================================
# LOAD EXISTING MASTER DATASET
# ============================================================

print("\n" + "=" * 60)
print("LOADING EXISTING MASTER DATASET")
print("=" * 60)

master_df = pd.read_csv(OLD_MASTER_FILE)

# Clean column names
master_df.columns = master_df.columns.str.strip()

print(f"Existing master rows : {len(master_df)}")
print(f"Existing columns     : {list(master_df.columns)}")


# ============================================================
# LOAD FREE-SWING DATASET
# ============================================================

print("\n" + "=" * 60)
print("LOADING FREE-SWING DATASET")
print("=" * 60)

free_df = pd.read_csv(FREE_SWING_FILE)

# Clean column names
free_df.columns = free_df.columns.str.strip()

print(f"Free-swing rows : {len(free_df)}")
print(f"Columns         : {list(free_df.columns)}")


# ============================================================
# CHECK REQUIRED FEATURES
# ============================================================

print("\n" + "=" * 60)
print("CHECKING REQUIRED FEATURES")
print("=" * 60)

missing_master = [
    col for col in REQUIRED_FEATURES
    if col not in master_df.columns
]

missing_free = [
    col for col in REQUIRED_FEATURES
    if col not in free_df.columns
]

if missing_master:
    raise Exception(
        f"❌ Missing features in existing master dataset: {missing_master}"
    )

if missing_free:
    raise Exception(
        f"❌ Missing features in free-swing dataset: {missing_free}"
    )

print("✅ All 9 ML features are present in both datasets.")


# ============================================================
# CHECK VALIDITY COLUMN
# ============================================================

if "validity" not in master_df.columns:
    raise Exception(
        "❌ Existing master dataset does not contain 'validity' column."
    )


# ============================================================
# LABEL FREE-SWING DATA
# ============================================================

print("\n" + "=" * 60)
print("LABELING FREE-SWING DATA")
print("=" * 60)

# Every free swing is an INVALID swing
free_df["validity"] = "INVALID"

print("✅ All free-swing samples labeled as INVALID.")


# ============================================================
# ALIGN COLUMNS
# ============================================================

print("\n" + "=" * 60)
print("ALIGNING DATASETS")
print("=" * 60)

# Find union of columns
all_columns = list(
    dict.fromkeys(
        list(master_df.columns) +
        list(free_df.columns)
    )
)

# Add missing columns as NaN
for col in all_columns:

    if col not in master_df.columns:
        master_df[col] = pd.NA

    if col not in free_df.columns:
        free_df[col] = pd.NA

# Same column order
master_df = master_df[all_columns]
free_df = free_df[all_columns]


# ============================================================
# COMBINE DATASETS
# ============================================================

print("\n" + "=" * 60)
print("COMBINING DATASETS")
print("=" * 60)

combined_df = pd.concat(
    [master_df, free_df],
    ignore_index=True
)

print(f"Old master rows       : {len(master_df)}")
print(f"New free-swing rows   : {len(free_df)}")
print(f"--------------------------------")
print(f"Combined rows         : {len(combined_df)}")


# ============================================================
# CHECK REQUIRED FEATURES FOR MISSING VALUES
# ============================================================

print("\n" + "=" * 60)
print("CHECKING DATA QUALITY")
print("=" * 60)

missing_values = combined_df[REQUIRED_FEATURES].isnull().sum()

print("\nMissing values in ML features:")

print(missing_values)

if missing_values.sum() == 0:
    print("\n✅ No missing values in required ML features.")
else:
    print("\n⚠ Missing values detected.")


# ============================================================
# CHECK DUPLICATES
# ============================================================

duplicate_count = combined_df.duplicated().sum()

print(f"\nDuplicate rows : {duplicate_count}")

if duplicate_count == 0:
    print("✅ No duplicate rows found.")
else:
    print("⚠ Duplicate rows found.")
    print("Duplicates are NOT automatically removed.")


# ============================================================
# CLASS DISTRIBUTION
# ============================================================

print("\n" + "=" * 60)
print("FINAL CLASS DISTRIBUTION")
print("=" * 60)

class_counts = combined_df["validity"].value_counts()

print(class_counts)

valid_count = (combined_df["validity"] == "VALID").sum()
invalid_count = (combined_df["validity"] == "INVALID").sum()

print("\nVALID   :", valid_count)
print("INVALID :", invalid_count)
print("TOTAL   :", len(combined_df))


# ============================================================
# EXPECTED COUNT CHECK
# ============================================================

if valid_count == 90 and invalid_count == 418:
    print("\n✅ EXPECTED DATASET SIZE CONFIRMED")
    print("   VALID   = 90")
    print("   INVALID = 418")
    print("   TOTAL   = 508")
else:
    print("\n⚠ Counts differ from expected values.")
    print("Please inspect the source datasets.")


# ============================================================
# REORDER IMPORTANT COLUMNS
# ============================================================

preferred_order = []

# Keep timestamp if available
if "timestamp" in combined_df.columns:
    preferred_order.append("timestamp")

preferred_order += REQUIRED_FEATURES
preferred_order.append("validity")

# Add any remaining columns afterward
remaining_columns = [
    col for col in combined_df.columns
    if col not in preferred_order
]

final_columns = preferred_order + remaining_columns

combined_df = combined_df[final_columns]


# ============================================================
# SAVE CLEAN MASTER DATASET
# ============================================================

print("\n" + "=" * 60)
print("SAVING CLEAN MASTER DATASET")
print("=" * 60)

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

combined_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n✅ CLEAN MASTER DATASET CREATED")
print(f"\nSaved to:")
print(OUTPUT_FILE)


# ============================================================
# FINAL VERIFICATION
# ============================================================

print("\n" + "=" * 60)
print("FINAL VERIFICATION")
print("=" * 60)

check_df = pd.read_csv(OUTPUT_FILE)

print(f"Rows       : {len(check_df)}")
print(f"Columns    : {len(check_df.columns)}")

print("\nClass distribution:")
print(check_df["validity"].value_counts())

print("\nFirst 5 rows:")
print(check_df.head())

print("\n" + "=" * 60)
print("STEP 1 COMPLETED ✅")
print("=" * 60)