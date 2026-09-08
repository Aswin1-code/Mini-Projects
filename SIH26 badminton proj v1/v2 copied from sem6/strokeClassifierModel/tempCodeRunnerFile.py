import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# =========================================
# FILE PATH
# =========================================

DATASET_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\strokeClassifierModel\stroke_data\realistic_badminton_stroke_dataset.csv"
MODEL_SAVE_PATH = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\strokeClassifierModel\stroke classifier pkl\stroke_model.pkl"

# =========================================
# LOAD DATASET
# =========================================

print("🏸 Loading Stroke Dataset...")

df = pd.read_csv(DATASET_FILE)

print("\nDataset Shape:")
print(df.shape)

print("\nClasses:")
print(df["stroke"].value_counts())

# =========================================
# FEATURES + LABEL
# =========================================

features = [
    "ax", "ay", "az",
    "gx", "gy", "gz",
    "speed", "impact", "duration",
    "acc_mag", "gyro_mag",
    "peak_acc", "peak_gyro",
    "energy"
]

X = df[features]
y = df["stroke"]

# =========================================
# TRAIN TEST SPLIT
# =========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# =========================================
# MODEL TRAINING
# =========================================

print("\n🔥 Training Stroke Classification Model...")

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=12,
    random_state=42
)

model.fit(X_train, y_train)

# =========================================
# EVALUATION
# =========================================

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\n===================================")
print("🎯 STROKE MODEL ACCURACY")
print("===================================")

print(f"Accuracy: {accuracy:.4f}")

print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))

# =========================================
# SAVE MODEL
# =========================================

model_pack = {
    "model": model,
    "features": features
}

joblib.dump(model_pack, MODEL_SAVE_PATH)

print("\n✅ Stroke Classification Model Saved!")
print(MODEL_SAVE_PATH)