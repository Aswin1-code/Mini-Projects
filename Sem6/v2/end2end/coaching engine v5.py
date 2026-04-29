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

def load_or_create_threshold():

    if not os.path.exists(THRESHOLD_FILE):
        print("\n⚠ Threshold file not found. Running calibration...")

        df = pd.read_csv(CALIBRATION_CSV)
        df = df[["speed", "impact", "duration"]].dropna()
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

        print("✅ Calibration completed & threshold created")

    return pd.read_csv(THRESHOLD_FILE)


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

def compute_stability_score(df, summary, consistency_scores):

    # -----------------------------
    # NORMALIZED PERFORMANCE SCORE
    # -----------------------------

    power_score = summary["avg_power"] / (summary["avg_power"] + summary["std_power"] + 1e-6)

    # scale to 10
    power_component = power_score * 10

    # -----------------------------
    # CONSISTENCY IMPACT
    # -----------------------------

    consistency_component = consistency_scores["consistency_score"] / 10

    # -----------------------------
    # FINAL STABILITY SCORE
    # -----------------------------

    stability = (0.6 * power_component) + (0.4 * consistency_component)

    return round(min(10, stability), 2)

def compute_consistency_scores(df, summary):

    scores = {}

    # -----------------------------
    # SPEED CONSISTENCY
    # -----------------------------
    speed_cv = df["speed"].std() / (df["speed"].mean() + 1e-6)

    # -----------------------------
    # IMPACT CONSISTENCY
    # -----------------------------
    impact_cv = df["impact"].std() / (df["impact"].mean() + 1e-6)

    # -----------------------------
    # POWER CONSISTENCY
    # -----------------------------
    power_cv = df["power"].std() / (df["power"].mean() + 1e-6)

    # -----------------------------
    # NORMALIZED CONSISTENCY SCORE (0–100)
    # lower CV = higher score
    # -----------------------------

    consistency_score = 100 * (
        1 - min(1, (speed_cv + impact_cv + power_cv) / 3)
    )

    scores["speed_cv"] = round(speed_cv, 3)
    scores["impact_cv"] = round(impact_cv, 3)
    scores["power_cv"] = round(power_cv, 3)

    scores["consistency_score"] = round(consistency_score, 2)

    return scores

def classify_player_type(df, summary):

    stroke_dist = df["stroke_type"].value_counts(normalize=True) * 100

    smash_pct = stroke_dist.get("SMASH", 0)
    drop_pct  = stroke_dist.get("DROP", 0)
    clear_pct = stroke_dist.get("CLEAR", 0)
    drive_pct = stroke_dist.get("DRIVE", 0)

    avg_power = summary["avg_power"]
    std_power = summary["std_power"]

    # -----------------------------
    # ATTACKER SCORE
    # -----------------------------
    attacker_score = (smash_pct * 0.6) + (avg_power / 100)

    # -----------------------------
    # DEFENDER SCORE
    # -----------------------------
    defender_score = (clear_pct * 0.6) + (1 / (avg_power + 1e-6)) * 1000

    # -----------------------------
    # ALL-ROUNDER SCORE
    # -----------------------------
    balance = 100 - abs(smash_pct - clear_pct) - abs(drop_pct - drive_pct)

    # -----------------------------
    # FINAL CLASSIFICATION
    # -----------------------------

    if attacker_score > defender_score and smash_pct > 40:
        player_type = "🔥 Attacker"
        explanation = "You rely heavily on smashes and high power shots."

    elif defender_score > attacker_score and clear_pct > 35:
        player_type = "🛡 Defensive Player"
        explanation = "You focus on rallies, clears, and controlled gameplay."

    elif balance > 60:
        player_type = "⚖ All-Rounder"
        explanation = "Balanced mix of attacking and defensive strokes."

    else:
        player_type = "🎯 Mixed Style Player"
        explanation = "No dominant pattern detected clearly."

    return {
        "player_type": player_type,
        "smash_pct": round(smash_pct, 2),
        "clear_pct": round(clear_pct, 2),
        "drop_pct": round(drop_pct, 2),
        "drive_pct": round(drive_pct, 2),
        "explanation": explanation
    }

def fatigue_detection(df):

    n = len(df)

    if n < 10:
        return {
            "fatigue_score": 0,
            "status": "Insufficient data"
        }

    # -----------------------------
    # SPLIT EARLY & LATE SWINGS
    # -----------------------------

    early = df.iloc[:int(n * 0.4)]
    late  = df.iloc[int(n * 0.6):]

    # -----------------------------
    # AVERAGES
    # -----------------------------

    early_speed = early["speed"].mean()
    late_speed  = late["speed"].mean()

    early_impact = early["impact"].mean()
    late_impact  = late["impact"].mean()

    early_power = early["power"].mean()
    late_power  = late["power"].mean()

    # -----------------------------
    # DROP CALCULATION (%)
    # -----------------------------

    speed_drop = ((early_speed - late_speed) / (early_speed + 1e-6)) * 100
    impact_drop = ((early_impact - late_impact) / (early_impact + 1e-6)) * 100
    power_drop = ((early_power - late_power) / (early_power + 1e-6)) * 100

    # -----------------------------
    # FATIGUE SCORE (AVERAGE DROP)
    # -----------------------------

    fatigue_score = np.mean([speed_drop, impact_drop, power_drop])

    # -----------------------------
    # STATUS CLASSIFICATION
    # -----------------------------

    if fatigue_score < 10:
        status = "Fresh performance throughout session"
    elif fatigue_score < 25:
        status = "Mild fatigue detected"
    else:
        status = "High fatigue detected – performance drop significant"

    return {
        "fatigue_score": round(fatigue_score, 2),
        "speed_drop": round(speed_drop, 2),
        "impact_drop": round(impact_drop, 2),
        "power_drop": round(power_drop, 2),
        "status": status
    }

