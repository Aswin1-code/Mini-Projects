import pandas as pd
import joblib

# =====================================================
# CONFIG PATHS
# =====================================================

CALIBRATION_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\badminton_data (3).csv"
NEW_DATA_CSV     = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\(3) complete data.csv"

THRESHOLD_FILE    = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\thresholdFile.csv"
MODEL_FILE        = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\performanceClassify ml train\swing_model.pkl"

OUTPUT_FILE       = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\final_classified_output.csv"

# =====================================================
# FEATURE ENGINEERING
# =====================================================

def add_features(df):
    df["power"] = df["speed"] * df["impact"]
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)
    return df

# =====================================================
# 1. CALIBRATION PHASE (30 SWINGS)
# =====================================================

def calibration():

    print("\n🏸 CALIBRATION PHASE STARTED")

    df = pd.read_csv(CALIBRATION_CSV)

    df = df[["speed", "impact", "duration"]].dropna()

    df = add_features(df)

    # --- Generate player-specific thresholds ---
    weak_th = df["power"].quantile(0.25)
    strong_th = df["power"].quantile(0.75)

    threshold_df = pd.DataFrame([{
        "weak_threshold": weak_th,
        "strong_threshold": strong_th,
        "avg_speed": df["speed"].mean(),
        "avg_impact": df["impact"].mean(),
        "avg_power": df["power"].mean()
    }])

    threshold_df.to_csv(THRESHOLD_FILE, index=False)

    print("\n✅ Calibration Done")
    print(threshold_df)

# =====================================================
# 2. LOAD ML MODEL
# =====================================================

def load_model():
    model_pack = joblib.load(MODEL_FILE)
    return model_pack["model"], model_pack["features"]

# =====================================================
# 3. PERFORMANCE CLASSIFICATION PHASE
# =====================================================

def classify():

    print("\n🤖 CLASSIFICATION PHASE STARTED")

    # Load new swing data
    df = pd.read_csv(NEW_DATA_CSV)
    df = df[["speed", "impact", "duration"]].dropna()

    df = add_features(df)

    # Load thresholds
    th = pd.read_csv(THRESHOLD_FILE)
    weak_th = th["weak_threshold"][0]
    strong_th = th["strong_threshold"][0]

    # Load ML model
    model, features = load_model()

    X = df[features]

    # ML prediction
    df["ml_prediction"] = model.predict(X)

    # =================================================
    # RULE-BASED CLASSIFICATION (using thresholds)
    # =================================================

    def rule_based(row):
        if row["power"] < weak_th:
            return "WEAK"
        elif row["power"] < strong_th:
            return "MEDIUM"
        else:
            return "STRONG"

    df["rule_prediction"] = df.apply(rule_based, axis=1)

    # =================================================
    # FINAL OUTPUT
    # =================================================

    print("\n📊 SAMPLE OUTPUT")
    print(df.head())

    print("\n📊 ML Prediction Count")
    print(df["ml_prediction"].value_counts())

    print("\n📊 Rule-Based Prediction Count")
    print(df["rule_prediction"].value_counts())

    df.to_csv(OUTPUT_FILE, index=False)

    print("\n💾 FINAL OUTPUT SAVED:", OUTPUT_FILE)

# =====================================================
# 4. MAIN CONTROLLER
# =====================================================

if __name__ == "__main__":

    print("\n==============================")
    print("🏸 SMART BADMINTON SYSTEM")
    print("==============================")

    print("\n1. Calibration (30 swings)")
    print("2. Classification (100+ swings)")

    choice = input("\nEnter choice: ")

    if choice == "1":
        calibration()

    elif choice == "2":
        classify()

    else:
        print("Invalid choice")