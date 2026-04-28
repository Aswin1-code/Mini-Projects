import pandas as pd
import matplotlib.pyplot as plt
import joblib

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
for col in ["speed", "impact", "duration"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

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
plt.scatter(df["speed"], df["impact"], c=df["new_label"].astype("category").cat.codes)
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
# 8. MODEL TRAINING
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
# 11. CROSS VALIDATION
# -------------------------------
cv_scores = cross_val_score(model, X, y, cv=5)
print("\n📊 Cross Validation Mean Score:", cv_scores.mean())

# -------------------------------
# 12. SAVE MODEL + FEATURES (IMPORTANT FIX)
# -------------------------------
model_package = {
    "model": model,
    "features": features
}

model_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\ML train\swing_model.pkl"
joblib.dump(model_package, model_path)

print("\n💾 Model + features saved at:", model_path)

# -------------------------------
# 13. TEST PREDICTION (SAFE VERSION)
# -------------------------------
sample = pd.DataFrame([{
    "speed": 45.2,
    "impact": 38.1,
    "duration": 0.52
}])

# feature engineering for sample
sample["power"] = sample["speed"] * sample["impact"]
sample["efficiency"] = sample["impact"] / (sample["duration"] + 1e-6)

# load correct feature order
sample = sample[features]

prediction = model.predict(sample)

print("\n🚀 Prediction:", prediction)