def technique_feedback(df, summary):

    feedback = []

    # -----------------------------
    # DATA-BASED THRESHOLDS
    # -----------------------------

    speed_low = df["speed"].quantile(0.25)
    speed_high = df["speed"].quantile(0.75)

    impact_low = df["impact"].quantile(0.25)
    impact_high = df["impact"].quantile(0.75)

    power_std = summary["std_power"]
    power_mean = summary["avg_power"]

    # -----------------------------
    # 1. TIMING (SPEED vs IMPACT)
    # -----------------------------

    ratio = summary["avg_speed"] / (summary["avg_impact"] + 1e-6)

    if ratio > 1.4:
        feedback.append("⚠ Timing Issue: High swing speed but low impact → late shuttle contact likely")
    elif ratio < 0.8:
        feedback.append("⚠ Timing Issue: Strong impact but low speed → early contact / poor acceleration")
    else:
        feedback.append("✔ Timing between speed and impact is balanced")

    # -----------------------------
    # 2. IMPACT QUALITY
    # -----------------------------

    if summary["avg_impact"] < impact_low:
        feedback.append("⚠ Impact Weakness: Below your normal baseline → inconsistent racket contact")
    elif summary["avg_impact"] < impact_high:
        feedback.append("ℹ Impact: Moderate but improvable contact strength")
    else:
        feedback.append("✔ Strong and stable shuttle impact")

    # -----------------------------
    # 3. SPEED CONSISTENCY
    # -----------------------------

    speed_std = df["speed"].std()

    if speed_std > df["speed"].mean() * 0.35:
        feedback.append("⚠ Speed inconsistency: Swing speed varies too much between shots")
    else:
        feedback.append("✔ Stable swing speed across sessions")

    # -----------------------------
    # 4. POWER CONSISTENCY
    # -----------------------------

    if power_std > power_mean * 0.35:
        feedback.append("⚠ Power inconsistency: Unstable shot strength across rallies")
    else:
        feedback.append("✔ Consistent power output")

    # -----------------------------
    # 5. PLAY STYLE INSIGHT
    # -----------------------------

    stroke_dist = df["stroke_type"].value_counts()
    dominant = stroke_dist.idxmax()

    if dominant == "SMASH":
        feedback.append("ℹ Play Style: Aggressive attacker (smash dominant)")
    elif dominant == "DROP":
        feedback.append("ℹ Play Style: Tactical control player")
    elif dominant == "CLEAR":
        feedback.append("ℹ Play Style: Defensive rally builder")
    else:
        feedback.append("ℹ Mixed playing style detected")

    return feedback

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
    th = load_or_create_threshold()

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
    
    fatigue = fatigue_detection(df)
    player_profile = classify_player_type(df, summary)
    consistency_scores = compute_consistency_scores(df, summary)
    stability_score = compute_stability_score(df, summary, consistency_scores)
    
    
    
    
    

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


    # =========================
    # STROKE DISTRIBUTION
    # =========================
    print("\n🏸 Stroke Distribution:")
    for stroke, count in df["stroke_type"].value_counts().items():
        print(f"{stroke:<10}: {count}")


    # =========================
    # BEST / WORST SWING
    # =========================
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


    # =========================
    # PLAYER vs PRO
    # =========================
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


    # =========================
    # GAP ANALYSIS
    # =========================
    print("\n🧠 GAP ANALYSIS")
    print("===================================")

    for feature, msg in gap_analysis:
        print(f"{feature} : {msg}")

    print("\n🏆 PLAYER LEVEL")
    print(level)


    # =========================
    # CONSISTENCY + STABILITY
    # =========================
    print("\n📊 CONSISTENCY ANALYSIS")
    print("===================================")

    print(f"Speed CV    : {consistency_scores['speed_cv']}")
    print(f"Impact CV   : {consistency_scores['impact_cv']}")
    print(f"Power CV    : {consistency_scores['power_cv']}")

    print(f"\nConsistency Score: {consistency_scores['consistency_score']}/100")
    print(f"⚡ Stability Score : {stability_score}/10")


    # =========================
    # FATIGUE
    # =========================
    print("\n🫀 FATIGUE ANALYSIS")
    print("===================================")

    print(f"Speed Drop  : {fatigue['speed_drop']} %")
    print(f"Impact Drop : {fatigue['impact_drop']} %")
    print(f"Power Drop  : {fatigue['power_drop']} %")

    print(f"\nFatigue Score: {fatigue['fatigue_score']} %")
    print("Status:", fatigue["status"])


    # =========================
    # PLAYER TYPE
    # =========================
    print("\n🧬 PLAYER TYPE ANALYSIS")
    print("===================================")

    print("Type:", player_profile["player_type"])
    print(player_profile["explanation"])

    print("\nStroke Distribution %:")
    print(f"SMASH : {player_profile['smash_pct']}")
    print(f"DROP  : {player_profile['drop_pct']}")
    print(f"CLEAR : {player_profile['clear_pct']}")
    print(f"DRIVE : {player_profile['drive_pct']}")


    # =========================
    # COACHING
    # =========================
    print("\n🎯 COACHING FEEDBACK")
    print("-----------------------------------")

    for s in suggestions:
        print("✔", s)


    # =========================
    # SAVE
    # =========================
    print("\n💾 Saving Output...")
    df.to_csv(OUTPUT_FILE, index=False)

    print("Saved:", OUTPUT_FILE)
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