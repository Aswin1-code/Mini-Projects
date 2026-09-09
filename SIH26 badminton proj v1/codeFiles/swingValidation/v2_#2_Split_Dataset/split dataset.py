import pandas as pd
import os

from sklearn.model_selection import train_test_split


# ============================================================
# STEP 2 — STRATIFIED TRAIN / TEST SPLIT
# ============================================================

print("\n" + "=" * 65)
print("STEP 2 — STRATIFIED TRAIN / TEST SPLIT")
print("=" * 65)


# ============================================================
# FILE PATHS
# ============================================================

MASTER_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\v2_#1_Master_Dataset\master_validation_dataset_v2.csv"
)

OUTPUT_FOLDER = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\v2_#2_Split_Dataset"
)

TRAIN_FILE = os.path.join(
    OUTPUT_FOLDER,
    "validation_train_v2.csv"
)

TEST_FILE = os.path.join(
    OUTPUT_FOLDER,
    "validation_test_v2.csv"
)


# ============================================================
# REQUIRED FEATURES
# ============================================================

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

TARGET_COLUMN = "validity"


# ============================================================
# LOAD MASTER DATASET
# ============================================================

print("\n📂 Loading master dataset...")

df = pd.read_csv(MASTER_FILE)

# Clean column names
df.columns = df.columns.str.strip()

print(f"Rows loaded    : {len(df)}")
print(f"Columns loaded : {list(df.columns)}")


# ============================================================
# BASIC VALIDATION
# ============================================================

print("\n" + "-" * 65)
print("CHECKING DATASET")
print("-" * 65)


# Check target column
if TARGET_COLUMN not in df.columns:
    raise Exception(
        f"❌ Target column '{TARGET_COLUMN}' not found."
    )


# Check required features
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

missing_count = df[REQUIRED_FEATURES + [TARGET_COLUMN]].isnull().sum()

print("\nMissing values:")

print(missing_count)

if missing_count.sum() > 0:
    raise Exception(
        "❌ Missing values detected. "
        "Fix the dataset before splitting."
    )

print("\n✅ No missing values in ML data.")


# ============================================================
# CHECK CLASS DISTRIBUTION
# ============================================================

print("\n" + "-" * 65)
print("ORIGINAL CLASS DISTRIBUTION")
print("-" * 65)

original_counts = df[TARGET_COLUMN].value_counts()

print(original_counts)

valid_count = (df[TARGET_COLUMN] == "VALID").sum()
invalid_count = (df[TARGET_COLUMN] == "INVALID").sum()

print(f"\nVALID   : {valid_count}")
print(f"INVALID : {invalid_count}")
print(f"TOTAL   : {len(df)}")


# ============================================================
# STRATIFIED 80 / 20 SPLIT
# ============================================================

print("\n" + "=" * 65)
print("CREATING STRATIFIED 80/20 SPLIT")
print("=" * 65)

train_df, test_df = train_test_split(
    df,
    test_size=0.20,
    random_state=42,
    stratify=df[TARGET_COLUMN],
    shuffle=True
)


# Reset indexes
train_df = train_df.reset_index(drop=True)
test_df = test_df.reset_index(drop=True)


# ============================================================
# PRINT TRAIN DISTRIBUTION
# ============================================================

print("\n" + "-" * 65)
print("TRAINING DATASET")
print("-" * 65)

train_counts = train_df[TARGET_COLUMN].value_counts()

print(train_counts)

train_valid = (
    train_df[TARGET_COLUMN] == "VALID"
).sum()

train_invalid = (
    train_df[TARGET_COLUMN] == "INVALID"
).sum()

print(f"\nVALID   : {train_valid}")
print(f"INVALID : {train_invalid}")
print(f"TOTAL   : {len(train_df)}")


# ============================================================
# PRINT TEST DISTRIBUTION
# ============================================================

print("\n" + "-" * 65)
print("FINAL TEST DATASET")
print("-" * 65)

test_counts = test_df[TARGET_COLUMN].value_counts()

print(test_counts)

test_valid = (
    test_df[TARGET_COLUMN] == "VALID"
).sum()

