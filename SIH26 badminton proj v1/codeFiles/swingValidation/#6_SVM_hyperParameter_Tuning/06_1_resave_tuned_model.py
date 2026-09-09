import pandas as pd
import joblib
import os

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


# =====================================================
# FILE PATHS
# =====================================================

TRAIN_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\dataset_swingValidation\#3_Augmented_validation"
    r"\validation_train_augmented.csv"
)

MODEL_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\swingValidation"
    r"\#6_SVM_hyperParameter_Tuning"
    r"\swing_validation_model_tuned.pkl"
)


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

TARGET = "validity"


# =====================================================
# LOAD TRAINING DATA
# =====================================================

print("\n=====================================================")
print(" STEP 6.1 - REBUILD TUNED SVM MODEL")
print("=====================================================\n")

df = pd.read_csv(TRAIN_FILE)

print("Training dataset shape:", df.shape)

print("\nClass distribution:")
print(df[TARGET].value_counts())


# =====================================================
# PREPARE DATA
# =====================================================

X = df[FEATURES].apply(
    pd.to_numeric,
    errors="coerce"
)

y = (
    df[TARGET]
    .astype(str)
    .str.upper()
    .str.strip()
)

valid_rows = (
    X.notna().all(axis=1) &
    y.notna()
)

X = X.loc[valid_rows]
y = y.loc[valid_rows]


# =====================================================
# BEST PARAMETERS FROM STEP 6
# =====================================================

BEST_C = 10
BEST_GAMMA = "scale"
BEST_CLASS_WEIGHT = None


print("\nUsing best configuration from Step 6:")

print("C             :", BEST_C)
print("gamma         :", BEST_GAMMA)
print("class_weight  :", BEST_CLASS_WEIGHT)


# =====================================================
# BUILD MODEL
# =====================================================

model = Pipeline([
    (
        "scaler",
        StandardScaler()
    ),

    (
        "svm",
        SVC(
            kernel="rbf",
            C=BEST_C,
            gamma=BEST_GAMMA,
            class_weight=BEST_CLASS_WEIGHT
        )
    )
])


# =====================================================
# TRAIN
# =====================================================

print("\nTraining final tuned model...")

model.fit(X, y)

print("Training completed.")


# =====================================================
# SAVE MODEL
# =====================================================

joblib.dump(
    model,
    MODEL_FILE
)

print("\nModel saved successfully:")
print(MODEL_FILE)


# =====================================================
# VERIFY MODEL CAN BE LOADED
# =====================================================

print("\nVerifying saved model...")

test_model = joblib.load(
    MODEL_FILE
)

print("Model loaded successfully.")


# =====================================================
# VERIFY PREDICTION
# =====================================================

test_prediction = test_model.predict(
    X.iloc[:5]
)

print("\nTest prediction:")
print(test_prediction)


# =====================================================
# COMPLETE
# =====================================================

print("\n=====================================================")
print(" STEP 6.1 COMPLETED SUCCESSFULLY")
print("=====================================================\n")