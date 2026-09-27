import pandas as pd
import joblib
import os
import numpy as np


# =====================================================
# FILE PATHS
# =====================================================

CALIBRATION_CSV = (
    r"C:\Users\aswin\Downloads\data 3\calib.csv"
)

NEW_DATA_CSV = (
    r"C:\Users\aswin\Downloads\data 3\game.csv"
)

THRESHOLD_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\final_end2end"
    r"\thresholdFiles\thresholdFile.csv"
)

# =====================================================
# SPLIT DATASET OUTPUT PATHS
# =====================================================

CALIBRATION_REAL_OUTPUT = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\final_end2end"
    r"\calibrationOutput\calibration_real_swings.csv"
)

CALIBRATION_DUMMY_OUTPUT = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\final_end2end"
    r"\calibrationOutput\calibration_dummy_swings.csv"
)

GAME_REAL_OUTPUT = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\final_end2end"
    r"\gameModeOutput\game_real_swings.csv"
)

GAME_DUMMY_OUTPUT = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles\final_end2end"
    r"\gameModeOutput\game_dummy_swings.csv"
)

# =====================================================
# EXISTING MODELS
# =====================================================

SWING_MODEL_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles"
    r"\performanceClassify ml train\swing_model.pkl"
)

STROKE_MODEL_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles"
    r"\strokeClassifierModel\stroke classifier pkl"
    r"\stroke_model.pkl"
)

PRO_DATASET_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles"
    r"\matlab generate pro data\pro_benchmark_dataset.csv"
)

OUTPUT_FILE = (
    r"E:\Mini Project\gitfolder all proj\Mini-Projects"
    r"\SIH26 badminton proj v1\codeFiles"
    r"\final_classified_op\final_classified_output_v1.csv"
)


# =====================================================
# COMMON HELPERS
# =====================================================

def save_csv(df, output_path):
    """Save a dataframe without modifying the source CSV."""

    folder = os.path.dirname(output_path)

    if folder:
        os.makedirs(folder, exist_ok=True)

    df.to_csv(output_path, index=False)


def load_and_split_intflag(csv_path, real_output, dummy_output):
    """
    Load the complete ESP32 CSV and separate:
        int_flag = 1 -> real swings
        int_flag = 0 -> dummy swings

    The original uploaded CSV is never modified.
    Both split datasets are saved separately.
    """

    df = pd.read_csv(csv_path)

    if "int_flag" not in df.columns:
        raise ValueError(
            f"Missing required column 'int_flag' in:\n{csv_path}"
        )

    # Preserve original values in the source dataframe,
    # but use a numeric helper column for reliable filtering.
    flag = pd.to_numeric(
        df["int_flag"],
        errors="coerce"
    )

    real_df = df[flag == 1].copy()
    dummy_df = df[flag == 0].copy()

    # Unexpected/missing flags are not classified as real or dummy.
    unknown_df = df[~flag.isin([0, 1])].copy()

    save_csv(real_df, real_output)
    save_csv(dummy_df, dummy_output)

    counts = {
        "total": len(df),
        "real": len(real_df),
        "dummy": len(dummy_df),
        "unknown": len(unknown_df)
    }

    return real_df, dummy_df, counts


# =====================================================
# FEATURE ENGINEERING
# =====================================================

def add_features(df):
    df = df.copy()

    df["power"] = df["speed"] * df["impact"]

    df["efficiency"] = (
        df["impact"] / (df["duration"] + 1e-6)
    )

    return df


def add_stroke_features(df):
    df = df.copy()

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

    return (
        model_pack["model"],
        model_pack["features"]
    )


def load_stroke_model():
    model_pack = joblib.load(STROKE_MODEL_FILE)

    return (
        model_pack["model"],
        model_pack["features"]
    )


# =====================================================
# CALIBRATION
# =====================================================

