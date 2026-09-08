import pandas as pd
import joblib
import os

# =====================================================
# FILE PATHS
# =====================================================

CALIBRATION_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\badminton_data (3).csv"
NEW_DATA_CSV     = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\(3) complete data.csv"

THRESHOLD_FILE    = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\thresholdFile.csv"
MODEL_FILE        = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\performanceClassify ml train\swing_model.pkl"

OUTPUT_FILE       = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\end2end\finalClassifiedOp\final_classified_output2.csv"

# =====================================================
# FEATURE ENGINEERING
# =====================================================

def add_features(df):
    df["power"] = df["speed"] * df["impact"]
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)
    return df

# =====================================================
# CALIBRATION FUNCTION
# =====================================================

def calibration():

    print("\n🏸 AUTO-CALIBRATION STARTED")

    df = pd.read_csv(CALIBRATION_CSV)
    df = df[["speed", "impact", "duration"]].dropna()

    df = add_features(df)

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

    print("✅ Calibration completed")
    print(threshold_df)

# =====================================================
# LOAD MODEL
# =====================================================

def load_model():
    model_pack = joblib.load(MODEL_FILE)
    return model_pack["model"], model_pack["features"]

# =====================================================
# CLASSIFICATION FUNCTION
# =====================================================

def classify():

    print("\n🤖 AUTO-CLASSIFICATION STARTED")

    df = pd.read_csv(NEW_DATA_CSV)
    df = df[["speed", "impact", "duration"]].dropna()

    df = add_features(df)

    # Load threshold
    th = pd.read_csv(THRESHOLD_FILE)
    weak_th = th["weak_threshold"][0]
    strong_th = th["strong_threshold"][0]

    # Load ML model
    model, features = load_model()

    X = df[features]

    df["ml_prediction"] = model.predict(X)

    # Rule-based prediction
    def rule(row):
        if row["power"] < weak_th:
            return "WEAK"
        elif row["power"] < strong_th:
            return "MEDIUM"
        else:
            return "STRONG"

    df["rule_prediction"] = df.apply(rule, axis=1)

    df.to_csv(OUTPUT_FILE, index=False)

    print("💾 Output saved:", OUTPUT_FILE)

# =====================================================
# AUTO CONTROLLER (NO MANUAL INPUT)
# =====================================================

if __name__ == "__main__":

    print("\n==============================")
    print("🏸 SMART BADMINTON AUTO SYSTEM")
    print("==============================")

    # STEP 1: Check threshold file
    if not os.path.exists(THRESHOLD_FILE):

        print("\n⚠ Threshold not found → Running Calibration First")
        calibration()

    else:

        print("\n✅ Threshold already exists → Skipping Calibration")

    # STEP 2: Always run classification
    classify()