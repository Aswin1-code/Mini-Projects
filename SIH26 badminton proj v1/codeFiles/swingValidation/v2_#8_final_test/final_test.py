import pandas as pd
import os

# =====================================================
# PATHS
# =====================================================

PREDICTIONS_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#7_Final_Evaluation\final_test_predictions_v2.csv"

OUTPUT_DIR = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\v2_#8_Final_Error_Analysis"

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
# HEADER
# =====================================================

print("=" * 70)
print("STEP 8 — FINAL TEST ERROR ANALYSIS")
print("=" * 70)

# =====================================================
# LOAD
# =====================================================

print("\n📂 Loading final test predictions...")

df = pd.read_csv(PREDICTIONS_CSV)

print(f"Rows loaded : {len(df)}")

# =====================================================
# CHECK
# =====================================================

required = FEATURES + [
    "validity",
    "predicted_validity"
]

missing = [c for c in required if c not in df.columns]

if missing:
    print("\n❌ Missing columns:")
    print(missing)
    raise SystemExit

print("✅ All required columns found.")

# =====================================================
# IDENTIFY ERRORS
# =====================================================

print("\n" + "=" * 70)
print("IDENTIFYING FINAL TEST ERRORS")
print("=" * 70)

invalid_to_valid = df[
    (df["validity"] == "INVALID") &
    (df["predicted_validity"] == "VALID")
].copy()

valid_to_invalid = df[
    (df["validity"] == "VALID") &
    (df["predicted_validity"] == "INVALID")
].copy()

all_errors = df[
    df["validity"] != df["predicted_validity"]
].copy()

print(f"\nINVALID → VALID : {len(invalid_to_valid)}")
print(f"VALID → INVALID : {len(valid_to_invalid)}")
print(f"TOTAL ERRORS    : {len(all_errors)}")

# =====================================================
# VALID TEST SAMPLES
# =====================================================

valid_test = df[
    df["validity"] == "VALID"
].copy()

invalid_test = df[
    df["validity"] == "INVALID"
].copy()

# =====================================================
# PRINT VALID TEST DATA
# =====================================================

print("\n" + "=" * 70)
print("ALL 18 VALID TEST SAMPLES")
print("=" * 70)

print(
    valid_test[
        FEATURES + ["validity", "predicted_validity"]
    ].to_string(index=False)
)

# =====================================================
# PRINT FALSE NEGATIVES
# =====================================================

print("\n" + "=" * 70)
print("FALSE NEGATIVES — VALID → INVALID")
print("=" * 70)

if len(valid_to_invalid) > 0:

    print(
        valid_to_invalid[
            FEATURES + ["validity", "predicted_validity"]
        ].to_string(index=False)
    )

else:
    print("\n🎉 No VALID → INVALID errors.")

# =====================================================
# PRINT TRUE VALID
# =====================================================

valid_correct = valid_test[
    valid_test["predicted_validity"] == "VALID"
].copy()

print("\n" + "=" * 70)
print("CORRECTLY DETECTED VALID SWINGS")
print("=" * 70)

print(f"\nCount : {len(valid_correct)}")

if len(valid_correct) > 0:

    print(
        valid_correct[
            FEATURES
        ].to_string(index=False)
    )

# =====================================================
# FEATURE DISTRIBUTION
# =====================================================

print("\n" + "=" * 70)
print("FINAL TEST FEATURE DISTRIBUTION")
print("=" * 70)

distribution = []

for feature in FEATURES:

    distribution.append({
        "feature": feature,

        "VALID_test_mean":
            valid_test[feature].mean(),

        "VALID_test_std":
            valid_test[feature].std(),

        "VALID_test_min":
            valid_test[feature].min(),

        "VALID_test_max":
            valid_test[feature].max(),

        "VALID_correct_mean":
            valid_correct[feature].mean()
            if len(valid_correct) > 0 else None,

        "VALID_error_mean":
            valid_to_invalid[feature].mean()
            if len(valid_to_invalid) > 0 else None,

        "INVALID_test_mean":
            invalid_test[feature].mean(),

        "INVALID_test_std":
            invalid_test[feature].std(),

        "INVALID_test_min":
            invalid_test[feature].min(),

        "INVALID_test_max":
            invalid_test[feature].max()
    })

distribution_df = pd.DataFrame(distribution)

print(
    distribution_df.to_string(index=False)
)

# =====================================================
# SAVE FILES
# =====================================================

false_negative_file = os.path.join(
    OUTPUT_DIR,
    "valid_predicted_as_invalid_final_v2.csv"
)

invalid_false_positive_file = os.path.join(
    OUTPUT_DIR,
    "invalid_predicted_as_valid_final_v2.csv"
)

all_errors_file = os.path.join(
    OUTPUT_DIR,
    "all_final_test_errors_v2.csv"
)

distribution_file = os.path.join(
    OUTPUT_DIR,
    "final_test_feature_distribution_v2.csv"
)

valid_test_file = os.path.join(
    OUTPUT_DIR,
    "all_valid_test_samples_v2.csv"
)

valid_to_invalid.to_csv(
    false_negative_file,
    index=False
)

invalid_to_valid.to_csv(
    invalid_false_positive_file,
    index=False
)

all_errors.to_csv(
    all_errors_file,
    index=False
)

distribution_df.to_csv(
    distribution_file,
    index=False
)

valid_test.to_csv(
    valid_test_file,
    index=False
)

# =====================================================
# SUMMARY
# =====================================================

print("\n" + "=" * 70)
print("FILES SAVED")
print("=" * 70)

print("\n❌ VALID → INVALID:")
print(false_negative_file)

print("\n❌ INVALID → VALID:")
print(invalid_false_positive_file)

print("\n❌ ALL ERRORS:")
print(all_errors_file)

print("\n📊 FEATURE DISTRIBUTION:")
print(distribution_file)

print("\n📄 ALL VALID TEST SAMPLES:")
print(valid_test_file)

print("\n" + "=" * 70)
print("STEP 8 COMPLETED ✅")
print("=" * 70)