def load_or_create_threshold():
    """
    Use only real calibration swings (int_flag = 1).

    Preserve original behavior:
    - If threshold file exists, load it.
    - If it does not exist, calculate thresholds and save them.
    """

    if not os.path.exists(THRESHOLD_FILE):

        print("\n⚠ Threshold file not found.")
        print("Running calibration using real swings only...")

        calibration_df, dummy_df, counts = load_and_split_intflag(
            CALIBRATION_CSV,
            CALIBRATION_REAL_OUTPUT,
            CALIBRATION_DUMMY_OUTPUT
        )

        print("\n📊 CALIBRATION DATASET")
        print(f"Total records : {counts['total']}")
        print(f"Real swings   : {counts['real']}")
        print(f"Dummy swings  : {counts['dummy']}")
        print(f"Unknown flags : {counts['unknown']}")

        if calibration_df.empty:
            raise ValueError(
                "No calibration swings with int_flag = 1."
            )

        required = ["speed", "impact", "duration"]

        missing = [
            col for col in required
            if col not in calibration_df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing calibration columns: {missing}"
            )

        # Use only real calibration swings.
        df = calibration_df[required].copy()
        df = df.dropna()

        if df.empty:
            raise ValueError(
                "No usable real calibration rows after removing NaN values."
            )

        # Existing feature engineering formulae.
        df = add_features(df)

        # Existing threshold formulae.
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

        folder = os.path.dirname(THRESHOLD_FILE)

        if folder:
            os.makedirs(folder, exist_ok=True)

        threshold_df.to_csv(
            THRESHOLD_FILE,
            index=False
        )

        print("\n✅ Calibration completed.")
        print("✅ Threshold file created.")

        print(
            f"Real calibration swings used: {len(df)}"
        )

        print(
            f"Weak threshold   : {weak_th:.2f}"
        )

        print(
            f"Strong threshold : {strong_th:.2f}"
        )

    else:
        print("\n✅ Existing threshold file found.")
        print("Loading saved calibration thresholds.")

    return pd.read_csv(THRESHOLD_FILE)


# =====================================================
# SESSION DURATION
# =====================================================

def calculate_session_duration(df):
    """
    Calculate elapsed session time using the ESP32 timestamp
    column, assumed to be milliseconds.

    Returns:
        duration_ms
        formatted duration: HH:MM:SS.mmm
    """

    if "timestamp" not in df.columns:
        return None, "Timestamp unavailable"

    timestamps = pd.to_numeric(
        df["timestamp"],
        errors="coerce"
    ).dropna()

    if len(timestamps) < 2:
        return None, "Insufficient timestamps"

    first_timestamp = timestamps.min()
    last_timestamp = timestamps.max()

    duration_ms = max(
        0,
        int(last_timestamp - first_timestamp)
    )

    total_seconds, milliseconds = divmod(
        duration_ms,
        1000
    )

    hours, remainder = divmod(
        total_seconds,
        3600
    )

    minutes, seconds = divmod(
        remainder,
        60
    )

    formatted = (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d}."
        f"{milliseconds:03d}"
    )

    return duration_ms, formatted


# =====================================================
# PRO COMPARISON
# =====================================================

def compare_with_pro(player_df):
    pro_df = pd.read_csv(PRO_DATASET_FILE)

    cols = [
        "speed",
        "impact",
        "duration",
        "power",
        "efficiency"
    ]

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
        analysis.append(
            ("Speed", "Major deficit in swing acceleration")
        )

    elif comparison["gap_speed"] < -2:
        analysis.append(
            ("Speed", "Moderate speed improvement needed")
        )

    else:
        analysis.append(
            ("Speed", "Close to pro level")
        )

    if comparison["gap_impact"] < -8:
        analysis.append(
            ("Impact", "Weak shuttle contact force")
        )

    elif comparison["gap_impact"] < -3:
        analysis.append(
            ("Impact", "Timing needs refinement")
        )

    else:
        analysis.append(
            ("Impact", "Good striking control")
        )

    if comparison["gap_power"] < -700:
        analysis.append(
            ("Power", "Very low explosive strength")
        )

    elif comparison["gap_power"] < -300:
        analysis.append(
            ("Power", "Power generation needs work")
        )

    else:
        analysis.append(
            ("Power", "Strong power output")
        )

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

        "weak_count": (
            df["final_prediction"] == "WEAK"
        ).sum(),

        "medium_count": (
            df["final_prediction"] == "MEDIUM"
        ).sum(),

        "strong_count": (
            df["final_prediction"] == "STRONG"
        ).sum(),

        "avg_speed": df["speed"].mean(),
        "avg_impact": df["impact"].mean(),
        "avg_power": df["power"].mean(),

        "std_power": df["power"].std(),
        "std_speed": df["speed"].std(),

        "best_swing": df.loc[
            df["power"].idxmax()
        ],

        "worst_swing": df.loc[
            df["power"].idxmin()
        ]
    }


