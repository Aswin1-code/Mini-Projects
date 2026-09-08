# =========================================
# train_model.py
# TRAIN ML MODEL + SAVE AS PKL
# Using: w_m_s_final_dataset.csv
# =========================================

import pandas as pd
import matplotlib.pyplot as plt
import joblib

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)

# =========================================
# 1. LOAD DATASET
# =========================================

file_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\w_m_s_final_dataset.csv"

df = pd.read_csv(file_path)

print("\n===================================")
print("🏸 RAW DATASET LOADED")
print("===================================")
print(df.head())
print(f"\nTotal Rows: {len(df)}")

# =========================================
# 2. CLEAN DATA
# =========================================

required_cols = ["speed", "impact", "duration"]

for col in required_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=required_cols)

print("\n===================================")
print("✅ CLEANED DATA")
print("===================================")
print(f"Valid Rows: {len(df)}")

# =========================================
# 3. LABEL CREATION (RULE-BASED)
# =========================================

def assign_label(speed, impact):
    """
    Initial training labels based on your thresholds
    Modify if needed
    """

    if speed >= 52 or impact >= 43:
        return "STRONG"

    elif speed >= 43 or impact >= 35:
        return "MEDIUM"

    else:
        return "WEAK"


df["new_label"] = df.apply(
    lambda row: assign_label(
        row["speed"],
        row["impact"]
    ),
    axis=1
)

print("\n===================================")
print("🏷 LABEL DISTRIBUTION")
print("===================================")
print(df["new_label"].value_counts())

# =========================================
# 4. FEATURE ENGINEERING
# =========================================

df["power"] = df["speed"] * df["impact"]

df["efficiency"] = (
    df["impact"] /
    (df["duration"] + 1e-6)
)

print("\n===================================")
print("⚙ FEATURES CREATED")
print("===================================")

print(df[[
    "speed",
    "impact",
    "duration",
    "power",
    "efficiency",
    "new_label"
]].head())

# =========================================
# 5. OPTIONAL VISUALIZATION
# =========================================

plt.figure(figsize=(8, 6))

plt.scatter(
    df["speed"],
    df["impact"],
    c=df["new_label"].astype("category").cat.codes
)

plt.xlabel("Speed")
plt.ylabel("Impact")
plt.title("Swing Classification Visualization")

plt.grid(True)
plt.show()

# =========================================
# 6. FEATURES + TARGET
# =========================================

features = [
    "speed",
    "impact",
    "duration",
    "power",
    "efficiency"
]

X = df[features]
y = df["new_label"]

# =========================================
# 7. TRAIN / TEST SPLIT
# =========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\n===================================")
print("📦 DATA SPLIT DONE")
print("===================================")
print(f"Train Size: {len(X_train)}")
print(f"Test Size : {len(X_test)}")

# =========================================
# 8. TRAIN RANDOM FOREST MODEL
# =========================================

model = RandomForestClassifier(
    n_estimators=150,
    random_state=42
)

model.fit(X_train, y_train)

print("\n===================================")
print("🤖 MODEL TRAINED")
print("===================================")

# =========================================
# 9. PREDICTION
# =========================================

y_pred = model.predict(X_test)

# =========================================
# 10. EVALUATION
# =========================================

print("\n===================================")
print("🔥 ML ACCURACY")
print("===================================")

accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")

print("\n===================================")
print("📋 CLASSIFICATION REPORT")
print("===================================")

print(classification_report(y_test, y_pred))

print("\n===================================")
print("🧾 CONFUSION MATRIX")
print("===================================")

print(confusion_matrix(y_test, y_pred))

# =========================================
# 11. CROSS VALIDATION
# =========================================

cv_scores = cross_val_score(
    model,
    X,
    y,
    cv=5
)

print("\n===================================")
print("📊 CROSS VALIDATION")
print("===================================")

print("Scores:", cv_scores)
print("Mean CV Score:", cv_scores.mean())

# =========================================
# 12. SAVE MODEL AS PKL
# =========================================

model_package = {
    "model": model,
    "features": features
}

save_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\swing_model.pkl"

joblib.dump(
    model_package,
    save_path
)

print("\n===================================")
print("💾 MODEL SAVED")
print("===================================")

print("Saved at:")
print(save_path)

# =========================================
# 13. SAMPLE TEST PREDICTION
# =========================================

sample = pd.DataFrame([{
    "speed": 45.2,
    "impact": 38.1,
    "duration": 0.52
}])

# Feature engineering for sample
sample["power"] = (
    sample["speed"] *
    sample["impact"]
)

sample["efficiency"] = (
    sample["impact"] /
    (sample["duration"] + 1e-6)
)

sample = sample[features]

prediction = model.predict(sample)

print("\n===================================")
print("🚀 SAMPLE TEST PREDICTION")
print("===================================")

print(sample)
print("Prediction:", prediction[0])

print("\n✅ TRAINING COMPLETED SUCCESSFULLY")