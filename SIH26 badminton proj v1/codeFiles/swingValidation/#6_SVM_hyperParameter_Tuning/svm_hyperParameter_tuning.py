import pandas as pd
import numpy as np
import joblib
import os

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_validate


# =====================================================
# FILE PATHS
# =====================================================

TRAIN_FILE = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#3_Augmented_Validation\validation_train_augmented.csv"
)

OUTPUT_DIR = (
r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\#6_SVM_hyperParameter_Tuning"
)

MODEL_FILE = os.path.join(
    OUTPUT_DIR,
    "swing_validation_model_tuned.pkl"
)

RESULTS_FILE = os.path.join(
    OUTPUT_DIR,
    "svm_tuning_results.csv"
)


# =====================================================
# CREATE OUTPUT DIRECTORY
# =====================================================

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

TARGET = "validity"


# =====================================================
# LOAD DATA
# =====================================================

print("\n=====================================================")
print(" STEP 6 - SVM HYPERPARAMETER TUNING")
print("=====================================================\n")

df = pd.read_csv(TRAIN_FILE)

print("Training dataset shape:", df.shape)

print("\nClass distribution:")
print(df[TARGET].value_counts())


# =====================================================
# PREPARE DATA
# =====================================================

X = df[FEATURES].apply(pd.to_numeric, errors="coerce")
y = df[TARGET].astype(str).str.upper().str.strip()

valid_rows = X.notna().all(axis=1) & y.notna()

X = X.loc[valid_rows]
y = y.loc[valid_rows]


# =====================================================
# CROSS VALIDATION
# =====================================================

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)


# =====================================================
# PARAMETER COMBINATIONS
# =====================================================

PARAMETER_COMBINATIONS = [

    # -------------------------------
    # C = 1
    # -------------------------------
    {
        "C": 1,
        "gamma": "scale",
        "class_weight": None
    },
    {
        "C": 1,
        "gamma": "scale",
        "class_weight": "balanced"
    },
    {
        "C": 1,
        "gamma": "scale",
        "class_weight": {
            "INVALID": 1.5,
            "VALID": 1.0
        }
    },

    # -------------------------------
    # C = 3
    # -------------------------------
    {
        "C": 3,
        "gamma": "scale",
        "class_weight": None
    },
    {
        "C": 3,
        "gamma": "scale",
        "class_weight": "balanced"
    },
    {
        "C": 3,
        "gamma": "scale",
        "class_weight": {
            "INVALID": 1.5,
            "VALID": 1.0
        }
    },

    # -------------------------------
    # C = 10
    # -------------------------------
    {
        "C": 10,
        "gamma": "scale",
        "class_weight": None
    },
    {
        "C": 10,
        "gamma": "scale",
        "class_weight": "balanced"
    },
    {
        "C": 10,
        "gamma": "scale",
        "class_weight": {
            "INVALID": 1.5,
            "VALID": 1.0
        }
    },

    # -------------------------------
    # C = 30
    # -------------------------------
    {
        "C": 30,
        "gamma": "scale",
        "class_weight": None
    },
    {
        "C": 30,
        "gamma": "scale",
        "class_weight": "balanced"
    },
    {
        "C": 30,
        "gamma": "scale",
        "class_weight": {
            "INVALID": 1.5,
            "VALID": 1.0
        }
    },

    # -------------------------------
    # C = 100
    # -------------------------------
    {
        "C": 100,
        "gamma": "scale",
        "class_weight": None
    },
    {
        "C": 100,
        "gamma": "scale",
        "class_weight": "balanced"
    },
    {
        "C": 100,
        "gamma": "scale",
        "class_weight": {
            "INVALID": 1.5,
            "VALID": 1.0
        }
    },

    # =================================================
    # DIFFERENT GAMMA VALUES
    # =================================================

    {
        "C": 10,
        "gamma": 0.001,
        "class_weight": "balanced"
    },
    {
        "C": 10,
        "gamma": 0.005,
        "class_weight": "balanced"
    },
    {
        "C": 10,
        "gamma": 0.01,
        "class_weight": "balanced"
    },
    {
        "C": 10,
        "gamma": 0.03,
        "class_weight": "balanced"
    },
    {
        "C": 10,
        "gamma": 0.1,
        "class_weight": "balanced"
    },

    # Conservative INVALID weighting
    {
        "C": 10,
        "gamma": 0.01,
        "class_weight": {
            "INVALID": 1.5,
            "VALID": 1.0
        }
    },
    {
        "C": 10,
        "gamma": 0.03,
        "class_weight": {
            "INVALID": 1.5,
            "VALID": 1.0
        }
    },
    {
        "C": 10,
        "gamma": 0.1,
        "class_weight": {
            "INVALID": 1.5,
            "VALID": 1.0
        }
    }
]


# =====================================================
# SCORING
# =====================================================

SCORING = {
    "accuracy": "accuracy",
    "valid_recall": "recall_macro",
}


# =====================================================
# CUSTOM MANUAL SCORING
# =====================================================

results = []


print("\nStarting cross-validation...")
print("Total configurations:", len(PARAMETER_COMBINATIONS))
print()