# =====================================================
# SMART COACH
# =====================================================

def generate_suggestions(summary, comparison):

    s = []

    if comparison["gap_speed"] < -3:
        s.append(
            "Increase racket swing speed using forearm acceleration"
        )

    if comparison["gap_impact"] < -5:
        s.append(
            "Improve shuttle contact timing"
        )

    if comparison["gap_power"] < -500:
        s.append(
            "Focus on explosive smash power"
        )

    if summary["std_power"] > 400:
        s.append(
            "Improve consistency in swing power"
        )

    if len(s) == 0:
        s.append(
            "Performance is close to pro level 🚀"
        )

    return s[:5]


# =====================================================
# STABILITY SCORE
# =====================================================

def compute_stability_score(
    df,
    summary,
    consistency_scores
):

    power_score = summary["avg_power"] / (
        summary["avg_power"] +
        summary["std_power"] +
        1e-6
    )

    power_component = power_score * 10

    consistency_component = (
        consistency_scores["consistency_score"] / 10
    )

    stability = (
        (0.6 * power_component) +
        (0.4 * consistency_component)
    )

    return round(
        min(10, stability),
        2
    )


# =====================================================
# CONSISTENCY SCORES
# =====================================================

def compute_consistency_scores(df, summary):

    scores = {}

    speed_cv = (
        df["speed"].std() /
        (df["speed"].mean() + 1e-6)
    )

    impact_cv = (
        df["impact"].std() /
        (df["impact"].mean() + 1e-6)
    )

    power_cv = (
        df["power"].std() /
        (df["power"].mean() + 1e-6)
    )

    consistency_score = 100 * (
        1 - min(
            1,
            (speed_cv + impact_cv + power_cv) / 3
        )
    )

    scores["speed_cv"] = round(speed_cv, 3)
    scores["impact_cv"] = round(impact_cv, 3)
    scores["power_cv"] = round(power_cv, 3)

    scores["consistency_score"] = round(
        consistency_score,
        2
    )

    return scores


# =====================================================
# PLAYER TYPE CLASSIFICATION
# =====================================================

def classify_player_type(df, summary):

    stroke_dist = (
        df["stroke_type"].value_counts(normalize=True) * 100
    )

    smash_pct = stroke_dist.get("SMASH", 0)
    drop_pct = stroke_dist.get("DROP", 0)
    clear_pct = stroke_dist.get("CLEAR", 0)
    drive_pct = stroke_dist.get("DRIVE", 0)

    avg_power = summary["avg_power"]
    std_power = summary["std_power"]

    attacker_score = (
        (smash_pct * 0.6) +
        (avg_power / 100)
    )

    defender_score = (
        (clear_pct * 0.6) +
        (1 / (avg_power + 1e-6)) * 1000
    )

    balance = (
        100 -
        abs(smash_pct - clear_pct) -
        abs(drop_pct - drive_pct)
    )

    if (
        attacker_score > defender_score
        and smash_pct > 40
    ):

        player_type = "🔥 Attacker"

        explanation = (
            "You rely heavily on smashes and high power shots."
        )

    elif (
        defender_score > attacker_score
        and clear_pct > 35
    ):

        player_type = "🛡 Defensive Player"

        explanation = (
            "You focus on rallies, clears, and controlled gameplay."
        )

    elif balance > 60:

        player_type = "⚖ All-Rounder"

        explanation = (
            "Balanced mix of attacking and defensive strokes."
        )

    else:

        player_type = "🎯 Mixed Style Player"

        explanation = (
            "No dominant pattern detected clearly."
        )

    return {
        "player_type": player_type,
        "smash_pct": round(smash_pct, 2),
        "clear_pct": round(clear_pct, 2),
        "drop_pct": round(drop_pct, 2),
        "drive_pct": round(drive_pct, 2),
        "explanation": explanation
    }


# =====================================================
# FATIGUE DETECTION
# =====================================================

