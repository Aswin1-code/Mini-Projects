import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# -------------------------------
# 1. LOAD DATA
# -------------------------------
df = pd.read_csv(r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\DataSet\w_m_s_final_dataset.csv")

# -------------------------------
# 2. CLEAN DATA
# -------------------------------
df["speed"] = pd.to_numeric(df["speed"], errors="coerce")
df["impact"] = pd.to_numeric(df["impact"], errors="coerce")
df["duration"] = pd.to_numeric(df["duration"], errors="coerce")

df = df.dropna()

# -------------------------------
# 3. LABEL CREATION (RULE SYSTEM)
# -------------------------------
def assign_label(speed, impact):
    if speed >= 52 or impact >= 43:
        return "STRONG"
    elif speed >= 43 or impact >= 35:
        return "MEDIUM"
    else:
        return "WEAK"

df["new_label"] = df.apply(lambda row: assign_label(row["speed"], row["impact"]), axis=1)

# -------------------------------
# 4. FEATURE ENGINEERING
# -------------------------------
df["power"] = df["speed"] * df["impact"]
df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)

# -------------------------------
# 5. VISUALIZATION
# -------------------------------
plt.scatter(
    df["speed"],
    df["impact"],
    c=df["new_label"].astype("category").cat.codes
)
plt.xlabel("Speed")
plt.ylabel("Impact")
plt.title("Swing Classification Visualization")
plt.show()

# -------------------------------
# 6. FEATURES & TARGET
# -------------------------------
features = ["speed", "impact", "duration", "power", "efficiency"]

X = df[features]
y = df["new_label"]

# -------------------------------
# 7. TRAIN-TEST SPLIT
# -------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# -------------------------------
# 8. MODEL TRAINING (RANDOM FOREST)
# -------------------------------
model = RandomForestClassifier(
    n_estimators=150,
    random_state=42
)

model.fit(X_train, y_train)

# -------------------------------
# 9. PREDICTION
# -------------------------------
y_pred = model.predict(X_test)

# -------------------------------
# 10. EVALUATION
# -------------------------------
print("\n🔥 ML ACCURACY:", accuracy_score(y_test, y_pred))

print("\n=== CLASSIFICATION REPORT ===")
print(classification_report(y_test, y_pred))

print("\n=== CONFUSION MATRIX ===")
print(confusion_matrix(y_test, y_pred))

# -------------------------------
# 11. CROSS VALIDATION (STABILITY CHECK)
# -------------------------------
cv_scores = cross_val_score(model, X, y, cv=5)
print("\n📊 Cross Validation Mean Score:", cv_scores.mean())

# -------------------------------
# 12. REAL-TIME STYLE PREDICTION SAMPLE
# -------------------------------
sample = pd.DataFrame([{
    "speed": 45.2,
    "impact": 38.1,
    "duration": 0.52,
}])

# auto feature generation (VERY IMPORTANT FIX)
sample["power"] = sample["speed"] * sample["impact"]
sample["efficiency"] = sample["impact"] / (sample["duration"] + 1e-6)

print("\n🚀 Prediction:", model.predict(sample[features]))

import joblib

# -------------------------------
# 13. SAVE TRAINED MODEL
# -------------------------------
model_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\ML train\swing_model.pkl"

joblib.dump(model, model_path)

print("\n💾 Model saved successfully at:", model_path)