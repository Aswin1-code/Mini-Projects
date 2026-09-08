import pandas as pd
import joblib
import os

# =====================================================
# FILE PATHS
# =====================================================

# First 30 swings → calibration dataset
#CALIBRATION_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\badminton_data.csv"
CALIBRATION_CSV =r"C:\Users\aswin\Downloads\data 1\badminton_data.csv"

# New swings to classify
#NEW_DATA_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\badminton_data (1).csv"
NEW_DATA_CSV = r"C:\Users\aswin\Downloads\data 1\badminton_data (1).csv"
# Threshold file
THRESHOLD_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\thresholdFile.csv"

# Trained ML model
MODEL_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\performanceClassify ml train\swing_model.pkl"

# MATLAB generated PRO benchmark dataset
PRO_DATASET_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\matlab generate pro data\pro_benchmark_dataset.csv"

# Final output
OUTPUT_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\end2end\finalClassifiedOp\final_classified_output_with_pro_comparison v2.csv"


# =====================================================
# FEATURE ENGINEERING
# =====================================================

def add_features(df):
    df["power"] = df["speed"] * df["impact"]

    # Keep same logic as your current system
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)

    return df


# =====================================================
# CALIBRATION FUNCTION
# =====================================================

def calibration():

    print("\n🏸 AUTO-CALIBRATION STARTED")

    df = pd.read_csv(CALIBRATION_CSV)
    df = df[["speed", "impact", "duration"]].dropna()

    # First 30 swings only
    df = df.head(30)

    df = add_features(df)

    weak_th = df["power"].quantile(0.25)
    strong_th = df["power"].quantile(0.75)

    threshold_df = pd.DataFrame([{
        "weak_threshold": weak_th,
        "strong_threshold": strong_th,
        "avg_speed": df["speed"].mean(),
        "avg_impact": df["impact"].mean(),
        "avg_power": df["power"].mean(),
        "avg_duration": df["duration"].mean(),
        "avg_efficiency": df["efficiency"].mean()
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
# PRO BENCHMARK COMPARISON
# =====================================================

def compare_with_pro(player_df):

    print("\n🏆 Comparing Against PRO Benchmark")

    pro_df = pd.read_csv(PRO_DATASET_FILE)

    # Required columns
    compare_cols = [
        "speed",
        "impact",
        "duration",
        "power",
        "efficiency"
    ]

    # Player average profile
    player_avg = player_df[compare_cols].mean()

    # Pro average profile
    pro_avg = pro_df[compare_cols].mean()

    comparison = {}

    for col in compare_cols:
        player_val = round(player_avg[col], 2)
        pro_val = round(pro_avg[col], 2)

        if col == "duration":
            # Lower duration is better
            gap = round(pro_val - player_val, 2)
        else:
            gap = round(player_val - pro_val, 2)

        comparison[f"player_avg_{col}"] = player_val
        comparison[f"pro_avg_{col}"] = pro_val
        comparison[f"gap_{col}"] = gap

    return comparison


# =====================================================
# IMPROVEMENT SUGGESTION ENGINE
# =====================================================

def generate_suggestions(comparison):

    suggestions = []

    if comparison["gap_speed"] < -5:
        suggestions.append("Improve wrist acceleration and racket swing speed")

    if comparison["gap_impact"] < -5:
        suggestions.append("Improve smash timing and impact force")

    if comparison["gap_efficiency"] < -10:
        suggestions.append("Improve shot execution efficiency and control")

    if comparison["gap_duration"] < -0.10:
        suggestions.append("Reduce swing execution time for faster response")

    if len(suggestions) == 0:
        suggestions.append("Performance is close to professional benchmark")

    return " | ".join(suggestions)


# =====================================================
# CLASSIFICATION FUNCTION
# =====================================================

def classify():

    print("\n🤖 AUTO-CLASSIFICATION STARTED")

    df = pd.read_csv(NEW_DATA_CSV)
    df = df[["speed", "impact", "duration"]].dropna()

    df = add_features(df)

    # ---------------------------------
    # Load threshold
    # ---------------------------------

    th = pd.read_csv(THRESHOLD_FILE)

    weak_th = th["weak_threshold"][0]
    strong_th = th["strong_threshold"][0]

    # ---------------------------------
    # Load ML model
    # ---------------------------------

    model, features = load_model()

    X = df[features]

    df["ml_prediction"] = model.predict(X)

    # ---------------------------------
    # Rule-based prediction
    # ---------------------------------

    def rule(row):
        if row["power"] < weak_th:
            return "WEAK"
        elif row["power"] < strong_th:
            return "MEDIUM"
        else:
            return "STRONG"

    df["rule_prediction"] = df.apply(rule, axis=1)

    # ---------------------------------
    # Final Prediction (Hybrid)
    # ---------------------------------

    df["final_prediction"] = df["ml_prediction"]

    # ---------------------------------
    # PRO Benchmark Comparison
    # ---------------------------------

    comparison = compare_with_pro(df)

    suggestions = generate_suggestions(comparison)

    print("\n========== PLAYER vs PRO ==========")

    for k, v in comparison.items():
        print(f"{k}: {v}")

    print("\n🎯 Suggestions:")
    print(suggestions)

    print("===================================\n")

    # Add comparison values to output CSV
    for key, value in comparison.items():
        df[key] = value

    df["improvement_suggestions"] = suggestions

    # ---------------------------------
    # Save output
    # ---------------------------------

    df.to_csv(OUTPUT_FILE, index=False)

    print("💾 Final Output Saved:")
    print(OUTPUT_FILE)


# =====================================================
# AUTO CONTROLLER
# =====================================================

if __name__ == "__main__":

    print("\n======================================")
    print("🏸 SMART BADMINTON AUTO SYSTEM + PRO AI")
    print("======================================")

    # STEP 1 → Calibration
    if not os.path.exists(THRESHOLD_FILE):

        print("\n⚠ Threshold file not found")
        print("Running first-time calibration...\n")

        calibration()

    else:

        print("\n✅ Threshold already exists")
        print("Skipping calibration")

    # STEP 2 → Classification + PRO comparison
    classify()