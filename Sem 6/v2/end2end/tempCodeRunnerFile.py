import pandas as pd
import joblib
import os
import numpy as np

# =====================================================
# FILE PATHS
# =====================================================

CALIBRATION_CSV = r"C:\Users\aswin\Downloads\data 1\badminton_data.csv"
NEW_DATA_CSV = r"C:\Users\aswin\Downloads\data 1\badminton_data (1).csv"

THRESHOLD_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\thresholdFile.csv"

SWING_MODEL_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\performanceClassify ml train\swing_model.pkl"

STROKE_MODEL_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\strokeClassifierModel\stroke classifier pkl\stroke_model.pkl" 

PRO_DATASET_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\matlab generate pro data\pro_benchmark_dataset.csv"

OUTPUT_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\end2end\finalClassifiedOp\final_classified_output_v4.csv"


# =====================================================
# FEATURE ENGINEERING
# =====================================================

def add_features(df):
    df["power"] = df["speed"] * df["impact"]
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)
    return df


def add_stroke_features(df):
    df["acc_mag"] = df["speed"]
    df["gyro_mag"] = df["impact"]
    df["peak_acc"] = df["speed"] * 1.2
    df["peak_gyro"] = df["impact"] * 1.1
    df["energy"] = df["power"] * df["duration"]
    return df


# =====================================================
# LOAD MODELS
# =====================================================

def load_swing_model():
    model_pack = joblib.load(SWING_MODEL_FILE)
    return model_pack["model"], model_pack["features"]


def load_stroke_model():
    model_pack = joblib.load(STROKE_MODEL_FILE)
    return model_pack["model"], model_pack["features"]


# =====================================================
# PRO COMPARISON
# =====================================================

def compare_with_pro(player_df):

    pro_df = pd.read_csv(PRO_DATASET_FILE)

    cols = ["speed", "impact", "duration", "power", "efficiency"]

    player_avg = player_df[cols].mean()
    pro_avg = pro_df[cols].mean()

    comparison = {}

    for col in cols:
        p = player_avg[col]
        pr = pro_avg[col]

        if col == "duration":
            gap = pr - p
        else:
            gap = p - pr

        comparison[f"player_avg_{col}"] = round(p, 2)
        comparison[f"pro_avg_{col}"] = round(pr, 2)
        comparison[f"gap_{col}"] = round(gap, 2)

    return comparison


# =====================================================
# GAP ANALYSIS
# =====================================================

def generate_gap_analysis(comparison):

    analysis = []

    if comparison["gap_speed"] < -5:
        analysis.append(("Speed", "Major deficit in swing acceleration"))
    elif comparison["gap_speed"] < -2:
        analysis.append(("Speed", "Moderate speed improvement needed"))
    else:
        analysis.append(("Speed", "Close to pro level"))

    if comparison["gap_impact"] < -8:
        analysis.append(("Impact", "Weak shuttle contact force"))
    elif comparison["gap_impact"] < -3:
        analysis.append(("Impact", "Timing needs refinement"))
    else:
        analysis.append(("Impact", "Good striking control"))

    if comparison["gap_power"] < -700:
        analysis.append(("Power", "Very low explosive strength"))
    elif comparison["gap_power"] < -300:
        analysis.append(("Power", "Power generation needs work"))
    else:
        analysis.append(("Power", "Strong power output"))

    total_gap = comparison["gap_power"]

    if total_gap > -200:
        level = "Near Pro Level 🏆"
    elif total_gap > -600:
        level = "Intermediate Player"
    else:
        level = "Needs Major Improvement"

    return analysis, level


# =====================================================
# SUMMARY
# =====================================================

def get_session_summary(df):

    return {
        "total_swings": len(df),
        "weak_count": (df["final_prediction"] == "WEAK").sum(),
        "medium_count": (df["final_prediction"] == "MEDIUM").sum(),
        "strong_count": (df["final_prediction"] == "STRONG").sum(),
        "avg_speed": df["speed"].mean(),
        "avg_impact": df["impact"].mean(),
        "avg_power": df["power"].mean(),
        "std_power": df["power"].std(),
        "std_speed": df["speed"].std(),
        "best_swing": df.loc[df["power"].idxmax()],
        "worst_swing": df.loc[df["power"].idxmin()]
    }


# =====================================================
# SMART COACH
# =====================================================