def fatigue_detection(df):

    n = len(df)

    if n < 10:
        return {
            "fatigue_score": 0,
            "speed_drop": 0,
            "impact_drop": 0,
            "power_drop": 0,
            "status": "Insufficient data"
        }

    early = df.iloc[:int(n * 0.4)]
    late = df.iloc[int(n * 0.6):]

    early_speed = early["speed"].mean()
    late_speed = late["speed"].mean()

    early_impact = early["impact"].mean()
    late_impact = late["impact"].mean()

    early_power = early["power"].mean()
    late_power = late["power"].mean()

    speed_drop = (
        (early_speed - late_speed) /
        (early_speed + 1e-6)
    ) * 100

    impact_drop = (
        (early_impact - late_impact) /
        (early_impact + 1e-6)
    ) * 100

    power_drop = (
        (early_power - late_power) /
        (early_power + 1e-6)
    ) * 100

    fatigue_score = np.mean([
        speed_drop,
        impact_drop,
        power_drop
    ])

    if fatigue_score < 10:
        status = "Fresh performance throughout session"

    elif fatigue_score < 25:
        status = "Mild fatigue detected"

    else:
        status = (
            "High fatigue detected – performance drop significant"
        )

    return {
        "fatigue_score": round(fatigue_score, 2),
        "speed_drop": round(speed_drop, 2),
        "impact_drop": round(impact_drop, 2),
        "power_drop": round(power_drop, 2),
        "status": status
    }


# =====================================================
# TECHNIQUE FEEDBACK
# Preserved from your original code.
# =====================================================

def technique_feedback(df, summary):

    feedback = []

    speed_low = df["speed"].quantile(0.25)
    speed_high = df["speed"].quantile(0.75)

    impact_low = df["impact"].quantile(0.25)
    impact_high = df["impact"].quantile(0.75)

    power_std = summary["std_power"]
    power_mean = summary["avg_power"]

    ratio = summary["avg_speed"] / (
        summary["avg_impact"] + 1e-6
    )

    if ratio > 1.4:
        feedback.append(
            "⚠ Timing Issue: High swing speed but low impact "
            "→ late shuttle contact likely"
        )

    elif ratio < 0.8:
        feedback.append(
            "⚠ Timing Issue: Strong impact but low speed "
            "→ early contact / poor acceleration"
        )

    else:
        feedback.append(
            "✔ Timing between speed and impact is balanced"
        )

    if summary["avg_impact"] < impact_low:
        feedback.append(
            "⚠ Impact Weakness: Below your normal baseline "
            "→ inconsistent racket contact"
        )

    elif summary["avg_impact"] < impact_high:
        feedback.append(
            "ℹ Impact: Moderate but improvable contact strength"
        )

    else:
        feedback.append(
            "✔ Strong and stable shuttle impact"
        )

    speed_std = df["speed"].std()

    if speed_std > df["speed"].mean() * 0.35:
        feedback.append(
            "⚠ Speed inconsistency: Swing speed varies too much "
            "between shots"
        )

    else:
        feedback.append(
            "✔ Stable swing speed across sessions"
        )

    if power_std > power_mean * 0.35:
        feedback.append(
            "⚠ Power inconsistency: Unstable shot strength "
            "across rallies"
        )

    else:
        feedback.append(
            "✔ Consistent power output"
        )

    stroke_dist = df["stroke_type"].value_counts()

    dominant = stroke_dist.idxmax()

    if dominant == "SMASH":
        feedback.append(
            "ℹ Play Style: Aggressive attacker (smash dominant)"
        )

    elif dominant == "DROP":
        feedback.append(
            "ℹ Play Style: Tactical control player"
        )

    elif dominant == "CLEAR":
        feedback.append(
            "ℹ Play Style: Defensive rally builder"
        )

    else:
        feedback.append(
            "ℹ Mixed playing style detected"
        )

    return feedback


# =====================================================
# TERMINAL DASHBOARD
# =====================================================