test_invalid = (
    test_df[TARGET_COLUMN] == "INVALID"
).sum()

print(f"\nVALID   : {test_valid}")
print(f"INVALID : {test_invalid}")
print(f"TOTAL   : {len(test_df)}")


# ============================================================
# VERIFY TOTALS
# ============================================================

print("\n" + "=" * 65)
print("VERIFYING SPLIT")
print("=" * 65)

if len(train_df) + len(test_df) != len(df):

    raise Exception(
        "❌ Train + Test count does not match original dataset."
    )

print(
    f"Original dataset : {len(df)}"
)

print(
    f"Training dataset : {len(train_df)}"
)

print(
    f"Test dataset     : {len(test_df)}"
)

print(
    f"Train + Test     : {len(train_df) + len(test_df)}"
)

print("\n✅ Total row count verified.")


# ============================================================
# VERIFY CLASS COUNTS
# ============================================================

print("\n" + "-" * 65)
print("VERIFYING CLASS COUNTS")
print("-" * 65)

expected_train_valid = 72
expected_train_invalid = 334

expected_test_valid = 18
expected_test_invalid = 84


if (
    train_valid == expected_train_valid
    and train_invalid == expected_train_invalid
    and test_valid == expected_test_valid
    and test_invalid == expected_test_invalid
):

    print("✅ Expected stratified distribution confirmed.")

else:

    print("⚠ Class distribution differs from expected values.")
    print("This can happen depending on split rounding.")


# ============================================================
# CHECK TRAIN / TEST OVERLAP
# ============================================================

print("\n" + "-" * 65)
print("CHECKING TRAIN / TEST OVERLAP")
print("-" * 65)

# Compare only ML feature columns
train_feature_set = set(
    map(
        tuple,
        train_df[REQUIRED_FEATURES].round(8).values
    )
)

test_feature_set = set(
    map(
        tuple,
        test_df[REQUIRED_FEATURES].round(8).values
    )
)

overlap = train_feature_set.intersection(test_feature_set)

print(
    f"Feature rows overlapping between train/test : {len(overlap)}"
)

if len(overlap) == 0:
    print("✅ No feature-level overlap detected.")
else:
    print(
        "⚠ Some identical feature vectors exist in both sets."
    )


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


# ============================================================
# SAVE TRAINING DATASET
# ============================================================

print("\n" + "=" * 65)
print("SAVING DATASETS")
print("=" * 65)

train_df.to_csv(
    TRAIN_FILE,
    index=False
)

print("\n✅ Training dataset saved:")
print(TRAIN_FILE)


# ============================================================
# SAVE FINAL TEST DATASET
# ============================================================

test_df.to_csv(
    TEST_FILE,
    index=False
)

print("\n✅ Final test dataset saved:")
print(TEST_FILE)


# ============================================================
# FINAL VERIFICATION AFTER SAVING
# ============================================================

print("\n" + "=" * 65)
print("FINAL FILE VERIFICATION")
print("=" * 65)

saved_train = pd.read_csv(TRAIN_FILE)
saved_test = pd.read_csv(TEST_FILE)


print("\nTRAIN FILE")
print("-" * 30)
print(f"Rows   : {len(saved_train)}")
print(
    saved_train[TARGET_COLUMN].value_counts()
)


print("\nTEST FILE")
print("-" * 30)
print(f"Rows   : {len(saved_test)}")
print(
    saved_test[TARGET_COLUMN].value_counts()
)


# ============================================================
# FINAL STATUS
# ============================================================

print("\n" + "=" * 65)
print("STEP 2 COMPLETED ✅")
print("=" * 65)

print("\nDataset structure:")
print("508 MASTER DATA")
print("      │")
print("      ├── 406 TRAINING DATA")
print("      │      ├── 72 VALID")
print("      │      └── 334 INVALID")
print("      │")
print("      └── 102 FINAL TEST DATA")
print("             ├── 18 VALID")
print("             └── 84 INVALID")

print("\n⚠ IMPORTANT:")
print("The 102-row final test dataset must remain untouched.")
print("Do NOT augment it.")
print("Do NOT tune the model using it.")
print("It will be used only for final evaluation.")