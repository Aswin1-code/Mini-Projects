import pandas as pd
import os

# =====================================================
# PATHS
# =====================================================

ORIGINAL_TRAIN_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#2_Split_Dataset\validation_train_v2.csv"

AUGMENTED_TRAIN_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#3_Augmented_Dataset\validation_train_augmented_v2.csv"

FINAL_TEST_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#2_Split_Dataset\validation_test_v2.csv"

OUTPUT_DIR = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#9_VALID_Coverage_Analysis"

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

# =====================================================
# LOAD
# =====================================================

print("=" * 70)
print("STEP 9 — VALID DATA COVERAGE ANALYSIS")
print("=" * 70)

original = pd.read_csv(ORIGINAL_TRAIN_CSV)
augmented = pd.read_csv(AUGMENTED_TRAIN_CSV)
test = pd.read_csv(FINAL_TEST_CSV)

# Only VALID
original_valid = original[
    original["validity"] == "VALID"
].copy()

augmented_valid = augmented[
    augmented["validity"] == "VALID"
].copy()

test_valid = test[
    test["validity"] == "VALID"
].copy()

# =====================================================
# COUNTS
# =====================================================

print("\n" + "=" * 70)
print("VALID SAMPLE COUNTS")
print("=" * 70)

print(f"\nOriginal training VALID : {len(original_valid)}")
print(f"Augmented training VALID: {len(augmented_valid)}")
print(f"Final test VALID        : {len(test_valid)}")

# =====================================================
# DISTRIBUTIONS
# =====================================================

print("\n" + "=" * 70)
print("VALID FEATURE DISTRIBUTION")
print("=" * 70)

rows = []

for feature in FEATURES:

    rows.append({
        "feature": feature,

        "original_train_mean":
            original_valid[feature].mean(),

        "original_train_std":
            original_valid[feature].std(),

        "original_train_min":
            original_valid[feature].min(),

        "original_train_max":
            original_valid[feature].max(),

        "augmented_train_mean":
            augmented_valid[feature].mean(),

        "augmented_train_std":
            augmented_valid[feature].std(),

        "augmented_train_min":
            augmented_valid[feature].min(),

        "augmented_train_max":
            augmented_valid[feature].max(),

        "final_test_mean":
            test_valid[feature].mean(),

        "final_test_std":
            test_valid[feature].std(),

        "final_test_min":
            test_valid[feature].min(),

        "final_test_max":
            test_valid[feature].max()
    })

distribution = pd.DataFrame(rows)

print(
    distribution.to_string(index=False)
)

# =====================================================
# RANGE COVERAGE
# =====================================================

print("\n" + "=" * 70)
print("TEST VALUES OUTSIDE ORIGINAL VALID TRAINING RANGE")
print("=" * 70)

coverage_rows = []

for feature in FEATURES:

    train_min = original_valid[feature].min()
    train_max = original_valid[feature].max()

    outside = test_valid[
        (test_valid[feature] < train_min) |
        (test_valid[feature] > train_max)
    ]

    coverage_rows.append({
        "feature": feature,
        "train_min": train_min,
        "train_max": train_max,
        "test_values_outside_range": len(outside),
        "test_total": len(test_valid),
        "percentage_outside":
            (len(outside) / len(test_valid)) * 100
    })

coverage = pd.DataFrame(coverage_rows)

print(
    coverage.to_string(index=False)
)

# =====================================================
# TEST SAMPLES OUTSIDE MULTIPLE RANGES
# =====================================================

print("\n" + "=" * 70)
print("FINAL TEST VALID SAMPLES")
print("=" * 70)

for index, row in test_valid.iterrows():

    outside_features = []

    for feature in FEATURES:

        train_min = original_valid[feature].min()
        train_max = original_valid[feature].max()

        if (
            row[feature] < train_min
            or
            row[feature] > train_max
        ):
            outside_features.append(feature)

    print(
        f"\nTest sample index {index}:"
    )

    print(
        f"  Outside features: "
        f"{outside_features if outside_features else 'None'}"
    )

# =====================================================
# SAVE
# =====================================================

distribution_file = os.path.join(
    OUTPUT_DIR,
    "valid_feature_distribution_comparison_v2.csv"
)

coverage_file = os.path.join(
    OUTPUT_DIR,
    "valid_test_range_coverage_v2.csv"
)

distribution.to_csv(
    distribution_file,
    index=False
)

coverage.to_csv(
    coverage_file,
    index=False
)

# =====================================================
# FINISH
# =====================================================

print("\n" + "=" * 70)
print("FILES SAVED")
print("=" * 70)

print("\n📊 Distribution:")
print(distribution_file)

print("\n📊 Range coverage:")
print(coverage_file)

print("\n" + "=" * 70)
print("STEP 9 COMPLETED ✅")
print("=" * 70)