def print_dashboard(
    summary,
    comparison,
    gap_analysis,
    level,
    consistency_scores,
    stability_score,
    fatigue,
    player_profile,
    suggestions,
    df,
    counts,
    session_duration
):

    print("\n" + "═" * 60)
    print("🏸 SMART BADMINTON AI DASHBOARD")
    print("═" * 60)

    # ================================================
    # SESSION INFORMATION
    # ================================================

    print("\n⏱ SESSION INFORMATION")
    print("-" * 60)

    print(f"Total swings       : {counts['total']}")
    print(f"Real swings        : {counts['real']}")
    print(f"Dummy swings       : {counts['dummy']}")
    print(f"Unknown int_flag   : {counts['unknown']}")

    print(f"Session duration   : {session_duration}")

    # ================================================
    # PERFORMANCE METRICS
    # ================================================

    print("\n📊 PERFORMANCE METRICS")
    print("-" * 60)

    print(f"Analyzed real swings: {summary['total_swings']}")

    print(
        f"Weak / Med / Strong : "
        f"{summary['weak_count']} / "
        f"{summary['medium_count']} / "
        f"{summary['strong_count']}"
    )

    print(f"Avg Speed           : {summary['avg_speed']:.2f}")
    print(f"Avg Impact          : {summary['avg_impact']:.2f}")
    print(f"Avg Power           : {summary['avg_power']:.2f}")

    # ================================================
    # STROKE DISTRIBUTION
    # ================================================

    print("\n🏸 STROKE DISTRIBUTION")
    print("-" * 60)

    for stroke, count in df["stroke_type"].value_counts().items():

        bar = "█" * int(count / 3)

        print(
            f"{stroke:<8} | {count:<3} | {bar}"
        )

    # ================================================
    # BEST SWING
    # ================================================

    print("\n🔥 BEST SWING")
    b = summary["best_swing"]

    print(
        f"Speed:{b['speed']:.2f} "
        f"Impact:{b['impact']:.2f} "
        f"Power:{b['power']:.2f}"
    )

    # ================================================
    # WORST SWING
    # ================================================

    print("\n❄ WORST SWING")
    w = summary["worst_swing"]

    print(
        f"Speed:{w['speed']:.2f} "
        f"Impact:{w['impact']:.2f} "
        f"Power:{w['power']:.2f}"
    )

    # ================================================
    # PLAYER VS PRO
    # ================================================

    print("\n🏆 PLAYER vs PRO")
    print("-" * 60)

    print(
        f"{'Metric':<10}"
        f"{'You':<10}"
        f"{'Pro':<10}"
        f"{'Gap'}"
    )

    for p in ["speed", "impact", "power"]:

        print(
            f"{p:<10}"
            f"{comparison[f'player_avg_{p}']:<10}"
            f"{comparison[f'pro_avg_{p}']:<10}"
            f"{comparison[f'gap_{p}']}"
        )

    # ================================================
    # GAP ANALYSIS
    # ================================================

    print("\n🧠 GAP ANALYSIS")
    print("-" * 60)

    for feature, message in gap_analysis:
        print(f"• {feature:<8}: {message}")

    print(f"\n🏆 Player Level: {level}")

    # ================================================
    # CONSISTENCY
    # ================================================

    print("\n📊 CONSISTENCY ENGINE")
    print("-" * 60)

    print(f"Speed CV      : {consistency_scores['speed_cv']}")
    print(f"Impact CV     : {consistency_scores['impact_cv']}")
    print(f"Power CV      : {consistency_scores['power_cv']}")

    print(
        f"Consistency   : "
        f"{consistency_scores['consistency_score']}/100"
    )

    print(f"Stability     : {stability_score}/10")

    # ================================================
    # FATIGUE
    # ================================================

    print("\n🫀 FATIGUE ANALYSIS")
    print("-" * 60)

    print(f"Speed Drop    : {fatigue['speed_drop']}%")
    print(f"Impact Drop   : {fatigue['impact_drop']}%")
    print(f"Power Drop    : {fatigue['power_drop']}%")

    print(f"Status        : {fatigue['status']}")

    # ================================================
    # PLAYER PROFILE
    # ================================================

    print("\n🧬 PLAYER PROFILE")
    print("-" * 60)

    print(f"Type : {player_profile['player_type']}")
    print(player_profile["explanation"])

    # ================================================
    # SMART COACH
    # ================================================

    print("\n🎯 AI COACH RECOMMENDATIONS")
    print("-" * 60)

    for suggestion in suggestions:
        print(f"✔ {suggestion}")

    print("\n" + "═" * 60)
    print("🏁 SESSION COMPLETE - PERFORMANCE RECORDED")
    print("═" * 60)


# =====================================================
# MAIN CLASSIFIER
# =====================================================