for i, params in enumerate(PARAMETER_COMBINATIONS, start=1):

    print(
        f"[{i}/{len(PARAMETER_COMBINATIONS)}] "
        f"C={params['C']} | "
        f"gamma={params['gamma']} | "
        f"class_weight={params['class_weight']}"
    )

    model = Pipeline([
        ("scaler", StandardScaler()),

        ("svm", SVC(
            kernel="rbf",
            C=params["C"],
            gamma=params["gamma"],
            class_weight=params["class_weight"]
        ))
    ])

    fold_invalid_recall = []
    fold_valid_recall = []
    fold_accuracy = []

    for train_idx, val_idx in cv.split(X, y):

        X_train = X.iloc[train_idx]
        X_val = X.iloc[val_idx]

        y_train = y.iloc[train_idx]
        y_val = y.iloc[val_idx]

        model.fit(X_train, y_train)

        predictions = model.predict(X_val)

        # ---------------------------------------------
        # INVALID RECALL
        # ---------------------------------------------

        invalid_actual = (y_val == "INVALID")

        invalid_correct = (
            (y_val == "INVALID") &
            (predictions == "INVALID")
        )

        if invalid_actual.sum() > 0:
            invalid_recall = (
                invalid_correct.sum() /
                invalid_actual.sum()
            )
        else:
            invalid_recall = 0

        # ---------------------------------------------
        # VALID RECALL
        # ---------------------------------------------

        valid_actual = (y_val == "VALID")

        valid_correct = (
            (y_val == "VALID") &
            (predictions == "VALID")
        )

        if valid_actual.sum() > 0:
            valid_recall = (
                valid_correct.sum() /
                valid_actual.sum()
            )
        else:
            valid_recall = 0

        # ---------------------------------------------
        # ACCURACY
        # ---------------------------------------------

        accuracy = np.mean(predictions == y_val)

        fold_invalid_recall.append(invalid_recall)
        fold_valid_recall.append(valid_recall)
        fold_accuracy.append(accuracy)

    mean_invalid_recall = np.mean(fold_invalid_recall)
    mean_valid_recall = np.mean(fold_valid_recall)
    mean_accuracy = np.mean(fold_accuracy)

    # =================================================
    # PRIMARY OBJECTIVE
    # =================================================
    #
    # We care more about rejecting INVALID swings.
    #
    # 60% INVALID rejection
    # 40% VALID detection
    #

    custom_score = (
        0.60 * mean_invalid_recall +
        0.40 * mean_valid_recall
    )

    results.append({
        "C": params["C"],
        "gamma": params["gamma"],
        "class_weight": str(params["class_weight"]),

        "mean_accuracy": mean_accuracy,
        "mean_invalid_recall": mean_invalid_recall,
        "mean_valid_recall": mean_valid_recall,

        "custom_score": custom_score
    })


# =====================================================
# RESULTS DATAFRAME
# =====================================================

results_df = pd.DataFrame(results)


# =====================================================
# SORT RESULTS
# =====================================================

results_df = results_df.sort_values(
    by=[
        "custom_score",
        "mean_invalid_recall",
        "mean_valid_recall"
    ],
    ascending=False
).reset_index(drop=True)


# =====================================================
# SAVE RESULTS
# =====================================================

results_df.to_csv(
    RESULTS_FILE,
    index=False
)


# =====================================================
# DISPLAY TOP RESULTS
# =====================================================

print("\n=====================================================")
print(" TOP SVM CONFIGURATIONS")
print("=====================================================\n")

print(
    results_df.head(10).to_string(index=False)
)


# =====================================================
# BEST PARAMETERS
# =====================================================

best = results_df.iloc[0]

best_C = best["C"]
best_gamma = best["gamma"]

if best["class_weight"] == "None":
    best_class_weight = None

elif best["class_weight"] == "balanced":
    best_class_weight = "balanced"

else:
    best_class_weight = {
        "INVALID": 1.5,
        "VALID": 1.0
    }


# =====================================================
# TRAIN FINAL TUNED MODEL
# =====================================================

print("\n=====================================================")
print(" TRAINING FINAL TUNED MODEL")
print("=====================================================\n")

print("Best C:", best_C)
print("Best gamma:", best_gamma)
print("Best class weight:", best_class_weight)

final_model = Pipeline([
    ("scaler", StandardScaler()),

    ("svm", SVC(
        kernel="rbf",
        C=best_C,
        gamma=best_gamma,
        class_weight=best_class_weight
    ))
])


final_model.fit(X, y)


# =====================================================
# SAVE MODEL
# =====================================================

joblib.dump(
    final_model,
    MODEL_FILE
)


# =====================================================
# FINAL OUTPUT
# =====================================================

print("\n=====================================================")
print(" STEP 6 COMPLETED")
print("=====================================================\n")

print("Best configuration:")
print("C                  :", best_C)
print("gamma              :", best_gamma)
print("class_weight       :", best_class_weight)

print("\nCross-validation results:")
print("Accuracy            :", round(best["mean_accuracy"] * 100, 2), "%")
print(
    "INVALID rejection   :",
    round(best["mean_invalid_recall"] * 100, 2),
    "%"
)
print(
    "VALID detection     :",
    round(best["mean_valid_recall"] * 100, 2),
    "%"
)
print(
    "Custom score        :",
    round(best["custom_score"] * 100, 2),
    "%"
)

print("\nModel saved to:")
print(MODEL_FILE)

print("\nResults saved to:")
print(RESULTS_FILE)

print("\n=====================================================")