def generate_suggestions(summary, comparison):

    s = []

    if comparison["gap_speed"] < -3:
        s.append("Increase racket swing speed using forearm acceleration")

    if comparison["gap_impact"] < -5:
        s.append("Improve shuttle contact timing")

    if comparison["gap_power"] < -500:
        s.append("Focus on explosive smash power")

    if summary["std_power"] > 400:
        s.append("Improve consistency in swing power")

    if len(s) == 0:
        s.append("Performance is close to pro level 🚀")

    return s[:5]


# =====================================================
# MAIN CLASSIFIER
# =====================================================

def classify():

    print("\n🤖 SMART BADMINTON AI SYSTEM STARTED")

    df = pd.read_csv(NEW_DATA_CSV)
    df = df.dropna()

    df = add_features(df)
    df = add_stroke_features(df)

    # -------------------------
    # LOAD THRESHOLD
    # -------------------------
    th = pd.read_csv(THRESHOLD_FILE)

    weak_th = th["weak_threshold"][0]
    strong_th = th["strong_threshold"][0]

    # -------------------------
    # LOAD MODELS
    # -------------------------
    swing_model, swing_features = load_swing_model()
    stroke_model, stroke_features = load_stroke_model()

    # -------------------------
    # SWING PREDICTION
    # -------------------------
    X_swing = df[swing_features]
    df["ml_swing"] = swing_model.predict(X_swing)

    # -------------------------
    # STROKE PREDICTION (FIXED SAFE VERSION)
    # -------------------------
    missing = [f for f in stroke_features if f not in df.columns]
    print("Missing features:", missing)

    if missing:
        raise Exception(f"Missing stroke features: {missing}")

    X_stroke = df.reindex(columns=stroke_features)
    df["stroke_type"] = stroke_model.predict(X_stroke)

    # -------------------------
    # RULE BASED CLASSIFICATION
    # -------------------------
    def rule(row):
        if row["power"] < weak_th:
            return "WEAK"
        elif row["power"] < strong_th:
            return "MEDIUM"
        else:
            return "STRONG"

    df["final_prediction"] = df.apply(rule, axis=1)

    # -------------------------
    # SUMMARY + PRO
    # -------------------------
    summary = get_session_summary(df)
    comparison = compare_with_pro(df)
    gap_analysis, level = generate_gap_analysis(comparison)
    suggestions = generate_suggestions(summary, comparison)

    # =================================================
    # OUTPUT
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

    print("\n🏸 Stroke Distribution:")
    for stroke, count in df["stroke_type"].value_counts().items():
        print(f"{stroke:<10}: {count}")

    print("\n🔥 BEST SWING")
    b = summary["best_swing"]
    print(f"Speed   : {b['speed']:.2f}")
    print(f"Impact  : {b['impact']:.2f}")
    print(f"Power   : {b['power']:.2f}")

    print("\n❄ WORST SWING")
    w = summary["worst_swing"]
    print(f"Speed   : {w['speed']:.2f}")
    print(f"Impact  : {w['impact']:.2f}")
    print(f"Power   : {w['power']:.2f}")

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
    # =================================================
    # 🧠 GAP ANALYSIS OUTPUT (FIX ADDED)
    # =================================================

    print("\n🧠 GAP ANALYSIS")
    print("===================================")

    for feature, msg in gap_analysis:
        print(f"{feature} : {msg}")

    print("\n🏆 PLAYER LEVEL")
    print("-----------------------------------")
    print(level)

    print("\n🎯 COACHING FEEDBACK")
    print("-----------------------------------")

    for s in suggestions:
        print("✔", s)

    # -------------------------
    # SAVE OUTPUT
    # -------------------------
    for k, v in comparison.items():
        df[k] = v

    df["session_suggestions"] = " | ".join(suggestions)
    df["player_level"] = level
    df["gap_analysis"] = " | ".join([f"{a[0]}: {a[1]}" for a in gap_analysis])

    df.to_csv(OUTPUT_FILE, index=False)

    print("\n💾 Final Output Saved:")
    print(OUTPUT_FILE)
    print("✅ SYSTEM COMPLETED SUCCESSFULLY")


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    print("\n======================================")
    print("🏸 SMART BADMINTON AUTO SYSTEM + PRO AI")
    print("======================================")

    if not os.path.exists(THRESHOLD_FILE):
        print("⚠ First run calibration required")
    else:
        print("✅ Threshold already exists")

    classify()