def classify():

    print("\n🤖 SMART BADMINTON AI SYSTEM STARTED")

    # ================================================
    # GAME MODE: LOAD AND SPLIT COMPLETE CSV
    # ================================================

    print("\n📂 Loading game-mode ESP32 CSV...")

    df, dummy_df, counts = load_and_split_intflag(
        NEW_DATA_CSV,
        GAME_REAL_OUTPUT,
        GAME_DUMMY_OUTPUT
    )

    print("\n📊 GAME DATASET")
    print("-" * 60)

    print(f"Total records : {counts['total']}")
    print(f"Real swings   : {counts['real']}")
    print(f"Dummy swings  : {counts['dummy']}")
    print(f"Unknown flags : {counts['unknown']}")

    print(f"\nReal swings saved to:\n{GAME_REAL_OUTPUT}")
    print(f"Dummy swings saved to:\n{GAME_DUMMY_OUTPUT}")

    # ================================================
    # SESSION DURATION FROM COMPLETE GAME CSV
    # ================================================

    complete_game_df = pd.read_csv(NEW_DATA_CSV)

    _, session_duration = calculate_session_duration(
        complete_game_df
    )

    # ================================================
    # CONTINUE ONLY WITH REAL SWINGS
    # ================================================

    if df.empty:
        print("\n⚠ No real swings detected.")
        print("The split CSV files have still been saved.")
        print("No further ML classification can be performed.")
        return

    # ================================================
    # FEATURE ENGINEERING
    # ================================================

    df = df.dropna().copy()

    if df.empty:
        print("\n⚠ No usable real swings after removing NaN rows.")
        return

    df = add_features(df)
    df = add_stroke_features(df)

    # ================================================
    # LOAD CALIBRATION THRESHOLDS
    # ================================================

    th = load_or_create_threshold()

    weak_th = th["weak_threshold"].iloc[0]
    strong_th = th["strong_threshold"].iloc[0]

    # ================================================
    # LOAD EXISTING MODELS
    # ================================================

    swing_model, swing_features = load_swing_model()
    stroke_model, stroke_features = load_stroke_model()

    # ================================================
    # EXISTING PERFORMANCE CLASSIFIER MODEL
    # ================================================

    missing_swing = [
        f for f in swing_features
        if f not in df.columns
    ]

    if missing_swing:
        raise ValueError(
            f"Missing swing model features: {missing_swing}"
        )

    X_swing = df[swing_features]

    df["ml_swing"] = swing_model.predict(X_swing)

    # ================================================
    # STROKE PREDICTION
    # ================================================

    missing_stroke = [
        f for f in stroke_features
        if f not in df.columns
    ]

    print("\nMissing stroke features:", missing_stroke)

    if missing_stroke:
        raise ValueError(
            f"Missing stroke features: {missing_stroke}"
        )

    X_stroke = df[stroke_features]

    df["stroke_type"] = stroke_model.predict(X_stroke)

    # ================================================
    # RULE-BASED PERFORMANCE CLASSIFICATION
    # ================================================

    def rule(row):

        if row["power"] < weak_th:
            return "WEAK"

        elif row["power"] < strong_th:
            return "MEDIUM"

        else:
            return "STRONG"

    df["final_prediction"] = df.apply(
        rule,
        axis=1
    )

    # ================================================
    # SUMMARY + PRO COMPARISON
    # ================================================

    summary = get_session_summary(df)

    comparison = compare_with_pro(df)

    gap_analysis, level = generate_gap_analysis(
        comparison
    )

    suggestions = generate_suggestions(
        summary,
        comparison
    )

    fatigue = fatigue_detection(df)

    player_profile = classify_player_type(
        df,
        summary
    )

    consistency_scores = compute_consistency_scores(
        df,
        summary
    )

    stability_score = compute_stability_score(
        df,
        summary,
        consistency_scores
    )

    # ================================================
    # SAVE FINAL CLASSIFIED OUTPUT
    # ================================================

    save_csv(
        df,
        OUTPUT_FILE
    )

    print(
        f"\n✅ Final classified output saved to:\n{OUTPUT_FILE}"
    )

    # ================================================
    # TERMINAL DASHBOARD
    # ================================================

    print_dashboard(
        summary,
        comparison,
        gap_analysis,
        level,
        consistency_scores,
        stability_score,
        fatigue,
        player_profile,
        suggestions,
        df,
        counts,
        session_duration
    )


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