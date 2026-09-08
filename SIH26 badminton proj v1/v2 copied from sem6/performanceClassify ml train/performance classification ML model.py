# =========================================
# classify_performance.py
# WEAK / MEDIUM / STRONG CLASSIFICATION
# ML + CALIBRATION HYBRID SYSTEM
# =========================================

import pandas as pd
import joblib

# =========================================
# 1. LOAD NEW PLAYER CSV DATA
# =========================================

file_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\(3) complete data.csv"
df = pd.read_csv(file_path)

print("\n===================================")
print("🏸 NEW PLAYER DATA LOADED")
print("===================================")
print(df.head())
print(f"\nTotal Rows: {len(df)}")

# =========================================
# 2. LOAD CALIBRATION THRESHOLDS
# =========================================

threshold_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\player_thresholds2.csv"
threshold_df = pd.read_csv(threshold_path)

weak_th = threshold_df["weak_threshold"].values[0]
strong_th = threshold_df["strong_threshold"].values[0]

print("\n===================================")
print("📏 THRESHOLDS LOADED")
print("===================================")
print(f"Weak Threshold   : {weak_th:.2f}")
print(f"Strong Threshold : {strong_th:.2f}")

# =========================================
# 3. CLEAN DATA
# =========================================

required_cols = ["speed", "impact", "duration"]

for col in required_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=required_cols)

if len(df) == 0:
    print("❌ No valid swing data found")
    exit()

print("\n===================================")
print("✅ CLEANED DATA")
print("===================================")
print(f"Valid Rows: {len(df)}")

# =========================================
# 4. FEATURE ENGINEERING
# =========================================

df["power"] = df["speed"] * df["impact"]

df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)

print("\n===================================")
print("⚙ FEATURES CREATED")
print("===================================")

print(df[["speed", "impact", "duration", "power", "efficiency"]].head())

# =========================================
# 5. LOAD TRAINED ML MODEL
# =========================================

model_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\swing_model.pkl"

model_package = joblib.load(model_path)

model = model_package["model"]
features = model_package["features"]

print("\n===================================")
print("🤖 MODEL LOADED")
print("===================================")
print("Features used:", features)

# =========================================
# 6. SAFETY CHECK (VERY IMPORTANT)
# =========================================

missing = [f for f in features if f not in df.columns]

if missing:
    print("❌ Missing features in dataset:", missing)
    exit()

# =========================================
# 7. PREPARE INPUT
# =========================================

X = df[features]

# =========================================
# 8. ML PREDICTION
# =========================================

df["ml_prediction"] = model.predict(X)

# =========================================
# 9. RULE-BASED CLASSIFICATION (USING THRESHOLDS)
# =========================================

def rule_classify(power):
    if power < weak_th:
        return "WEAK"
    elif power > strong_th:
        return "STRONG"
    else:
        return "MEDIUM"

df["rule_prediction"] = df["power"].apply(rule_classify)

# =========================================
# 10. DISPLAY RESULTS
# =========================================

print("\n===================================")
print("🏸 CLASSIFICATION RESULTS")
print("===================================")

print(df[[
    "speed",
    "impact",
    "duration",
    "power",
    "efficiency",
    "ml_prediction",
    "rule_prediction"
]].head(20))

# =========================================
# 11. SUMMARY
# =========================================

print("\n===================================")
print("📊 ML PREDICTION SUMMARY")
print("===================================")

summary = df["ml_prediction"].value_counts()

for label, count in summary.items():
    print(f"{label} : {count}")

# =========================================
# 12. BEST & WORST SWING ANALYSIS
# =========================================

best_idx = df["power"].idxmax()
worst_idx = df["power"].idxmin()

best = df.loc[best_idx]
worst = df.loc[worst_idx]

print("\n===================================")
print("🔥 BEST SWING")
print("===================================")

print(f"Speed      : {best['speed']:.2f}")
print(f"Impact     : {best['impact']:.2f}")
print(f"Duration   : {best['duration']:.2f}")
print(f"Power      : {best['power']:.2f}")
print(f"ML Class   : {best['ml_prediction']}")
print(f"Rule Class : {best['rule_prediction']}")

print("\n===================================")
print("❄ WORST SWING")
print("===================================")

print(f"Speed      : {worst['speed']:.2f}")
print(f"Impact     : {worst['impact']:.2f}")
print(f"Duration   : {worst['duration']:.2f}")
print(f"Power      : {worst['power']:.2f}")
print(f"ML Class   : {worst['ml_prediction']}")
print(f"Rule Class : {worst['rule_prediction']}")

# =========================================
# 13. SAVE OUTPUT
# =========================================

save_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\classified_output.csv"

df.to_csv(save_path, index=False)

print("\n===================================")
print("💾 OUTPUT SAVED")
print("===================================")
print(save_path)

print("\n✅ CLASSIFICATION COMPLETED SUCCESSFULLY")