import pandas as pd
import joblib
import os

# =====================================================
# FILE PATHS
# =====================================================

# First 30 swings → calibration dataset
#CALIBRATION_CSV = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\badminton_data.csv"
CALIBRATION_CSV = r"C:\Users\aswin\Downloads\data 1\badminton_data.csv"

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
OUTPUT_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\end2end\finalClassifiedOp\final_classified_output_with_pro_comparison_v3.csv"


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

    compare_cols = [
        "speed",
        "impact",
        "duration",
        "power",
        "efficiency"
    ]

    player_avg = player_df[compare_cols].mean()
    pro_avg = pro_df[compare_cols].mean()

    comparison = {}

    for col in compare_cols:
        player_val = round(player_avg[col], 2)
        pro_val = round(pro_avg[col], 2)

        if col == "duration":
            # Lower is better
            gap = round(pro_val - player_val, 2)
        else:
            gap = round(player_val - pro_val, 2)

        comparison[f"player_avg_{col}"] = player_val
        comparison[f"pro_avg_{col}"] = pro_val
        comparison[f"gap_{col}"] = gap

    return comparison


# =====================================================
# SESSION SUMMARY FUNCTION
# =====================================================

def get_session_summary(df):

    summary = {}

    summary["total_swings"] = len(df)

    summary["weak_count"] = (df["final_prediction"] == "WEAK").sum()
    summary["medium_count"] = (df["final_prediction"] == "MEDIUM").sum()
    summary["strong_count"] = (df["final_prediction"] == "STRONG").sum()

    summary["avg_speed"] = df["speed"].mean()
    summary["avg_impact"] = df["impact"].mean()
    summary["avg_power"] = df["power"].mean()

    # Consistency
    summary["std_power"] = df["power"].std()
    summary["std_speed"] = df["speed"].std()

    # Best + Worst swing
    best_idx = df["power"].idxmax()
    worst_idx = df["power"].idxmin()

    summary["best_swing"] = df.loc[best_idx]
    summary["worst_swing"] = df.loc[worst_idx]

    return summary


# =====================================================
# SMART COACHING ENGINE
# =====================================================

def generate_smart_suggestions(summary, comparison):

    suggestions = []

    # SPEED
    if comparison["gap_speed"] < -3:
        suggestions.append(
            "Increase racket swing speed using forearm acceleration"
        )

    # IMPACT
    if comparison["gap_impact"] < -5:
        suggestions.append(
            "Improve shuttle contact timing and hitting strength"
        )

    # POWER
    if comparison["gap_power"] < -500:
        suggestions.append(
            "Focus on explosive power generation during smashes"
        )

    # DURATION
    if comparison["gap_duration"] < -0.08:
        suggestions.append(
            "Reduce swing execution time for faster response"
        )

    # CONSISTENCY
    if summary["std_power"] > 400:
        suggestions.append(
            "Improve consistency — your swing power varies too much"
        )

    if summary["std_speed"] > 8:
        suggestions.append(
            "Maintain stable swing speed across all shots"
        )

    # FALLBACK
    if len(suggestions) == 0:
        suggestions.append(
            "Your performance is close to professional level. Keep refining technique."
        )

    return suggestions[:5]


# =====================================================
# CLASSIFICATION FUNCTION
# =====================================================

def classify():

    print("\n🤖 AUTO-CLASSIFICATION STARTED")

    df = pd.read_csv(NEW_DATA_CSV)
    df = df[["speed", "impact", "duration"]].dropna()

    df = add_features(df)

    # ---------------------------------
    # Load Threshold
    # ---------------------------------

    th = pd.read_csv(THRESHOLD_FILE)

    weak_th = th["weak_threshold"][0]
    strong_th = th["strong_threshold"][0]

    # ---------------------------------
    # Load ML Model
    # ---------------------------------

    model, features = load_model()

    X = df[features]

    df["ml_prediction"] = model.predict(X)

    # ---------------------------------
    # Rule-Based Prediction
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
    # Session Summary
    # ---------------------------------

    summary = get_session_summary(df)

    # ---------------------------------
    # Pro Comparison
    # ---------------------------------

    comparison = compare_with_pro(df)

    # ---------------------------------
    # Smart Suggestions
    # ---------------------------------

    suggestions = generate_smart_suggestions(summary, comparison)

    # =================================================
    # PRINT PERFORMANCE SUMMARY
    # =================================================

    print("\n===================================")
    print("📊 PERFORMANCE SUMMARY")
    print("===================================")

    print(f"Total Swings : {summary['total_swings']}")
    print(f"Weak         : {summary['weak_count']}")
    print(f"Medium       : {summary['medium_count']}")
    print(f"Strong       : {summary['strong_count']}")

    print(f"\nAvg Speed    : {summary['avg_speed']:.2f}")
    print(f"Avg Impact   : {summary['avg_impact']:.2f}")
    print(f"Avg Power    : {summary['avg_power']:.2f}")

    # =================================================
    # BEST SWING
    # =================================================

    print("\n🔥 BEST SWING")

    b = summary["best_swing"]

    print(f"Speed   : {b['speed']:.2f}")
    print(f"Impact  : {b['impact']:.2f}")
    print(f"Power   : {b['power']:.2f}")

    # =================================================
    # WORST SWING
    # =================================================

    print("\n❄ WORST SWING")

    w = summary["worst_swing"]

    print(f"Speed   : {w['speed']:.2f}")
    print(f"Impact  : {w['impact']:.2f}")
    print(f"Power   : {w['power']:.2f}")

    # =================================================
    # PLAYER vs PRO TABLE
    # =================================================

    print("\n===================================")
    print("🏆 PLAYER vs PRO")
    print("===================================")

    print("Parameter   Player    Pro      Gap")

    for param in ["speed", "impact", "power"]:
        print(
            f"{param.capitalize():<10} "
            f"{comparison[f'player_avg_{param}']:<8} "
            f"{comparison[f'pro_avg_{param}']:<8} "
            f"{comparison[f'gap_{param}']}"
        )
    print("\n🏆Gap Analysis")
    print("===================================")
    if comparison["gap_power"] >-200:
        print("Near Pro Level")
    elif comparison["gap_power"] >-600:
        print("Needs improvement")
    else:
        print("Major Gap")
        
    print("-----------------------------------")
    # =================================================
    # COACHING FEEDBACK
    # =================================================

    print("\n🎯 COACHING FEEDBACK")
    print("-----------------------------------")

    for s in suggestions:
        print("✔", s)

    print("-----------------------------------")

    # =================================================
    # SAVE TO OUTPUT CSV
    # =================================================

    for key, value in comparison.items():
        df[key] = value

    df["session_suggestions"] = " | ".join(suggestions)

    df.to_csv(OUTPUT_FILE, index=False)

    print("\n💾 Final Output Saved:")
    print(OUTPUT_FILE)

    print("\n✅ PERFORMANCE CLASSIFICATION COMPLETED")


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

    # STEP 2 → Classification + Pro Comparison
    classify()