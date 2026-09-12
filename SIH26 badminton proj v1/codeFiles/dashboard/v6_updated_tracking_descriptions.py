import streamlit as st
import pandas as pd
import joblib
import os
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="🏸 Badminton AI Dashboard",
    page_icon="🏸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CUSTOM CSS
# =====================================================
st.markdown("""
<style>
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
    @keyframes glow {
        0% { box-shadow: 0 0 5px rgba(14, 165, 233, 0.3); }
        50% { box-shadow: 0 0 20px rgba(14, 165, 233, 0.6); }
        100% { box-shadow: 0 0 5px rgba(14, 165, 233, 0.3); }
    }

    .stApp {
        background: linear-gradient(135deg, #0a0e17 0%, #111827 50%, #0a0e17 100%);
    }
    .stApp, .stMarkdown, .stText {
        color: #e2e8f0 !important;
    }
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid rgba(56, 189, 248, 0.2);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        animation: fadeInUp 0.6s ease-out forwards;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 12px 35px rgba(14, 165, 233, 0.25);
        border-color: rgba(56, 189, 248, 0.5);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; }
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border-radius: 12px 12px 0 0;
        border: 1px solid rgba(56, 189, 248, 0.2);
        color: #94a3b8;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: linear-gradient(145deg, #334155 0%, #1e293b 100%);
        color: #38bdf8;
        transform: translateY(-3px);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(145deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: white !important;
        border: 1px solid rgba(56, 189, 248, 0.5) !important;
        box-shadow: 0 0 20px rgba(14, 165, 233, 0.4);
    }
    h1, h2, h3 { color: #f8fafc !important; font-weight: 700 !important; }
    h1 { text-shadow: 0 0 20px rgba(56, 189, 248, 0.3); }
    .stButton>button {
        background: linear-gradient(145deg, #0ea5e9 0%, #0284c7 100%);
        color: white; border: none; border-radius: 12px;
        padding: 10px 24px; font-weight: 600;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .stButton>button:hover {
        background: linear-gradient(145deg, #38bdf8 0%, #0ea5e9 100%);
        box-shadow: 0 4px 20px rgba(56, 189, 248, 0.5);
        transform: translateY(-3px) scale(1.05);
    }
    .stDataFrame {
        background: #1e293b; border-radius: 12px;
        border: 1px solid rgba(56, 189, 248, 0.2);
    }
    .stProgress > div > div {
        background: linear-gradient(90deg, #0ea5e9 0%, #38bdf8 100%);
        border-radius: 10px;
    }
    .stSelectbox > div > div {
        background: #1e293b; border-radius: 10px;
        border: 1px solid rgba(56, 189, 248, 0.2); color: white;
    }
    hr { border-color: rgba(56, 189, 248, 0.2); }
    .animated-card {
        animation: fadeInUp 0.7s ease-out forwards;
    }
    .hover-lift {
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .hover-lift:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 15px 40px rgba(14, 165, 233, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# FILE PATHS (portable defaults — override via upload)
# =====================================================
# These legacy absolute paths are kept only as optional fallbacks.
# Preferred path: user uploads both CSVs via the sidebar.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYER_HISTORY_DIR = os.path.join(BASE_DIR, "players")
os.makedirs(PLAYER_HISTORY_DIR, exist_ok=True)

CALIBRATION_CSV = os.path.join(BASE_DIR, "badminton_data.csv")
NEW_DATA_CSV = os.path.join(BASE_DIR, "badminton_data_session.csv")
THRESHOLD_FILE = os.path.join(BASE_DIR, "thresholdFile.csv")
SWING_MODEL_FILE = os.path.join(BASE_DIR, "swing_model.pkl")
STROKE_MODEL_FILE = os.path.join(BASE_DIR, "stroke_model.pkl")
PRO_DATASET_FILE = os.path.join(BASE_DIR, "pro_benchmark_dataset.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "final_classified_output_v4.csv")

# =====================================================
# PLAYER / LONGITUDINAL CSV STORAGE (CSV ONLY — NO SQLITE)
# =====================================================
LONGITUDINAL_COLUMNS = [
    "player_id", "player_name", "session_id", "date",
    "total_swings",
    "avg_speed", "avg_impact", "avg_power", "avg_efficiency",
    "weak_count", "medium_count", "strong_count", "strong_percentage",
    "workload_index", "workload_per_swing",
    "consistency_score", "stability_score",
    "beginning_power", "middle_power", "ending_power",
    "session_power_change_pct",
    "speed_drop_pct", "impact_drop_pct", "power_drop_pct",
    "fatigue_related_change",
    "endurance_maintenance_pct",
    "stroke_drop", "stroke_clear", "stroke_smash", "stroke_drive",
    "peak_power", "player_level", "player_type",
    "fitness_progress_score", "readiness_trend"
]


def safe_filename(value):
    value = str(value).strip()
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)
    return cleaned.strip("_") or "player"


def player_history_path(player_id, player_name=""):
    filename = safe_filename(player_id)
    if player_name:
        filename += "_" + safe_filename(player_name)
    return os.path.join(PLAYER_HISTORY_DIR, filename + ".csv")


def find_player_file(player_id):
    pid = safe_filename(player_id)
    if not os.path.isdir(PLAYER_HISTORY_DIR):
        return None
    matches = [
        os.path.join(PLAYER_HISTORY_DIR, f)
        for f in os.listdir(PLAYER_HISTORY_DIR)
        if f.lower().endswith(".csv") and f.split("_")[0] == pid
    ]
    return matches[0] if matches else None


def load_player_history(player_id):
    path = find_player_file(player_id)
    if path is None:
        return pd.DataFrame(columns=LONGITUDINAL_COLUMNS)
    try:
        hist = pd.read_csv(path)
        for col in LONGITUDINAL_COLUMNS:
            if col not in hist.columns:
                hist[col] = np.nan
        return hist[LONGITUDINAL_COLUMNS].sort_values("session_id")
    except Exception:
        return pd.DataFrame(columns=LONGITUDINAL_COLUMNS)


def get_existing_session_ids(player_id):
    hist = load_player_history(player_id)
    if hist.empty:
        return set()
    ids = pd.to_numeric(hist["session_id"], errors="coerce").dropna().astype(int)
    return set(ids.tolist())


def get_next_session_id(player_id):
    existing = get_existing_session_ids(player_id)
    return (max(existing) + 1) if existing else 1


def build_session_record(player_id, player_name, session_id, summary,
                         consistency_scores, stability_score, fatigue,
                         player_profile, level, df, fitness_progress_score=None,
                         readiness_trend=""):
    n = len(df)
    if n:
        first_end = max(1, n // 3)
        mid_start = first_end
        mid_end = max(mid_start + 1, (2 * n) // 3)
        beginning_power = float(df.iloc[:first_end]["power"].mean())
        middle_power = float(df.iloc[mid_start:mid_end]["power"].mean())
        ending_power = float(df.iloc[mid_end:]["power"].mean())
    else:
        beginning_power = middle_power = ending_power = 0.0

    session_power_change = (
        ((ending_power - beginning_power) / (abs(beginning_power) + 1e-6)) * 100
        if beginning_power else 0.0
    )

    endurance_maintenance = (
        (ending_power / (abs(beginning_power) + 1e-6)) * 100
        if beginning_power else 100.0
    )

    # Project-defined Training Workload Index: WEAK=1, MEDIUM=2, STRONG=3
    weak = int(summary["weak_count"])
    medium = int(summary["medium_count"])
    strong = int(summary["strong_count"])
    total = max(int(summary["total_swings"]), 1)
    workload_index = weak + (2 * medium) + (3 * strong)
    strong_pct = (strong / total) * 100

    # Decline-only fatigue-related change (max(0, drop))
    speed_drop = max(0.0, float(fatigue.get("speed_drop", 0)))
    impact_drop = max(0.0, float(fatigue.get("impact_drop", 0)))
    power_drop = max(0.0, float(fatigue.get("power_drop", 0)))
    fatigue_related_change = float(np.mean([speed_drop, impact_drop, power_drop]))

    stroke_counts = df["stroke_type"].value_counts() if "stroke_type" in df.columns else pd.Series(dtype=float)

    return {
        "player_id": str(player_id),
        "player_name": str(player_name),
        "session_id": int(session_id),
        "date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_swings": int(summary["total_swings"]),
        "avg_speed": round(float(summary["avg_speed"]), 3),
        "avg_impact": round(float(summary["avg_impact"]), 3),
        "avg_power": round(float(summary["avg_power"]), 3),
        "avg_efficiency": round(float(summary["avg_efficiency"]), 3),
        "weak_count": weak,
        "medium_count": medium,
        "strong_count": strong,
        "strong_percentage": round(strong_pct, 2),
        "workload_index": int(workload_index),
        "workload_per_swing": round(workload_index / total, 3),
        "consistency_score": round(float(consistency_scores["consistency_score"]), 2),
        "stability_score": round(float(stability_score), 2),
        "beginning_power": round(beginning_power, 3),
        "middle_power": round(middle_power, 3),
        "ending_power": round(ending_power, 3),
        "session_power_change_pct": round(session_power_change, 2),
        "speed_drop_pct": round(speed_drop, 2),
        "impact_drop_pct": round(impact_drop, 2),
        "power_drop_pct": round(power_drop, 2),
        "fatigue_related_change": round(fatigue_related_change, 2),
        "endurance_maintenance_pct": round(endurance_maintenance, 2),
        "stroke_drop": int(stroke_counts.get("DROP", 0)),
        "stroke_clear": int(stroke_counts.get("CLEAR", 0)),
        "stroke_smash": int(stroke_counts.get("SMASH", 0)),
        "stroke_drive": int(stroke_counts.get("DRIVE", 0)),
        "peak_power": round(float(df["power"].max()), 3) if len(df) else 0.0,
        "player_level": str(level),
        "player_type": str(player_profile["player_type"]),
        "fitness_progress_score": round(float(fitness_progress_score), 1) if fitness_progress_score is not None else np.nan,
        "readiness_trend": str(readiness_trend) if readiness_trend else ""
    }


def append_player_session(record):
    """Append a session row. Never overwrites an existing session_id."""
    player_id = record["player_id"]
    player_name = record["player_name"]
    path = find_player_file(player_id)

    if path is None:
        path = player_history_path(player_id, player_name)

    if os.path.exists(path):
        history = pd.read_csv(path)
        if "session_id" in history.columns:
            ids = pd.to_numeric(history["session_id"], errors="coerce")
            if int(record["session_id"]) in ids.dropna().astype(int).tolist():
                return False, path, (
                    f"Session {int(record['session_id'])} already exists for this player. "
                    "Existing data will not be overwritten. Please choose another Session ID."
                )

    new_row = pd.DataFrame([record], columns=LONGITUDINAL_COLUMNS)

    if os.path.exists(path):
        history = pd.read_csv(path)
        for col in LONGITUDINAL_COLUMNS:
            if col not in history.columns:
                history[col] = np.nan
        history = history[LONGITUDINAL_COLUMNS]
        history = pd.concat([history, new_row], ignore_index=True)
    else:
        history = new_row

    history["session_id"] = pd.to_numeric(history["session_id"], errors="coerce")
    history = history.sort_values("session_id").reset_index(drop=True)
    history.to_csv(path, index=False)
    return True, path, "Session saved successfully."


def percentage_change(first, last):
    if pd.isna(first) or pd.isna(last) or abs(float(first)) < 1e-9:
        return np.nan
    return ((float(last) - float(first)) / abs(float(first))) * 100


def add_longitudinal_derived_metrics(history):
    h = history.copy()
    h = h.sort_values("session_id").reset_index(drop=True)

    numeric_cols = [
        "total_swings", "avg_speed", "avg_impact", "avg_power",
        "avg_efficiency", "strong_percentage", "workload_index",
        "workload_per_swing", "consistency_score", "stability_score",
        "beginning_power", "middle_power", "ending_power",
        "session_power_change_pct", "fatigue_related_change",
        "endurance_maintenance_pct",
        "stroke_drop", "stroke_clear", "stroke_smash", "stroke_drive",
        "peak_power", "fitness_progress_score"
    ]
    for col in numeric_cols:
        if col in h.columns:
            h[col] = pd.to_numeric(h[col], errors="coerce")

    if "endurance_maintenance_pct" not in h.columns or h["endurance_maintenance_pct"].isna().all():
        h["endurance_maintenance_pct"] = np.where(
            h["beginning_power"].abs() > 1e-9,
            (h["ending_power"] / h["beginning_power"]) * 100,
            np.nan
        )

    if len(h) > 1:
        h["fatigue_change_from_previous"] = h["fatigue_related_change"].diff()
        h["power_change_from_previous_pct"] = h["avg_power"].pct_change() * 100
        h["consistency_change_from_previous"] = h["consistency_score"].diff()
    else:
        h["fatigue_change_from_previous"] = np.nan
        h["power_change_from_previous_pct"] = np.nan
        h["consistency_change_from_previous"] = np.nan

    return h


def compute_readiness_trend(history):
    """Performance-based readiness / recovery trend (not physiological recovery)."""
    if history is None or len(history) < 2:
        return "Insufficient history for readiness trend"
    h = add_longitudinal_derived_metrics(history)
    last = h.iloc[-1]
    prev = h.iloc[-2]
    power_change = percentage_change(prev["avg_power"], last["avg_power"])
    fatigue_last = float(last.get("fatigue_related_change", 0) or 0)
    fatigue_prev = float(prev.get("fatigue_related_change", 0) or 0)

    if pd.notna(power_change) and power_change >= 5 and fatigue_last <= fatigue_prev + 2:
        return "Good performance recovery trend relative to previous session"
    if pd.notna(power_change) and power_change <= -8:
        return "Possible incomplete performance recovery trend (lower output vs previous session)"
    return "Stable performance readiness trend relative to previous session"


def compute_progress_indicator(history):
    """Project-defined Fitness & Performance Progress Indicator (0–100)."""
    if history is None or history.empty:
        return 50.0
    h = add_longitudinal_derived_metrics(history)
    first = h.iloc[0]
    last = h.iloc[-1]
    components = []
    for col in ["avg_power", "avg_speed", "consistency_score", "strong_percentage"]:
        change = percentage_change(first.get(col), last.get(col))
        if pd.notna(change):
            components.append(np.clip(change, -50, 50))
    progress = 50 + (np.mean(components) if components else 0)
    return float(np.clip(progress, 0, 100))


def generate_longitudinal_feedback(history):
    if history.empty:
        return {
            "strengths": [],
            "improvements": [],
            "training_focus": [],
            "progress_score": 50.0,
            "readiness_trend": "No history yet",
            "final_feedback": "No longitudinal session history is available yet."
        }

    h = add_longitudinal_derived_metrics(history)
    first = h.iloc[0]
    last = h.iloc[-1]
    progress = compute_progress_indicator(h)
    readiness = compute_readiness_trend(h)

    strengths = []
    improvements = []
    training_focus = []

    metrics = [
        ("avg_power", "Swing Power Index"),
        ("avg_speed", "Swing Speed Index"),
        ("consistency_score", "Consistency"),
        ("strong_percentage", "Strong-intensity percentage"),
        ("total_swings", "Training volume")
    ]

    for col, label in metrics:
        if pd.notna(first.get(col)) and pd.notna(last.get(col)):
            change = percentage_change(first[col], last[col])
            if pd.notna(change):
                if change >= 10:
                    strengths.append(
                        f"{label} improved by {change:.1f}% from Session {int(first['session_id'])} "
                        f"to Session {int(last['session_id'])}."
                    )
                elif change <= -10:
                    improvements.append(
                        f"{label} decreased by {abs(change):.1f}% across the tracked sessions."
                    )

    if len(h) >= 2:
        fatigue_first = float(first.get("fatigue_related_change", 0) or 0)
        fatigue_last = float(last.get("fatigue_related_change", 0) or 0)
        if fatigue_last < fatigue_first - 2:
            strengths.append(
                "Fatigue-related performance change is lower in the latest session, "
                "suggesting better performance maintenance."
            )
        elif fatigue_last > fatigue_first + 5:
            improvements.append(
                "The latest session shows a larger fatigue-related performance change than the baseline."
            )

        end_maint = float(last.get("endurance_maintenance_pct", 100) or 100)
        if end_maint >= 95:
            strengths.append("Late-session Swing Power Index is maintained close to early-session values.")
        elif end_maint < 85:
            improvements.append(
                "Late-session Swing Power Index falls noticeably below early-session values; "
                "endurance-related performance maintenance needs attention."
            )

    if float(last.get("consistency_score", 0) or 0) < 60:
        training_focus.append("Work on repeatable swing mechanics and controlled shot execution.")
    if float(last.get("avg_power", 0) or 0) < float(first.get("avg_power", 0) or 0) * 0.95:
        training_focus.append("Use progressive power and explosive-swing drills while maintaining technique.")
    if float(last.get("strong_percentage", 0) or 0) < 20:
        training_focus.append("Include controlled high-intensity stroke sets to build badminton-specific performance capacity.")
    if float(last.get("endurance_maintenance_pct", 100) or 100) < 90:
        training_focus.append("Use interval-based rally drills to improve late-session performance maintenance.")
    if float(last.get("fatigue_related_change", 0) or 0) > 15:
        training_focus.append(
            "Monitor performance changes during longer sessions and include adequate recovery between high-intensity sets."
        )

    if not strengths:
        strengths.append("The available sessions do not yet show a large improvement in the tracked metrics.")
    if not improvements:
        improvements.append("No major negative trend was identified in the available longitudinal metrics.")
    if not training_focus:
        training_focus.append("Continue progressive training and monitor the next sessions against the player's personal baseline.")

    final_feedback = (
        f"Across {len(h)} tracked sessions, the player's badminton-specific performance profile "
        f"shows a project-defined Fitness & Performance Progress Indicator of {progress:.1f}/100. "
        f"Readiness trend: {readiness}. "
        f"The latest session should be interpreted against the player's own historical baseline, "
        f"considering training workload, intensity, consistency, endurance-related performance maintenance "
        f"and fatigue-related performance changes together. "
        "These are racket-derived, project-defined performance indicators — not direct physiological measurements."
    )

    return {
        "strengths": strengths[:6],
        "improvements": improvements[:6],
        "training_focus": training_focus[:6],
        "progress_score": round(progress, 1),
        "readiness_trend": readiness,
        "final_feedback": final_feedback
    }


def longitudinal_stroke_long_table(history):
    rows = []
    for _, r in history.iterrows():
        rows.append({
            "Session": int(r["session_id"]),
            "DROP": int(r.get("stroke_drop", 0)),
            "CLEAR": int(r.get("stroke_clear", 0)),
            "SMASH": int(r.get("stroke_smash", 0)),
            "DRIVE": int(r.get("stroke_drive", 0))
        })
    return pd.DataFrame(rows)


def consecutive_session_changes(history):
    """Return a table of consecutive-session percentage changes."""
    h = add_longitudinal_derived_metrics(history)
    if len(h) < 2:
        return pd.DataFrame()
    rows = []
    for i in range(1, len(h)):
        prev = h.iloc[i - 1]
        curr = h.iloc[i]
        rows.append({
            "From Session": int(prev["session_id"]),
            "To Session": int(curr["session_id"]),
            "Power Δ%": round(percentage_change(prev["avg_power"], curr["avg_power"]), 2)
            if pd.notna(percentage_change(prev["avg_power"], curr["avg_power"])) else np.nan,
            "Speed Δ%": round(percentage_change(prev["avg_speed"], curr["avg_speed"]), 2)
            if pd.notna(percentage_change(prev["avg_speed"], curr["avg_speed"])) else np.nan,
            "Consistency Δ": round(float(curr["consistency_score"]) - float(prev["consistency_score"]), 2)
            if pd.notna(curr["consistency_score"]) and pd.notna(prev["consistency_score"]) else np.nan,
            "Workload Δ": int(curr["workload_index"]) - int(prev["workload_index"])
            if pd.notna(curr["workload_index"]) and pd.notna(prev["workload_index"]) else np.nan,
            "Fatigue-related Δ": round(
                float(curr.get("fatigue_related_change", 0) or 0) -
                float(prev.get("fatigue_related_change", 0) or 0), 2
            )
        })
    return pd.DataFrame(rows)


# =====================================================
# FEATURE ENGINEERING
# =====================================================
def add_features(df):
    df = df.copy()
    df["power"] = df["speed"] * df["impact"]          # Swing Power Index (project-defined)
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)  # Impact Efficiency Index
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
# LOAD MODELS / THRESHOLDS
# =====================================================
def load_swing_model():
    model_pack = joblib.load(SWING_MODEL_FILE)
    return model_pack["model"], model_pack["features"]


def load_stroke_model():
    model_pack = joblib.load(STROKE_MODEL_FILE)
    return model_pack["model"], model_pack["features"]


def load_or_create_threshold(calibration_df=None, force_recalibrate=False):
    """
    If calibration_df is provided (uploaded), thresholds are recalculated from it
    and written to THRESHOLD_FILE so behaviour is transparent.
    Otherwise the existing threshold file is reused when present.
    """
    if force_recalibrate or (calibration_df is not None) or (not os.path.exists(THRESHOLD_FILE)):
        if calibration_df is None:
            if not os.path.exists(CALIBRATION_CSV):
                raise FileNotFoundError(
                    "Calibration CSV not found. Please upload a Calibration CSV."
                )
            df = pd.read_csv(CALIBRATION_CSV)
        else:
            df = calibration_df.copy()

        required = ["speed", "impact", "duration"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise Exception(f"Calibration CSV missing columns: {missing}")

        df = df[required].dropna().head(30)
        if len(df) == 0:
            raise Exception("Calibration CSV contains no usable rows.")

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
        return threshold_df, True  # recalibrated
    return pd.read_csv(THRESHOLD_FILE), False


# =====================================================
# PRO COMPARISON & GAP ANALYSIS
# =====================================================
def compare_with_pro(player_df):
    if not os.path.exists(PRO_DATASET_FILE):
        # Graceful fallback when pro dataset is absent
        cols = ["speed", "impact", "duration", "power", "efficiency"]
        player_avg = player_df[cols].mean()
        comparison = {}
        for col in cols:
            p = player_avg[col]
            comparison[f"player_avg_{col}"] = round(p, 2)
            comparison[f"pro_avg_{col}"] = round(p, 2)
            comparison[f"gap_{col}"] = 0.0
        return comparison

    pro_df = pd.read_csv(PRO_DATASET_FILE)
    cols = ["speed", "impact", "duration", "power", "efficiency"]
    player_avg = player_df[cols].mean()
    pro_avg = pro_df[cols].mean()
    comparison = {}
    for col in cols:
        p = player_avg[col]
        pr = pro_avg[col]
        gap = pr - p if col == "duration" else p - pr
        comparison[f"player_avg_{col}"] = round(p, 2)
        comparison[f"pro_avg_{col}"] = round(pr, 2)
        comparison[f"gap_{col}"] = round(gap, 2)
    return comparison


def generate_gap_analysis(comparison):
    analysis = []
    if comparison["gap_speed"] < -5:
        analysis.append(("Swing Speed Index", "Major deficit in swing acceleration"))
    elif comparison["gap_speed"] < -2:
        analysis.append(("Swing Speed Index", "Moderate speed improvement needed"))
    else:
        analysis.append(("Swing Speed Index", "Close to pro level"))
    if comparison["gap_impact"] < -8:
        analysis.append(("Impact Index", "Weak shuttle contact force (proxy)"))
    elif comparison["gap_impact"] < -3:
        analysis.append(("Impact Index", "Timing needs refinement"))
    else:
        analysis.append(("Impact Index", "Good striking control"))
    if comparison["gap_power"] < -700:
        analysis.append(("Swing Power Index", "Very low explosive strength (proxy)"))
    elif comparison["gap_power"] < -300:
        analysis.append(("Swing Power Index", "Power generation needs work"))
    else:
        analysis.append(("Swing Power Index", "Strong power output (proxy)"))
    total_gap = comparison["gap_power"]
    if total_gap > -200:
        level = "Near Pro Level 🏆"
    elif total_gap > -600:
        level = "Intermediate Player"
    else:
        level = "Needs Major Improvement"
    return analysis, level


# =====================================================
# SESSION SUMMARY & COACHING HELPERS
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
        "avg_efficiency": df["efficiency"].mean() if "efficiency" in df.columns else 0,
        "std_power": df["power"].std(),
        "std_speed": df["speed"].std(),
        "best_swing": df.loc[df["power"].idxmax()] if len(df) else None,
        "worst_swing": df.loc[df["power"].idxmin()] if len(df) else None
    }


def generate_suggestions(summary, comparison):
    s = []
    if comparison["gap_speed"] < -3:
        s.append("Increase racket swing speed using forearm acceleration drills")
    if comparison["gap_impact"] < -5:
        s.append("Improve shuttle contact timing and clean stroke execution")
    if comparison["gap_power"] < -500:
        s.append("Focus on explosive smash power generation while preserving technique")
    if summary["std_power"] > 400:
        s.append("Improve consistency in Swing Power Index across repeated swings")
    if len(s) == 0:
        s.append("Performance indices are close to the professional benchmark 🚀")
    return s[:5]


def compute_stability_score(df, summary, consistency_scores):
    power_score = summary["avg_power"] / (summary["avg_power"] + summary["std_power"] + 1e-6)
    power_component = power_score * 10
    consistency_component = consistency_scores["consistency_score"] / 10
    stability = (0.6 * power_component) + (0.4 * consistency_component)
    return round(min(10, stability), 2)


def compute_consistency_scores(df, summary):
    scores = {}
    speed_cv = df["speed"].std() / (df["speed"].mean() + 1e-6)
    impact_cv = df["impact"].std() / (df["impact"].mean() + 1e-6)
    power_cv = df["power"].std() / (df["power"].mean() + 1e-6)
    consistency_score = 100 * (1 - min(1, (speed_cv + impact_cv + power_cv) / 3))
    scores["speed_cv"] = round(speed_cv, 3)
    scores["impact_cv"] = round(impact_cv, 3)
    scores["power_cv"] = round(power_cv, 3)
    scores["consistency_score"] = round(consistency_score, 2)
    return scores


def classify_player_type(df, summary):
    stroke_dist = df["stroke_type"].value_counts(normalize=True) * 100
    smash_pct = stroke_dist.get("SMASH", 0)
    drop_pct = stroke_dist.get("DROP", 0)
    clear_pct = stroke_dist.get("CLEAR", 0)
    drive_pct = stroke_dist.get("DRIVE", 0)
    avg_power = summary["avg_power"]
    attacker_score = (smash_pct * 0.6) + (avg_power / 100)
    defender_score = (clear_pct * 0.6) + (1 / (avg_power + 1e-6)) * 1000
    balance = 100 - abs(smash_pct - clear_pct) - abs(drop_pct - drive_pct)
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
    """
    Fatigue-related performance change (decline-only).
    Not a physiological / medical fatigue diagnosis.
    """
    n = len(df)
    if n < 10:
        return {
            "fatigue_score": 0, "speed_drop": 0, "impact_drop": 0,
            "power_drop": 0, "status": "Insufficient data for fatigue-related analysis"
        }
    early = df.iloc[:int(n * 0.4)]
    late = df.iloc[int(n * 0.6):]
    speed_drop = max(0.0, ((early["speed"].mean() - late["speed"].mean()) / (early["speed"].mean() + 1e-6)) * 100)
    impact_drop = max(0.0, ((early["impact"].mean() - late["impact"].mean()) / (early["impact"].mean() + 1e-6)) * 100)
    power_drop = max(0.0, ((early["power"].mean() - late["power"].mean()) / (early["power"].mean() + 1e-6)) * 100)
    fatigue_score = float(np.mean([speed_drop, impact_drop, power_drop]))
    if fatigue_score < 10:
        status = "Stable performance throughout session (low fatigue-related change)"
    elif fatigue_score < 25:
        status = "Mild fatigue-related performance change detected"
    else:
        status = "Notable fatigue-related performance change – late-session decline significant"
    return {
        "fatigue_score": round(fatigue_score, 2),
        "speed_drop": round(speed_drop, 2),
        "impact_drop": round(impact_drop, 2),
        "power_drop": round(power_drop, 2),
        "status": status
    }


def technique_feedback(df, summary):
    feedback = []
    impact_low = df["impact"].quantile(0.25)
    impact_high = df["impact"].quantile(0.75)
    power_std = summary["std_power"]
    power_mean = summary["avg_power"]
    ratio = summary["avg_speed"] / (summary["avg_impact"] + 1e-6)
    if ratio > 1.4:
        feedback.append("⚠ Timing Issue: High Swing Speed Index but low Impact Index → late shuttle contact likely")
    elif ratio < 0.8:
        feedback.append("⚠ Timing Issue: Strong Impact Index but low Swing Speed Index → early contact / poor acceleration")
    else:
        feedback.append("✔ Timing between Swing Speed Index and Impact Index is balanced")
    if summary["avg_impact"] < impact_low:
        feedback.append("⚠ Impact Index weakness: Below your normal baseline → inconsistent racket contact")
    elif summary["avg_impact"] < impact_high:
        feedback.append("ℹ Impact Index: Moderate but improvable contact strength")
    else:
        feedback.append("✔ Strong and stable Impact Index")
    speed_std = df["speed"].std()
    if speed_std > df["speed"].mean() * 0.35:
        feedback.append("⚠ Speed inconsistency: Swing Speed Index varies too much between shots")
    else:
        feedback.append("✔ Stable Swing Speed Index across the session")
    if power_std > power_mean * 0.35:
        feedback.append("⚠ Power inconsistency: Unstable Swing Power Index across rallies")
    else:
        feedback.append("✔ Consistent Swing Power Index")
    stroke_dist = df["stroke_type"].value_counts()
    dominant = stroke_dist.idxmax() if len(stroke_dist) else "MIXED"
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
# PDF REPORT GENERATOR
# =====================================================
def generate_pdf_report(df, summary, comparison, gap_analysis, level, consistency_scores,
                        stability_score, fatigue, player_profile, suggestions):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'], fontSize=28,
        textColor=rl_colors.HexColor('#0ea5e9'), spaceAfter=20,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading2'], fontSize=16,
        textColor=rl_colors.HexColor('#0ea5e9'), spaceAfter=12,
        spaceBefore=15, fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'CustomBody', parent=styles['BodyText'], fontSize=10,
        textColor=rl_colors.HexColor('#334155'), spaceAfter=6, alignment=TA_LEFT
    )

    story = []
    story.append(Paragraph("SMART BADMINTON AI", title_style))
    story.append(Paragraph("Comprehensive Session Report", ParagraphStyle(
        'Subtitle', parent=styles['Normal'], fontSize=14,
        textColor=rl_colors.HexColor('#64748b'), alignment=TA_CENTER, spaceAfter=20
    )))
    story.append(Spacer(1, 10))

    story.append(Paragraph("SESSION OVERVIEW", heading_style))
    overview_data = [
        ['Metric', 'Value'],
        ['Total Swings', str(int(summary['total_swings']))],
        ['Weak Swings', str(int(summary['weak_count']))],
        ['Medium Swings', str(int(summary['medium_count']))],
        ['Strong Swings', str(int(summary['strong_count']))],
        ['Player Level', level],
        ['Player Type', player_profile['player_type'].replace('🔥', '').replace('🛡', '').replace('⚖', '').replace('🎯', '').strip()]
    ]
    overview_table = Table(overview_data, colWidths=[3 * inch, 3 * inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#0ea5e9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), rl_colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.HexColor('#334155')),
        ('GRID', (0, 0), (-1, -1), 1, rl_colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.HexColor('#f8fafc'), rl_colors.HexColor('#f1f5f9')]),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("PERFORMANCE INDICES", heading_style))
    perf_data = [
        ['Metric', 'Your Average', 'Pro Average', 'Gap'],
        ['Swing Speed Index', f"{summary['avg_speed']:.2f}", f"{comparison['pro_avg_speed']:.2f}", f"{comparison['gap_speed']:.2f}"],
        ['Impact Index', f"{summary['avg_impact']:.2f}", f"{comparison['pro_avg_impact']:.2f}", f"{comparison['gap_impact']:.2f}"],
        ['Swing Power Index', f"{summary['avg_power']:.2f}", f"{comparison['pro_avg_power']:.2f}", f"{comparison['gap_power']:.2f}"],
        ['Impact Efficiency Index', f"{summary['avg_efficiency']:.2f}", f"{comparison['pro_avg_efficiency']:.2f}", f"{comparison['gap_efficiency']:.2f}"],
        ['Consistency Score', f"{consistency_scores['consistency_score']:.2f}/100", 'N/A', 'N/A'],
        ['Stability Score', f"{stability_score}/10", 'N/A', 'N/A']
    ]
    perf_table = Table(perf_data, colWidths=[2.2 * inch, 1.4 * inch, 1.4 * inch, 1.2 * inch])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#0ea5e9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), rl_colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.HexColor('#334155')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, rl_colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.HexColor('#f8fafc'), rl_colors.HexColor('#f1f5f9')]),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    story.append(perf_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("STROKE DISTRIBUTION", heading_style))
    stroke_data = [
        ['Stroke Type', 'Percentage'],
        ['SMASH', f"{player_profile['smash_pct']:.1f}%"],
        ['CLEAR', f"{player_profile['clear_pct']:.1f}%"],
        ['DROP', f"{player_profile['drop_pct']:.1f}%"],
        ['DRIVE', f"{player_profile['drive_pct']:.1f}%"]
    ]
    stroke_table = Table(stroke_data, colWidths=[3 * inch, 3 * inch])
    stroke_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#f472b6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), rl_colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.HexColor('#334155')),
        ('GRID', (0, 0), (-1, -1), 1, rl_colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.HexColor('#fdf2f8'), rl_colors.HexColor('#fce7f3')]),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(stroke_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("GAP ANALYSIS", heading_style))
    for feature, msg in gap_analysis:
        if "deficit" in msg.lower() or "weak" in msg.lower() or "low" in msg.lower():
            c = rl_colors.HexColor('#ef4444')
        elif "improvement" in msg.lower() or "needs" in msg.lower() or "work" in msg.lower():
            c = rl_colors.HexColor('#fbbf24')
        else:
            c = rl_colors.HexColor('#34d399')
        story.append(Paragraph(f"<b>{feature}</b>: {msg}", ParagraphStyle(
            'GapItem', parent=body_style, textColor=c, fontSize=11, spaceAfter=8
        )))
    story.append(Spacer(1, 10))

    story.append(Paragraph("FATIGUE-RELATED & CONSISTENCY", heading_style))
    fatigue_data = [
        ['Metric', 'Value'],
        ['Status', fatigue['status']],
        ['Fatigue-related Change', f"{fatigue['fatigue_score']:.2f}%"],
        ['Speed Drop %', f"{fatigue['speed_drop']:.2f}%"],
        ['Impact Drop %', f"{fatigue['impact_drop']:.2f}%"],
        ['Power Drop %', f"{fatigue['power_drop']:.2f}%"],
        ['Consistency Score', f"{consistency_scores['consistency_score']:.2f}/100"]
    ]
    fatigue_table = Table(fatigue_data, colWidths=[3 * inch, 3 * inch])
    fatigue_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#34d399')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), rl_colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.HexColor('#334155')),
        ('GRID', (0, 0), (-1, -1), 1, rl_colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.HexColor('#f0fdf4'), rl_colors.HexColor('#dcfce7')]),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    story.append(fatigue_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("AI COACH RECOMMENDATIONS", heading_style))
    for i, suggestion in enumerate(suggestions, 1):
        story.append(Paragraph(f"{i}. {suggestion}", ParagraphStyle(
            'Suggestion', parent=body_style, fontSize=11, spaceAfter=10,
            textColor=rl_colors.HexColor('#1e293b'), leftIndent=20
        )))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "-- Generated by Smart Badminton AI System | Project-defined performance indices (not physiological measurements) --",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8,
                       textColor=rl_colors.HexColor('#94a3b8'), alignment=TA_CENTER, spaceBefore=30)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# =====================================================
# MAIN CLASSIFIER (called only after explicit start)
# =====================================================
def classify(game_bytes, calibration_bytes):
    """
    Requires both game_bytes and calibration_bytes (uploaded files).
    Does not fall back to hard-coded paths for the main analytics path.
    """
    if game_bytes is None or calibration_bytes is None:
        raise ValueError("Both Calibration CSV and Game/Session CSV must be uploaded.")

    df = pd.read_csv(io.BytesIO(game_bytes))
    calibration_df = pd.read_csv(io.BytesIO(calibration_bytes))

    df = df.dropna().copy()
    required = ["speed", "impact", "duration"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise Exception(f"Game CSV missing columns: {missing}")

    df = add_features(df)
    df = add_stroke_features(df)

    th, recalibrated = load_or_create_threshold(calibration_df, force_recalibrate=True)
    weak_th = th["weak_threshold"].iloc[0]
    strong_th = th["strong_threshold"].iloc[0]

    # Models are optional for demo robustness — if missing, intensity still works via rules
    try:
        swing_model, swing_features = load_swing_model()
        missing_swing = [f for f in swing_features if f not in df.columns]
        if missing_swing:
            raise Exception(f"Missing swing-model features: {missing_swing}")
        X_swing = df[swing_features]
        df["ml_swing"] = swing_model.predict(X_swing)
    except Exception:
        df["ml_swing"] = "N/A"

    try:
        stroke_model, stroke_features = load_stroke_model()
        missing = [f for f in stroke_features if f not in df.columns]
        if missing:
            raise Exception(f"Missing stroke features: {missing}")
        X_stroke = df.reindex(columns=stroke_features)
        df["stroke_type"] = stroke_model.predict(X_stroke)
    except Exception:
        # Fallback: simple rule so the rest of the pipeline can still run in demos
        df["stroke_type"] = "DRIVE"

    def rule(row):
        if row["power"] < weak_th:
            return "WEAK"
        elif row["power"] < strong_th:
            return "MEDIUM"
        else:
            return "STRONG"

    df["final_prediction"] = df.apply(rule, axis=1)

    summary = get_session_summary(df)
    comparison = compare_with_pro(df)
    gap_analysis, level = generate_gap_analysis(comparison)
    suggestions = generate_suggestions(summary, comparison)
    fatigue = fatigue_detection(df)
    player_profile = classify_player_type(df, summary)
    consistency_scores = compute_consistency_scores(df, summary)
    stability_score = compute_stability_score(df, summary, consistency_scores)

    return (
        df, summary, comparison, gap_analysis, level, consistency_scores,
        stability_score, fatigue, player_profile, suggestions, recalibrated
    )


# =====================================================
# HELPER UI CHARTS
# =====================================================
def create_gauge_chart(value, title, max_val=100):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16, 'color': '#e2e8f0'}},
        gauge={
            'axis': {'range': [0, max_val], 'tickcolor': '#94a3b8'},
            'bar': {'color': '#0ea5e9'},
            'bgcolor': 'rgba(30, 41, 59, 0.5)',
            'borderwidth': 2,
            'bordercolor': 'rgba(56, 189, 248, 0.3)',
            'steps': [
                {'range': [0, max_val * 0.33], 'color': 'rgba(239, 68, 68, 0.2)'},
                {'range': [max_val * 0.33, max_val * 0.66], 'color': 'rgba(234, 179, 8, 0.2)'},
                {'range': [max_val * 0.66, max_val], 'color': 'rgba(34, 197, 94, 0.2)'}
            ],
            'threshold': {'line': {'color': '#38bdf8', 'width': 4}, 'thickness': 0.75, 'value': value}
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'), height=250)
    return fig


# =====================================================
# SESSION LEVEL PERFORMANCE — INFERENCE & RENDER (NEW)
# Reuses existing summary / consistency / fatigue / df values.
# All wording is badminton-specific and non-medical.
# =====================================================
def _safe_pct(part, total):
    if total is None or total == 0 or pd.isna(total):
        return 0.0
    return round((float(part) / float(total)) * 100, 1)


def compute_session_duration_minutes(df):
    """Best-effort session duration from available columns.
    Returns (minutes_float, human_str) or (None, 'Not available').

    Supports:
    1. Real datetime strings in timestamp/time/datetime/ts
    2. Numeric elapsed milliseconds (ESP32 millis since first swing)  ← your CSV format
    3. Numeric elapsed seconds
    4. Fallback: sum of per-swing duration column
    """
    if df is None or len(df) == 0:
        return None, "Not available for this session"

    # ---- 1 & 2. timestamp / time / datetime / ts / elapsed columns ----
    for col in ["timestamp", "time", "datetime", "ts", "elapsed_ms", "elapsed"]:
        if col not in df.columns:
            continue

        series = df[col]

        # Try real datetime first
        try:
            ts = pd.to_datetime(series, errors="coerce").dropna()
            # Only accept if it actually looks like real datetimes (year > 1971)
            if len(ts) >= 2 and ts.max().year > 1971:
                delta = (ts.max() - ts.min()).total_seconds()
                if delta > 0:
                    mins = int(delta // 60)
                    secs = int(delta % 60)
                    return delta / 60.0, f"{mins} min {secs:02d} sec"
        except Exception:
            pass

        # Treat as numeric elapsed time (ESP32 style: 0, 1410, 3713, ... ms)
        try:
            vals = pd.to_numeric(series, errors="coerce").dropna()
            if len(vals) >= 2:
                delta_raw = float(vals.max() - vals.min())
                if delta_raw <= 0:
                    continue

                # Heuristic: values > 500 almost certainly milliseconds
                # (a short session of a few seconds already produces thousands of ms)
                if delta_raw >= 500 or float(vals.max()) > 500:
                    delta_sec = delta_raw / 1000.0          # milliseconds → seconds
                else:
                    delta_sec = delta_raw                   # already seconds

                if delta_sec > 0:
                    mins = int(delta_sec // 60)
                    secs = int(delta_sec % 60)
                    return delta_sec / 60.0, f"{mins} min {secs:02d} sec"
        except Exception:
            pass

    # ---- 3. Fallback: sum of swing durations ----
    if "duration" in df.columns:
        total_sec = float(pd.to_numeric(df["duration"], errors="coerce").sum())
        if total_sec > 1:   # only show if meaningful
            mins = int(total_sec // 60)
            secs = int(total_sec % 60)
            return total_sec / 60.0, f"{mins} min {secs:02d} sec (sum of swing durations)"

    return None, "Not available (no usable timestamps)"


def compute_between_swing_recovery(df):
    """Between-swing recovery interval (movement recovery interval).
    Returns dict with avg/median/max in seconds, or None values if unavailable.
    """
    result = {"avg": None, "median": None, "max": None, "available": False}
    if df is None or len(df) < 2:
        return result

    for col in ["timestamp", "time", "datetime", "ts", "elapsed_ms", "elapsed"]:
        if col not in df.columns:
            continue

        series = df[col]

        # Try real datetime gaps
        try:
            ts = pd.to_datetime(series, errors="coerce").dropna().sort_values()
            if len(ts) >= 2 and ts.max().year > 1971:
                gaps = ts.diff().dt.total_seconds().dropna()
                gaps = gaps[gaps > 0]
                if len(gaps) > 0:
                    result["avg"] = round(float(gaps.mean()), 2)
                    result["median"] = round(float(gaps.median()), 2)
                    result["max"] = round(float(gaps.max()), 2)
                    result["available"] = True
                    return result
        except Exception:
            pass

        # Numeric elapsed ms / s (ESP32)
        try:
            vals = pd.to_numeric(series, errors="coerce").dropna().sort_values()
            if len(vals) >= 2:
                gaps = vals.diff().dropna()
                gaps = gaps[gaps > 0]
                if len(gaps) == 0:
                    continue

                # Same heuristic: large numbers = milliseconds
                if float(gaps.median()) > 50 or float(vals.max()) > 500:
                    gaps = gaps / 1000.0   # ms → seconds

                result["avg"] = round(float(gaps.mean()), 2)
                result["median"] = round(float(gaps.median()), 2)
                result["max"] = round(float(gaps.max()), 2)
                result["available"] = True
                return result
        except Exception:
            pass

    # Fallback using swing duration
    if "duration" in df.columns and len(df) >= 2:
        result["avg"] = round(float(df["duration"].mean()), 2)
        result["median"] = round(float(df["duration"].median()), 2)
        result["max"] = round(float(df["duration"].max()), 2)
        result["available"] = True
        result["note"] = "Approximated from swing duration (true inter-swing timestamps unavailable)"
    return result


def generate_session_insight(summary, consistency_scores, fatigue, intensity_drop, strong_pct, workload_index):
    """Dynamic natural-language overall session insight (no hard-coded sentence)."""
    total = int(summary.get("total_swings", 0))
    parts = []
    parts.append(f"Your session recorded {total} swings.")

    if strong_pct >= 45:
        parts.append("A large share of swings were classified as strong, indicating high racket-movement intensity.")
    elif strong_pct >= 25:
        parts.append("A balanced mix of intensity levels was observed.")
    else:
        parts.append("Most swings were in the weak-to-medium intensity range.")

    cons = float(consistency_scores.get("consistency_score", 50) or 50)
    if cons >= 75:
        parts.append("Racket movement characteristics stayed relatively consistent.")
    elif cons >= 55:
        parts.append("Moderate variation in swing characteristics was present (normal when mixing stroke types).")
    else:
        parts.append("Swing characteristics varied considerably across the session.")

    if intensity_drop is not None:
        if intensity_drop < 5:
            parts.append("Performance indicators remained fairly stable from early to late session.")
        elif intensity_drop < 15:
            parts.append("A mild decline in movement intensity appeared toward the later part of the session.")
        else:
            parts.append("A noticeable drop in racket-movement intensity occurred in the later part of the session.")

    parts.append(
        "These are badminton-specific performance indicators derived from racket sensor data — "
        "not direct physiological measurements."
    )
    return " ".join(parts)


def generate_workload_inference(workload_index, total_swings, strong_pct):
    if total_swings < 30:
        return ("🟢 Light activity volume",
                "This session contained a relatively small number of recorded swings. "
                "It represents light racket activity volume.")
    if total_swings < 80 and strong_pct < 30:
        return ("🟡 Moderate training volume",
                "Your session involved a moderate amount of racket activity with mostly controlled intensity.")
    if strong_pct >= 40 or workload_index > total_swings * 2.2:
        return ("🔴 High racket-activity demand",
                "Your session involved a high amount of racket activity and repeated higher-intensity movements. "
                "This indicates a relatively demanding badminton session from a movement-volume perspective.")
    return ("🟡 Solid training volume",
            "Your session showed a solid amount of racket activity. "
            "Combined intensity and volume suggest a productive training load for technique and movement practice.")


def generate_intensity_inference(weak_pct, medium_pct, strong_pct):
    if strong_pct >= 50:
        overall = "HIGH"
        text = (f"More than half of your recorded swings ({strong_pct}%) were classified as strong, "
                "so this session contained a large amount of high-intensity racket movement.")
    elif strong_pct >= 30 or (strong_pct + medium_pct) >= 60:
        overall = "MODERATE–HIGH"
        text = (f"A substantial portion of swings were medium or strong "
                f"(Medium {medium_pct}%, Strong {strong_pct}%). "
                "The session contained meaningful high-effort racket movements.")
    elif weak_pct >= 55:
        overall = "LOW–MODERATE"
        text = (f"The majority of swings ({weak_pct}%) were classified as weak. "
                "This can reflect technical/control practice, warm-up, or lower-intensity rally work.")
    else:
        overall = "MODERATE"
        text = (f"Intensity was distributed across weak ({weak_pct}%), medium ({medium_pct}%) "
                f"and strong ({strong_pct}%) swings.")
    return overall, text


def generate_power_inference(peak_speed, avg_speed, peak_accel):
    lines = []
    if peak_speed is not None:
        lines.append(
            f"Your highest racket movement speed was {peak_speed:.2f}. "
            "This indicates your strongest explosive racket movement during this session."
        )
    if avg_speed is not None:
        lines.append(
            f"Average swing speed across the session was {avg_speed:.2f}. "
            "Average speed is more representative of overall session performance than a single peak."
        )
    if peak_accel is not None:
        lines.append(
            f"Peak acceleration (impact proxy) reached {peak_accel:.2f}. "
            "Higher values indicate a more sudden/intense racket movement, "
            "but this is not a direct measurement of force applied to the shuttle."
        )
    return " ".join(lines) if lines else "Power-related indices are limited for this session."


def generate_endurance_inference(intensity_drop, fatigue_score, performance_trend_status):
    """intensity_drop and fatigue_score are decline-only percentages (project-defined)."""
    if intensity_drop is None:
        return ("🟡 Insufficient data",
                "Not enough swings to reliably compare early vs late session intensity.")
    if intensity_drop < 5:
        return ("🟢 Stable performance",
                "Your racket movement performance remained relatively stable throughout the session, "
                "suggesting you maintained movement intensity well.")
    if intensity_drop < 15:
        return ("🟡 Mild late-session decline",
                f"Your average movement intensity was about {intensity_drop:.1f}% lower in the final part "
                "of the session compared with the beginning. This may indicate increasing fatigue during prolonged activity.")
    return ("🔴 Noticeable late-session decline",
            f"Your racket movement performance dropped noticeably ({intensity_drop:.1f}% intensity drop) "
            "during the later part of the session. This suggests that fatigue may have affected movement intensity. "
            "This is a performance indicator, not a medical diagnosis.")


def generate_consistency_inference(consistency_score, speed_cv):
    if consistency_score >= 75:
        status = "🟢 High consistency"
        text = (f"Swing Consistency: {consistency_score:.1f}/100. "
                "Your swings were relatively consistent in their movement characteristics. "
                "A higher value means repeated swings were more similar to each other.")
    elif consistency_score >= 55:
        status = "🟡 Moderate consistency"
        text = (f"Swing Consistency: {consistency_score:.1f}/100. "
                "Moderate variation was present. This is common when mixing different stroke types "
                "(smash, clear, drop, drive) that naturally have different motion patterns.")
    else:
        status = "🔴 Lower consistency"
        text = (f"Swing Consistency: {consistency_score:.1f}/100. "
                "Swing characteristics varied considerably. This can happen because of changes in stroke type, "
                "movement intensity, or late-session fatigue. Low consistency does not automatically mean poor technique.")
    if speed_cv is not None:
        text += f" Speed coefficient of variation was {speed_cv:.3f}."
    return status, text


def render_session_level_performance(df, summary, consistency_scores, fatigue, player_profile, level):
    """Full player-friendly Session Level Performance report.
    Reuses existing calculated values; adds only interpretation layer + a few derived indicators.
    """
    st.markdown("""
    <div style="text-align:center; padding: 8px 0 18px 0;">
        <h1 style="font-size:2.1rem; background: linear-gradient(90deg,#0ea5e9,#38bdf8,#22d3ee);
                   -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0;">
            🏸 SESSION LEVEL PERFORMANCE
        </h1>
        <p style="color:#94a3b8; margin-top:6px;">
            Badminton-specific fitness-related &amp; performance indicators derived from racket movement data
        </p>
    </div>
    """, unsafe_allow_html=True)

    if df is None or len(df) == 0:
        st.warning("No session data available. Run analytics first.")
        return

    total = int(summary.get("total_swings", len(df)))
    weak = int(summary.get("weak_count", 0))
    medium = int(summary.get("medium_count", 0))
    strong = int(summary.get("strong_count", 0))
    weak_pct = _safe_pct(weak, total)
    medium_pct = _safe_pct(medium, total)
    strong_pct = _safe_pct(strong, total)

    # Workload (reuse project definition: WEAK=1, MEDIUM=2, STRONG=3)
    workload_index = weak + (2 * medium) + (3 * strong)
    workload_per_swing = round(workload_index / max(total, 1), 3)

    duration_min, duration_str = compute_session_duration_minutes(df)
    recovery = compute_between_swing_recovery(df)

    # Intensity drop (reuse early/late logic already present in fatigue_detection)
    intensity_drop = float(fatigue.get("power_drop", fatigue.get("fatigue_score", 0)) or 0)
    peak_speed = float(df["speed"].max()) if "speed" in df.columns and len(df) else None
    avg_speed = float(summary.get("avg_speed", 0))
    peak_accel = float(df["impact"].max()) if "impact" in df.columns and len(df) else None
    cons_score = float(consistency_scores.get("consistency_score", 0) or 0)
    speed_cv = consistency_scores.get("speed_cv")

    # ---------- SESSION INSIGHT ----------
    insight = generate_session_insight(
        summary, consistency_scores, fatigue, intensity_drop, strong_pct, workload_index
    )
    st.markdown("### 🏸 Session Insight")
    st.markdown(f"""
    <div style="background: linear-gradient(145deg,#1e293b 0%,#0f172a 100%);
                border-radius:16px; padding:22px; border:1px solid rgba(56,189,248,0.35);
                margin-bottom:18px;">
        <p style="color:#e2e8f0; line-height:1.7; margin:0; font-size:1.05rem;">{insight}</p>
    </div>
    """, unsafe_allow_html=True)

    # ---------- 1. SESSION SUMMARY ----------
    st.markdown("---")
    st.markdown("### 🏸 Session Summary")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Swings", total)
    with c2:
        st.metric("Session Duration", duration_str if duration_str else "N/A")
    with c3:
        st.metric("Estimated Workload Index", workload_index)
    with c4:
        overall_int, _ = generate_intensity_inference(weak_pct, medium_pct, strong_pct)
        st.metric("Overall Intensity", overall_int)

    st.caption(
        f"You completed **{total}** swings during this session. "
        "This represents the overall amount of racket activity recorded. "
        "Swing count alone does not determine fitness."
    )
    st.caption(
        f"**Session Duration:** {duration_str}. "
        "This is the total time covered by the recorded session. "
        "A longer session generally represents greater training volume, but duration alone does not determine fitness."
    )

    wl_status, wl_text = generate_workload_inference(workload_index, total, strong_pct)
    st.info(f"**Workload** — {wl_status}\n\n{wl_text}\n\n"
            f"*Formula (project-defined): Workload Index = 1×Weak + 2×Medium + 3×Strong = {workload_index}. "
            f"Workload per swing ≈ {workload_per_swing}.*")

    overall_int, int_text = generate_intensity_inference(weak_pct, medium_pct, strong_pct)
    st.markdown(f"""
    **Intensity breakdown**
    - Weak: **{weak_pct}%** ({weak} swings)
    - Medium: **{medium_pct}%** ({medium} swings)
    - Strong: **{strong_pct}%** ({strong} swings)
    """)
    st.success(int_text)

    # ---------- 2. POWER ----------
    st.markdown("---")
    st.markdown("### 💪 Power — Racket Movement Power Indicators")
    st.caption(
        "The system uses an MPU6050 on the racket. These are **racket movement power indicators**, "
        "not direct measurements of human muscular power in watts."
    )

    p1, p2, p3 = st.columns(3)
    with p1:
        st.metric("Peak Speed", f"{peak_speed:.2f}" if peak_speed is not None else "N/A")
    with p2:
        st.metric("Average Speed", f"{avg_speed:.2f}")
    with p3:
        st.metric("Peak Acceleration (Impact proxy)", f"{peak_accel:.2f}" if peak_accel is not None else "N/A")

    # Peak / Average speed graphs
    x_axis = list(range(len(df)))
    fig_spd = go.Figure()
    fig_spd.add_trace(go.Scatter(
        x=x_axis, y=df["speed"], mode="lines",
        line=dict(color="#0ea5e9", width=2), fill="tozeroy",
        fillcolor="rgba(14,165,233,0.12)", name="Swing Speed Index"
    ))
    if peak_speed is not None:
        fig_spd.add_hline(y=peak_speed, line_dash="dot", line_color="#f472b6",
                          annotation_text=f"Peak {peak_speed:.1f}")
    fig_spd.add_hline(y=avg_speed, line_dash="dash", line_color="#34d399",
                      annotation_text=f"Avg {avg_speed:.1f}")
    fig_spd.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
        title="Swing Speed across Session", xaxis_title="Swing #",
        yaxis_title="Swing Speed Index", height=320, showlegend=False
    )
    st.plotly_chart(fig_spd, use_container_width=True, key="slp_speed")

    st.markdown("""
    **What this means:** Peak speed shows the fastest racket movement detected during the session.  
    Higher values indicate that the player produced faster racket movement during at least one swing.  
    Average speed represents the typical racket movement speed across your swings and is more useful 
    for understanding overall session performance than looking only at the single fastest swing.
    """)
    st.info(generate_power_inference(peak_speed, avg_speed, peak_accel))

    # Peak acceleration (impact) distribution
    fig_acc = go.Figure()
    fig_acc.add_trace(go.Histogram(
        x=df["impact"], nbinsx=20,
        marker=dict(color="rgba(244,114,182,0.7)", line=dict(color="#f472b6", width=1)),
        name="Impact / Accel"
    ))
    if peak_accel is not None:
        fig_acc.add_vline(x=peak_accel, line_dash="dash", line_color="#38bdf8",
                          annotation_text=f"Peak {peak_accel:.1f}")
    fig_acc.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
        title="Peak Acceleration / Impact Index Distribution",
        xaxis_title="Impact Index (acceleration proxy)", yaxis_title="Count",
        height=300, showlegend=False
    )
    st.plotly_chart(fig_acc, use_container_width=True, key="slp_accel")
    st.caption(
        "Peak acceleration shows the highest acceleration detected during racket movement. "
        "Higher values indicate a more sudden/intense racket movement, but this is **not** a direct "
        "measurement of the force applied to the shuttle."
    )

    # ---------- 3. ENDURANCE & FATIGUE ----------
    st.markdown("---")
    st.markdown("### 🫁 Endurance & Fatigue — Badminton-specific indicators")
    st.caption(
        "These indicators describe performance changes derived from racket data. "
        "They are **not** physiological or medical fatigue diagnoses (no HR, VO₂, lactate, etc.)."
    )

    end_status, end_text = generate_endurance_inference(intensity_drop, fatigue.get("fatigue_score"), None)
    e1, e2, e3 = st.columns(3)
    with e1:
        st.metric("Intensity Drop (early → late)", f"{intensity_drop:.1f}%")
    with e2:
        st.metric("Fatigue-related Change", f"{fatigue.get('fatigue_score', 0):.1f}%")
    with e3:
        if recovery["available"] and recovery["avg"] is not None:
            st.metric("Avg Between-Swing Recovery", f"{recovery['avg']:.2f} s")
        else:
            st.metric("Avg Between-Swing Recovery", "Not available")

    st.markdown(f"**Status:** {end_status}")
    st.info(end_text)

    # Performance trend (reuse grouped approach)
    n = len(df)
    if n >= 10:
        df_tmp = df.copy()
        df_tmp["swing_group"] = pd.cut(range(n), bins=min(10, n // 2), labels=False)
        grouped = df_tmp.groupby("swing_group").agg(
            {"speed": "mean", "power": "mean", "impact": "mean"}
        ).reset_index()
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=grouped["swing_group"], y=grouped["power"],
            mode="lines+markers", name="Avg Swing Power Index",
            line=dict(color="#34d399", width=3), marker=dict(size=8)
        ))
        fig_trend.add_trace(go.Scatter(
            x=grouped["swing_group"], y=grouped["speed"],
            mode="lines+markers", name="Avg Swing Speed Index",
            line=dict(color="#0ea5e9", width=2), marker=dict(size=7)
        ))
        fig_trend.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
            title="Performance Trend across Session",
            xaxis_title="Session Progress (early → late)",
            yaxis_title="Index value", height=360, hovermode="x unified"
        )
        st.plotly_chart(fig_trend, use_container_width=True, key="slp_trend")
        st.markdown("""
        **What this means:** This graph shows whether your racket movement performance stayed stable, 
        improved, or decreased as the session progressed.
        """)
        if intensity_drop < 5:
            st.success("🟢 Your performance remained relatively stable throughout the session.")
        elif intensity_drop < 15:
            st.warning("🟡 Performance decreased slightly toward the end of the session.")
        else:
            st.error("🔴 Performance dropped noticeably in the later part of the session.")
    else:
        st.info("Need at least 10 swings for a reliable performance-trend graph.")

    # Recovery explanation
    st.markdown("#### Between-Swing Recovery Time (Movement Recovery Interval)")
    if recovery["available"]:
        st.write(
            f"- Average: **{recovery['avg']} s**  \n"
            f"- Median: **{recovery.get('median', '—')} s**  \n"
            f"- Maximum gap: **{recovery.get('max', '—')} s**"
        )
        if recovery.get("note"):
            st.caption(recovery["note"])
        st.caption(
            "Recovery time here represents the average gap between detected swings. "
            "Shorter gaps indicate repeated swings with less time between movements; "
            "longer gaps indicate more recovery between movements. "
            "This is a **racket-motion / session metric**, not physiological recovery."
        )
    else:
        st.warning(
            "Recovery Time — Not available because this session does not contain sufficient "
            "timestamp information."
        )

    # ---------- 4. CONSISTENCY ----------
    st.markdown("---")
    st.markdown("### 🎯 Consistency")
    cons_status, cons_text = generate_consistency_inference(cons_score, speed_cv)
    st.metric("Swing Consistency Score", f"{cons_score:.1f}/100")
    st.markdown(f"**Status:** {cons_status}")
    st.info(cons_text)
    st.caption(
        "Consistency is calculated from the existing project formula using coefficients of variation "
        "of speed, impact and power (already computed in the main pipeline)."
    )

    fig_var = go.Figure()
    fig_var.add_trace(go.Scatter(
        x=list(range(len(df))), y=df["speed"],
        mode="lines", line=dict(color="#0ea5e9", width=1.5), name="Speed"
    ))
    fig_var.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
        title="Speed Variation across Session",
        xaxis_title="Swing #", yaxis_title="Swing Speed Index", height=320, showlegend=False
    )
    st.plotly_chart(fig_var, use_container_width=True, key="slp_speed_var")
    st.markdown("""
    **What this means:** This graph shows how much your swing speed changed from one swing to another. 
    Smaller variation means more stable racket movement; larger variation means greater differences between swings.  
    Different badminton strokes naturally have different speeds, so variation is not automatically “bad”.
    """)

    # ---------- 5. DETAILED ANALYTICS ----------
    st.markdown("---")
    st.markdown("### 📊 Detailed Analytics")

    with st.expander("📈 Additional Graphs", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            fig_pow = go.Figure()
            fig_pow.add_trace(go.Scatter(
                x=list(range(len(df))), y=df["power"],
                mode="lines", line=dict(color="#34d399", width=2),
                fill="tozeroy", fillcolor="rgba(52,211,153,0.12)"
            ))
            fig_pow.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
                title="Swing Power Index over Session", height=280, showlegend=False
            )
            st.plotly_chart(fig_pow, use_container_width=True, key="slp_power_line")
        with col_b:
            if "duration" in df.columns:
                fig_dur = go.Figure()
                fig_dur.add_trace(go.Histogram(
                    x=df["duration"], nbinsx=15,
                    marker=dict(color="rgba(251,191,36,0.7)")
                ))
                fig_dur.update_layout(
                    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
                    title="Swing Duration Distribution", height=280, showlegend=False
                )
                st.plotly_chart(fig_dur, use_container_width=True, key="slp_dur")
            else:
                st.info("Duration column not available for distribution.")

        # Intensity pie
        pred_counts = df["final_prediction"].value_counts() if "final_prediction" in df.columns else pd.Series()
        if not pred_counts.empty:
            fig_pie = go.Figure(data=[go.Pie(
                labels=pred_counts.index, values=pred_counts.values, hole=0.45,
                marker=dict(colors=["#ef4444", "#fbbf24", "#34d399"])
            )])
            fig_pie.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"), title="Intensity Distribution", height=320
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="slp_int_pie")

    with st.expander("📋 Raw Session Metrics Table", expanded=True):
        metrics_rows = [
            {"Metric": "Total Swings", "Value": total},
            {"Metric": "Session Duration", "Value": duration_str},
            {"Metric": "Estimated Workload Index", "Value": workload_index},
            {"Metric": "Workload per Swing", "Value": workload_per_swing},
            {"Metric": "Overall Intensity", "Value": overall_int},
            {"Metric": "Weak %", "Value": f"{weak_pct}%"},
            {"Metric": "Medium %", "Value": f"{medium_pct}%"},
            {"Metric": "Strong %", "Value": f"{strong_pct}%"},
            {"Metric": "Peak Speed", "Value": f"{peak_speed:.2f}" if peak_speed is not None else "N/A"},
            {"Metric": "Average Speed", "Value": f"{avg_speed:.2f}"},
            {"Metric": "Peak Acceleration (Impact proxy)", "Value": f"{peak_accel:.2f}" if peak_accel is not None else "N/A"},
            {"Metric": "Consistency Score", "Value": f"{cons_score:.1f}/100"},
            {"Metric": "Intensity Drop %", "Value": f"{intensity_drop:.1f}%"},
            {"Metric": "Fatigue-related Change %", "Value": f"{fatigue.get('fatigue_score', 0):.1f}%"},
            {"Metric": "Avg Between-Swing Recovery (s)", "Value": recovery["avg"] if recovery["available"] else "Not available"},
            {"Metric": "Player Level (existing)", "Value": level},
            {"Metric": "Player Type (existing)", "Value": player_profile.get("player_type", "")},
        ]
        st.dataframe(pd.DataFrame(metrics_rows), use_container_width=True, hide_index=True)

    st.caption(
        "All values above are project-defined performance indicators derived from racket sensor data. "
        "They are not direct physiological measurements or medical diagnoses."
    )


# =====================================================
# SIDEBAR — SESSION SETUP
# =====================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-size: 2.5rem; margin-bottom: 0; animation: float 3s ease-in-out infinite;">🏸</h1>
        <h2 style="font-size: 1.2rem; color: #38bdf8; margin-top: 5px;">BADMINTON AI</h2>
        <p style="color: #94a3b8; font-size: 0.8rem;">Smart Swing Analytics + Longitudinal Tracking</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("👤 Player & Session")

    player_id = st.text_input(
        "Player ID",
        value=st.session_state.get("player_id", "P001"),
        help="Unique ID used as the primary key for the player's longitudinal CSV."
    ).strip()

    player_name = st.text_input(
        "Player Name",
        value=st.session_state.get("player_name", ""),
        help="Used for display and for the first player CSV filename."
    ).strip()

    if player_id:
        existing_ids = get_existing_session_ids(player_id)
        existing_history = load_player_history(player_id)
        if existing_history.empty:
            st.caption("🆕 New player — no sessions saved yet.")
            suggested = 1
        else:
            st.caption(f"📚 Existing player — {len(existing_history)} saved session(s).")
            st.caption(f"Existing Session IDs: {sorted(existing_ids)}")
            suggested = get_next_session_id(player_id)
            st.caption(f"Suggested next Session ID: **{suggested}** (you may choose any unused ID)")
    else:
        existing_ids = set()
        existing_history = pd.DataFrame(columns=LONGITUDINAL_COLUMNS)
        suggested = 1

    session_id = st.number_input(
        "Session ID (user-controlled)",
        min_value=1,
        value=int(st.session_state.get("session_id", suggested)),
        step=1,
        help="You control the Session ID. The system never silently changes it. "
             "If this ID already exists, the session will NOT be overwritten."
    )

    if player_id and int(session_id) in existing_ids:
        st.warning(f"⚠ Session {int(session_id)} already exists for this player. "
                   "Analytics can still run, but saving will be blocked.")

    st.markdown("---")
    st.subheader("📂 Sensor Data Uploads")

    calibration_upload = st.file_uploader(
        "1. Calibration CSV (required)",
        type=["csv"],
        key="calibration_upload",
        help="Used to derive intensity thresholds (WEAK / MEDIUM / STRONG)."
    )

    game_upload = st.file_uploader(
        "2. Game / Session CSV (required)",
        type=["csv"],
        key="game_upload",
        help="Raw session CSV from the ESP32 / racket sensor pipeline."
    )

    both_uploaded = (calibration_upload is not None) and (game_upload is not None)

    if both_uploaded:
        st.success("✅ Both files uploaded")
    else:
        st.info("❌ Waiting for both Calibration CSV and Game/Session CSV")

    st.markdown("---")
    st.subheader("▶ Analysis Control")

    start_clicked = st.button(
        "▶ START SESSION ANALYTICS",
        use_container_width=True,
        disabled=not both_uploaded,
        help="Analytics run only after both files are uploaded and this button is pressed."
    )

    if not both_uploaded:
        st.caption("Upload both files to enable the Start button.")

    st.markdown("---")
    st.subheader("🎮 Display Filters")
    stroke_filter = st.multiselect(
        "🏸 Stroke Filter",
        ["SMASH", "DROP", "CLEAR", "DRIVE"],
        default=["SMASH", "DROP", "CLEAR", "DRIVE"]
    )

    st.markdown("---")
    st.subheader("⚡ Quick Stats")
    if st.session_state.get("analysis_done"):
        s = st.session_state.summary
        st.metric("Total Swings", s["total_swings"])
        st.metric("Avg Swing Power Index", f"{s['avg_power']:.1f}")
        st.metric("Stability", f"{st.session_state.stability_score}/10")
    else:
        st.caption("Run analytics to see quick stats.")

    st.markdown("---")
    st.caption("© 2026 Smart Badminton AI | SIH 2026")
    st.caption("Racket-derived performance indices only — not physiological measurements.")

# Persist identity
st.session_state.player_id = player_id
st.session_state.player_name = player_name
st.session_state.session_id = int(session_id)

# =====================================================
# MAIN HEADER
# =====================================================
st.markdown("""
<div style="text-align: center; padding: 10px 0 20px 0;">
    <h1 style="font-size: 2.6rem; background: linear-gradient(90deg, #0ea5e9, #38bdf8, #22d3ee);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🏸 SMART BADMINTON AI DASHBOARD
    </h1>
    <p style="color: #94a3b8; font-size: 1.05rem;">
        Badminton-specific, non-invasive fitness-related &amp; performance assessment
        using racket-based movement data
    </p>
</div>
""", unsafe_allow_html=True)

# =====================================================
# ANALYTICS TRIGGER (explicit only)
# =====================================================
if start_clicked and both_uploaded:
    with st.spinner("🤖 Analysing swings with AI..."):
        try:
            game_bytes = game_upload.getvalue()
            calibration_bytes = calibration_upload.getvalue()
            (
                df, summary, comparison, gap_analysis, level, consistency_scores,
                stability_score, fatigue, player_profile, suggestions, recalibrated
            ) = classify(game_bytes, calibration_bytes)

            st.session_state.analysis_done = True
            st.session_state.df = df
            st.session_state.summary = summary
            st.session_state.comparison = comparison
            st.session_state.gap_analysis = gap_analysis
            st.session_state.level = level
            st.session_state.consistency_scores = consistency_scores
            st.session_state.stability_score = stability_score
            st.session_state.fatigue = fatigue
            st.session_state.player_profile = player_profile
            st.session_state.suggestions = suggestions
            st.session_state.recalibrated = recalibrated
            st.session_state.save_attempted = False  # allow one save after this run

            if recalibrated:
                st.info("ℹ Intensity thresholds were recalculated from the uploaded Calibration CSV for this session.")
            st.success("✅ Session analytics completed successfully.")

        except Exception as e:
            st.session_state.analysis_done = False
            st.error(f"❌ Error during classification: {e}")
            st.info(
                "Check that both CSVs contain speed, impact and duration columns, "
                "and that model / threshold files are accessible if used."
            )
            st.stop()

# Gate the rest of the UI
if not st.session_state.get("analysis_done"):
    st.markdown("---")
    st.info(
        "Upload **both** the Calibration CSV and the Game/Session CSV in the sidebar, "
        "then press **▶ START SESSION ANALYTICS** to begin.\n\n"
        "Analytics will not run automatically on page load."
    )
    st.markdown("""
    <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
                border-radius: 16px; padding: 24px; border: 1px solid rgba(56,189,248,0.25); margin-top: 20px;">
        <h3 style="color:#38bdf8; margin-top:0;">How this system works</h3>
        <p style="color:#94a3b8; line-height:1.6;">
            MPU6050 (racket only) → Swing detection → Feature extraction → Stroke classification (ML) →
            Intensity classification (rule-based thresholds) → Session performance indices →
            CSV player history → Longitudinal fitness-related performance analysis.
        </p>
        <p style="color:#64748b; font-size:0.9rem; margin-bottom:0;">
            All fitness-related outputs are project-defined performance indicators derived from
            racket movement data. They are not direct physiological measurements (HR, VO₂, EMG, etc.).
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Unpack from session state
df = st.session_state.df
summary = st.session_state.summary
comparison = st.session_state.comparison
gap_analysis = st.session_state.gap_analysis
level = st.session_state.level
consistency_scores = st.session_state.consistency_scores
stability_score = st.session_state.stability_score
fatigue = st.session_state.fatigue
player_profile = st.session_state.player_profile
suggestions = st.session_state.suggestions

# =====================================================
# SAVE SESSION (once per successful analysis, never overwrite)
# =====================================================
if player_id and player_name:
    if not st.session_state.get("save_attempted"):
        hist_before = load_player_history(player_id)
        readiness = compute_readiness_trend(hist_before) if not hist_before.empty else "First session — baseline"
        progress_preview = compute_progress_indicator(
            pd.concat([hist_before, pd.DataFrame([{
                "avg_power": summary["avg_power"],
                "avg_speed": summary["avg_speed"],
                "consistency_score": consistency_scores["consistency_score"],
                "strong_percentage": (summary["strong_count"] / max(summary["total_swings"], 1)) * 100
            }])], ignore_index=True)
        ) if not hist_before.empty else 50.0

        session_record = build_session_record(
            player_id, player_name, int(session_id), summary,
            consistency_scores, stability_score, fatigue,
            player_profile, level, df,
            fitness_progress_score=progress_preview,
            readiness_trend=readiness
        )
        saved, history_path, message = append_player_session(session_record)
        st.session_state.save_attempted = True
        if saved:
            st.success(f"✅ Session {int(session_id)} saved to player history → `{os.path.basename(history_path)}`")
        else:
            st.warning(f"ℹ️ {message}")
else:
    st.warning("⚠ Enter both Player ID and Player Name to enable longitudinal CSV logging.")

# Apply stroke filter for display
if stroke_filter:
    df_filtered = df[df["stroke_type"].isin(stroke_filter)].copy()
else:
    df_filtered = df.copy()

if len(df_filtered) == 0:
    st.warning("⚠ No data matches the selected filters. Showing all data.")
    df_filtered = df.copy()

summary_filtered = get_session_summary(df_filtered)

# =====================================================
# TABS
# =====================================================
tabs = st.tabs([
    "📊 Overview", "📈 Performance", "🏆 Pro Comparison",
    "🧠 AI Coach", "🧬 Player Profile", "⚡ Fatigue & Consistency",
    "📥 Export Data", "📅 Longitudinal Fitness & Performance",
    "🏸 Session Level Performance"
])

# ==================== TAB 1: OVERVIEW ====================
with tabs[0]:
    st.markdown("### 📊 Session Overview Dashboard")
    st.caption("Values are project-defined performance indices derived from racket sensor data.")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total Swings", int(summary_filtered["total_swings"]))
    with col2:
        st.metric("Avg Swing Speed Index", f"{summary_filtered['avg_speed']:.1f}",
                  delta=f"{comparison['gap_speed']:.1f} vs Pro")
    with col3:
        st.metric("Avg Impact Index", f"{summary_filtered['avg_impact']:.1f}",
                  delta=f"{comparison['gap_impact']:.1f} vs Pro")
    with col4:
        st.metric("Avg Swing Power Index", f"{summary_filtered['avg_power']:.1f}",
                  delta=f"{comparison['gap_power']:.1f} vs Pro")
    with col5:
        st.metric("Consistency", f"{consistency_scores['consistency_score']:.1f}")
    with col6:
        st.metric("Stability", f"{stability_score}/10")

    st.markdown("---")
    st.markdown("#### 📈 Performance Indices Over Session")
    perf_col1, perf_col2, perf_col3 = st.columns(3)
    x_axis = list(range(len(df_filtered)))

    with perf_col1:
        st.markdown("<p style='text-align:center;color:#0ea5e9;font-weight:bold;font-size:1.1rem;'>⚡ SWING SPEED INDEX</p>",
                    unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_axis, y=df_filtered["speed"], mode='lines',
            line=dict(color='#0ea5e9', width=2.5), fill='tozeroy',
            fillcolor='rgba(14,165,233,0.15)'
        ))
        fig.add_hline(y=summary_filtered["avg_speed"], line_dash="dash", line_color="#f472b6",
                      annotation_text=f"Avg: {summary_filtered['avg_speed']:.1f}")
        fig.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
            margin=dict(l=30, r=30, t=30, b=30), xaxis_title="Swing #",
            yaxis_title="Swing Speed Index", height=280, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, key="ov_speed")

    with perf_col2:
        st.markdown("<p style='text-align:center;color:#f472b6;font-weight:bold;font-size:1.1rem;'>💥 IMPACT INDEX</p>",
                    unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_axis, y=df_filtered["impact"], mode='lines',
            line=dict(color='#f472b6', width=2.5), fill='tozeroy',
            fillcolor='rgba(244,114,182,0.15)'
        ))
        fig.add_hline(y=summary_filtered["avg_impact"], line_dash="dash", line_color="#0ea5e9",
                      annotation_text=f"Avg: {summary_filtered['avg_impact']:.1f}")
        fig.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
            margin=dict(l=30, r=30, t=30, b=30), xaxis_title="Swing #",
            yaxis_title="Impact Index", height=280, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, key="ov_impact")

    with perf_col3:
        st.markdown("<p style='text-align:center;color:#34d399;font-weight:bold;font-size:1.1rem;'>🔋 SWING POWER INDEX</p>",
                    unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_axis, y=df_filtered["power"], mode='lines',
            line=dict(color='#34d399', width=2.5), fill='tozeroy',
            fillcolor='rgba(52,211,153,0.15)'
        ))
        fig.add_hline(y=summary_filtered["avg_power"], line_dash="dash", line_color="#fbbf24",
                      annotation_text=f"Avg: {summary_filtered['avg_power']:.1f}")
        fig.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
            margin=dict(l=30, r=30, t=30, b=30), xaxis_title="Swing #",
            yaxis_title="Swing Power Index", height=280, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, key="ov_power")

    st.markdown("---")
    st.markdown("#### 🏸 Stroke Distribution")
    stroke_counts = df_filtered["stroke_type"].value_counts()
    pie_colors = ['#0ea5e9', '#f472b6', '#34d399', '#fbbf24']
    fig_pie = go.Figure(data=[go.Pie(
        labels=stroke_counts.index, values=stroke_counts.values, hole=0.5,
        marker=dict(colors=pie_colors, line=dict(color='#1e293b', width=2)),
        textinfo='label+percent', textfont=dict(color='#e2e8f0', size=12),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    fig_pie.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'),
        showlegend=False, margin=dict(l=20, r=20, t=40, b=20), height=350,
        annotations=[dict(text=f'<b>{len(df_filtered)}</b><br>Swings', x=0.5, y=0.5,
                          font=dict(size=16, color='#e2e8f0'), showarrow=False)]
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 🔥 Best & ❄ Worst Swings (by Swing Power Index)")
    if summary_filtered["best_swing"] is not None:
        col_best, col_worst = st.columns(2)
        with col_best:
            b = summary_filtered["best_swing"]
            st.markdown(f"""
            <div class="animated-card hover-lift" style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
                 border-radius: 16px; padding: 20px; border: 1px solid rgba(52, 211, 153, 0.3);">
                <h4 style="color: #34d399; margin: 0;">🔥 BEST SWING</h4>
                <p style="color: #94a3b8; margin: 5px 0;">Swing #{b.name}</p>
                <div style="display: flex; gap: 20px; margin-top: 15px;">
                    <div><p style="color: #64748b; margin: 0; font-size: 0.8rem;">SPEED IDX</p>
                         <p style="color: #e2e8f0; margin: 0; font-size: 1.4rem; font-weight: bold;">{b['speed']:.2f}</p></div>
                    <div><p style="color: #64748b; margin: 0; font-size: 0.8rem;">IMPACT IDX</p>
                         <p style="color: #e2e8f0; margin: 0; font-size: 1.4rem; font-weight: bold;">{b['impact']:.2f}</p></div>
                    <div><p style="color: #64748b; margin: 0; font-size: 0.8rem;">POWER IDX</p>
                         <p style="color: #34d399; margin: 0; font-size: 1.4rem; font-weight: bold;">{b['power']:.2f}</p></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_worst:
            w = summary_filtered["worst_swing"]
            st.markdown(f"""
            <div class="animated-card hover-lift" style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
                 border-radius: 16px; padding: 20px; border: 1px solid rgba(239, 68, 68, 0.3);">
                <h4 style="color: #ef4444; margin: 0;">❄ WORST SWING</h4>
                <p style="color: #94a3b8; margin: 5px 0;">Swing #{w.name}</p>
                <div style="display: flex; gap: 20px; margin-top: 15px;">
                    <div><p style="color: #64748b; margin: 0; font-size: 0.8rem;">SPEED IDX</p>
                         <p style="color: #e2e8f0; margin: 0; font-size: 1.4rem; font-weight: bold;">{w['speed']:.2f}</p></div>
                    <div><p style="color: #64748b; margin: 0; font-size: 0.8rem;">IMPACT IDX</p>
                         <p style="color: #e2e8f0; margin: 0; font-size: 1.4rem; font-weight: bold;">{w['impact']:.2f}</p></div>
                    <div><p style="color: #64748b; margin: 0; font-size: 0.8rem;">POWER IDX</p>
                         <p style="color: #ef4444; margin: 0; font-size: 1.4rem; font-weight: bold;">{w['power']:.2f}</p></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==================== TAB 2: PERFORMANCE ====================
with tabs[1]:
    st.markdown("### 📈 Performance Analytics")
    st.caption("Distributions of project-defined performance indices.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📊 Swing Speed Index Distribution")
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df_filtered["speed"], nbinsx=20,
            marker=dict(color='rgba(14,165,233,0.7)', line=dict(color='rgba(14,165,233,1)', width=2)),
            name='Speed'
        ))
        fig.add_vline(x=summary_filtered["avg_speed"], line_dash="dash", line_color="#f472b6",
                      annotation_text=f"Avg: {summary_filtered['avg_speed']:.1f}", annotation_position="top")
        fig.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
            xaxis_title="Swing Speed Index", yaxis_title="Frequency",
            height=350, showlegend=False, margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### 📊 Swing Power Index Distribution")
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df_filtered["power"], nbinsx=20,
            marker=dict(color='rgba(52,211,153,0.7)', line=dict(color='rgba(52,211,153,1)', width=2)),
            name='Power'
        ))
        fig.add_vline(x=summary_filtered["avg_power"], line_dash="dash", line_color="#f472b6",
                      annotation_text=f"Avg: {summary_filtered['avg_power']:.1f}", annotation_position="top")
        fig.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
            xaxis_title="Swing Power Index", yaxis_title="Frequency",
            height=350, showlegend=False, margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    # NOTE: Box plots (Swing Quality Distribution) intentionally removed per requirements.
    # NOTE: Player Capability Radar intentionally removed per requirements.

    st.markdown("---")
    st.markdown("#### 🎯 Swing Speed Index vs Impact Index (coloured by stroke, sized by Swing Power Index)")
    stroke_color_map = {"SMASH": "#ef4444", "DROP": "#fbbf24", "CLEAR": "#0ea5e9", "DRIVE": "#34d399"}
    fig_scatter = px.scatter(
        df_filtered, x="speed", y="impact", color="stroke_type", size="power",
        color_discrete_map=stroke_color_map, template='plotly_dark', height=500,
        labels={"speed": "Swing Speed Index", "impact": "Impact Index", "power": "Swing Power Index"}
    )
    fig_scatter.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(30,41,59,0.3)',
        font=dict(color='#e2e8f0'), margin=dict(l=40, r=40, t=40, b=40)
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# ==================== TAB 3: PRO COMPARISON ====================
with tabs[2]:
    st.markdown("### 🏆 Player vs Pro Comparison")
    st.caption("Performance gaps are relative differences in project-defined indices, not medical/fitness gaps.")

    col1, col2, col3 = st.columns(3)
    with col1:
        gap_speed_pct = (comparison["gap_speed"] / (comparison["pro_avg_speed"] + 1e-6)) * 100
        st.metric("Swing Speed Index", f"{comparison['player_avg_speed']:.1f}",
                  delta=f"{gap_speed_pct:.1f}% vs Pro ({comparison['pro_avg_speed']:.1f})", delta_color="inverse")
    with col2:
        gap_impact_pct = (comparison["gap_impact"] / (comparison["pro_avg_impact"] + 1e-6)) * 100
        st.metric("Impact Index", f"{comparison['player_avg_impact']:.1f}",
                  delta=f"{gap_impact_pct:.1f}% vs Pro ({comparison['pro_avg_impact']:.1f})", delta_color="inverse")
    with col3:
        gap_power_pct = (comparison["gap_power"] / (comparison["pro_avg_power"] + 1e-6)) * 100
        st.metric("Swing Power Index", f"{comparison['player_avg_power']:.1f}",
                  delta=f"{gap_power_pct:.1f}% vs Pro ({comparison['pro_avg_power']:.1f})", delta_color="inverse")

    st.markdown("---")
    st.markdown("#### 📊 Side-by-Side Comparison")
    bar_col1, bar_col2, bar_col3 = st.columns(3)
    bar_configs = [
        ("⚡ Swing Speed Index", "speed", "#0ea5e9", "rgba(14,165,233,0.5)", bar_col1),
        ("💥 Impact Index", "impact", "#f472b6", "rgba(244,114,182,0.5)", bar_col2),
        ("🔋 Swing Power Index", "power", "#34d399", "rgba(52,211,153,0.5)", bar_col3),
    ]
    for label, key, player_color, pro_color, col in bar_configs:
        with col:
            player_val = comparison[f"player_avg_{key}"]
            pro_val = comparison[f"pro_avg_{key}"]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["You", "Pro"], y=[player_val, pro_val],
                marker_color=[player_color, pro_color],
                text=[f"{player_val:.1f}", f"{pro_val:.1f}"],
                textposition='outside', textfont=dict(color='#e2e8f0', size=14)
            ))
            fig.update_layout(
                template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
                title=dict(text=label, font=dict(size=14, color='#f8fafc'), x=0.5),
                height=350, yaxis_title=key, margin=dict(l=20, r=20, t=50, b=20), showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 🧠 Gap Analysis")
    for feature, msg in gap_analysis:
        if "deficit" in msg.lower() or "weak" in msg.lower() or "low" in msg.lower():
            emoji, color = "🔴", "#ef4444"
        elif "improvement" in msg.lower() or "needs" in msg.lower() or "work" in msg.lower():
            emoji, color = "🟡", "#fbbf24"
        else:
            emoji, color = "🟢", "#34d399"
        st.markdown(f"""
        <div class="animated-card hover-lift" style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
             border-radius: 12px; padding: 15px; margin: 10px 0; border-left: 4px solid {color};">
            <span style="font-size: 1.2rem;">{emoji}</span>
            <span style="font-weight: bold; color: {color};"> {feature}</span>: {msg}
        </div>
        """, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align: center; margin-top: 20px;">
        <h3 style="color: #38bdf8;">🏆 Player Level: {level}</h3>
    </div>
    """, unsafe_allow_html=True)

# ==================== TAB 4: AI COACH ====================
with tabs[3]:
    st.markdown("### 🧠 AI Coach Insights")
    st.markdown("#### 💡 Smart Recommendations")
    for i, suggestion in enumerate(suggestions):
        st.markdown(f"""
        <div class="animated-card hover-lift" style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
             border-radius: 16px; padding: 20px; margin: 15px 0; border: 1px solid rgba(56, 189, 248, 0.2);">
            <div style="display: flex; align-items: center; gap: 15px;">
                <div style="background: linear-gradient(145deg, #0ea5e9, #0284c7); width: 45px; height: 45px;
                     border-radius: 50%; display: flex; align-items: center; justify-content: center;
                     font-size: 1.3rem; flex-shrink: 0;">{i+1}</div>
                <p style="color: #e2e8f0; margin: 0; font-size: 1.1rem; font-weight: 600;">{suggestion}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🔍 Technique Feedback")
    feedback_list = technique_feedback(df_filtered, summary_filtered)
    for fb in feedback_list:
        if "⚠" in fb:
            color, bg = "#ef4444", "rgba(239, 68, 68, 0.1)"
        elif "✔" in fb:
            color, bg = "#34d399", "rgba(52, 211, 153, 0.1)"
        else:
            color, bg = "#fbbf24", "rgba(251, 191, 36, 0.1)"
        st.markdown(f"""
        <div class="animated-card" style="background: {bg}; border-radius: 12px; padding: 15px; margin: 10px 0;
             border-left: 4px solid {color};">
            <p style="color: #e2e8f0; margin: 0; font-size: 1rem;">{fb}</p>
        </div>
        """, unsafe_allow_html=True)

# ==================== TAB 5: PLAYER PROFILE ====================
with tabs[4]:
    st.markdown("### 🧬 Player Profile")
    st.markdown("#### 🎯 Player Type Classification")

    pt = player_profile['player_type']
    if "Attacker" in pt:
        icon, type_color = "🔥", "#ef4444"
    elif "Defensive" in pt:
        icon, type_color = "🛡", "#0ea5e9"
    elif "All" in pt:
        icon, type_color = "⚖", "#34d399"
    else:
        icon, type_color = "🎯", "#fbbf24"

    col_type1, col_type2, col_type3 = st.columns([1, 2, 1])
    with col_type2:
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 24px;
             padding: 40px; text-align: center; border: 3px solid {type_color};
             box-shadow: 0 12px 40px {type_color}40; margin-bottom: 20px;">
            <div style="font-size: 5rem; margin-bottom: 20px;">{icon}</div>
            <h2 style="color: {type_color}; margin: 0; font-size: 2.2rem;">{pt}</h2>
            <p style="color: #94a3b8; margin-top: 20px; font-size: 1.1rem; line-height: 1.6;">{player_profile['explanation']}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("#### 📊 Style Scores")
        stroke_dist_norm = df_filtered["stroke_type"].value_counts(normalize=True) * 100
        smash_pct_f = stroke_dist_norm.get("SMASH", 0)
        clear_pct_f = stroke_dist_norm.get("CLEAR", 0)
        avg_power_f = summary_filtered["avg_power"]
        attack_score = min(100, (smash_pct_f * 0.6) + (avg_power_f / 100))
        defense_score = min(100, (clear_pct_f * 0.6) + 30)
        balance_score = max(0, 100 - abs(smash_pct_f - clear_pct_f) * 2)

        st.markdown("<p style='color:#ef4444;font-weight:bold;margin-bottom:5px;'>🔥 Attack Score</p>", unsafe_allow_html=True)
        st.progress(int(attack_score), text=f"{attack_score:.1f}/100")
        st.markdown("<p style='color:#0ea5e9;font-weight:bold;margin-bottom:5px;'>🛡 Defense Score</p>", unsafe_allow_html=True)
        st.progress(int(defense_score), text=f"{defense_score:.1f}/100")
        st.markdown("<p style='color:#34d399;font-weight:bold;margin-bottom:5px;'>⚖ Balance Score</p>", unsafe_allow_html=True)
        st.progress(int(balance_score), text=f"{balance_score:.1f}/100")

        st.markdown("---")
        st.markdown("#### 📋 Player Stats")
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 12px;
             padding: 15px; border: 1px solid rgba(56,189,248,0.15);">
            <p style="color:#94a3b8;margin:8px 0;"><b>Total Swings:</b> <span style="color:#e2e8f0;">{summary_filtered['total_swings']}</span></p>
            <p style="color:#94a3b8;margin:8px 0;"><b>Avg Swing Power Index:</b> <span style="color:#e2e8f0;">{summary_filtered['avg_power']:.2f}</span></p>
            <p style="color:#94a3b8;margin:8px 0;"><b>Stability:</b> <span style="color:#e2e8f0;">{stability_score}/10</span></p>
            <p style="color:#94a3b8;margin:8px 0;"><b>Consistency:</b> <span style="color:#e2e8f0;">{consistency_scores['consistency_score']:.1f}/100</span></p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("#### 🏸 Stroke Distribution")
        donut_labels = ['SMASH', 'CLEAR', 'DROP', 'DRIVE']
        donut_values = [player_profile['smash_pct'], player_profile['clear_pct'],
                        player_profile['drop_pct'], player_profile['drive_pct']]
        donut_colors = ['#ef4444', '#0ea5e9', '#fbbf24', '#34d399']
        fig_donut = go.Figure(data=[go.Pie(
            labels=donut_labels, values=donut_values, hole=0.6,
            marker=dict(colors=donut_colors, line=dict(color='#1e293b', width=3)),
            textinfo='label+percent', textfont=dict(color='#e2e8f0', size=14),
            hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>'
        )])
        fig_donut.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'),
            showlegend=False, height=400,
            annotations=[dict(text='<b>Style</b>', x=0.5, y=0.5, font=dict(size=18, color='#e2e8f0'), showarrow=False)]
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🎯 Intensity Classification Distribution")
        pred_counts = df_filtered["final_prediction"].value_counts()
        pred_color_map = {"STRONG": "#34d399", "MEDIUM": "#fbbf24", "WEAK": "#ef4444"}
        fig_pred = go.Figure(data=[go.Bar(
            x=pred_counts.index, y=pred_counts.values,
            marker_color=[pred_color_map.get(p, '#0ea5e9') for p in pred_counts.index],
            text=pred_counts.values, textposition='outside', textfont=dict(color='#e2e8f0', size=16)
        )])
        fig_pred.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
            height=300, xaxis_title="Intensity", yaxis_title="Count",
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig_pred, use_container_width=True)

# ==================== TAB 6: FATIGUE & CONSISTENCY ====================
with tabs[5]:
    st.markdown("### ⚡ Fatigue-Related Performance Change & Consistency")
    st.caption(
        "These indicators describe performance changes derived from racket data. "
        "They are not physiological or medical fatigue diagnoses."
    )
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🫀 Fatigue-Related Performance Change")
        fatigue_color = "#34d399" if "Stable" in fatigue["status"] or "low" in fatigue["status"].lower() else \
            "#fbbf24" if "Mild" in fatigue["status"] else "#ef4444"
        fatigue_emoji = "✅" if "Stable" in fatigue["status"] or "low" in fatigue["status"].lower() else \
            "⚠️" if "Mild" in fatigue["status"] else "🔴"
        fatigue_score_val = fatigue['fatigue_score']

        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 20px;
             padding: 30px; text-align: center; border: 2px solid {fatigue_color};
             box-shadow: 0 8px 30px {fatigue_color}30; margin-bottom: 20px;">
            <div style="font-size: 3.5rem; margin-bottom: 15px;">{fatigue_emoji}</div>
            <h3 style="color: {fatigue_color}; margin: 0; font-size: 1.3rem;">{fatigue['status']}</h3>
            <p style="color: #e2e8f0; margin-top: 15px; font-size: 2.5rem; font-weight: bold; line-height: 1;">{fatigue_score_val:.1f}%</p>
            <p style="color: #64748b; margin: 5px 0 0 0; font-size: 0.9rem;">Fatigue-Related Change Index</p>
            <div style="display: flex; justify-content: space-around; margin-top: 20px; padding: 15px;
                 background: rgba(15,23,42,0.5); border-radius: 12px;">
                <div><p style="color:#64748b;margin:0;font-size:0.75rem;">SPEED DROP</p>
                     <p style="color:#0ea5e9;margin:0;font-weight:bold;font-size:1.1rem;">{fatigue['speed_drop']:.1f}%</p></div>
                <div><p style="color:#64748b;margin:0;font-size:0.75rem;">IMPACT DROP</p>
                     <p style="color:#f472b6;margin:0;font-weight:bold;font-size:1.1rem;">{fatigue['impact_drop']:.1f}%</p></div>
                <div><p style="color:#64748b;margin:0;font-size:0.75rem;">POWER DROP</p>
                     <p style="color:#34d399;margin:0;font-weight:bold;font-size:1.1rem;">{fatigue['power_drop']:.1f}%</p></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📉 Drop Metric Gauges")
        drops = [
            ("Speed Drop %", fatigue['speed_drop'], "gauge_spd"),
            ("Impact Drop %", fatigue['impact_drop'], "gauge_imp"),
            ("Power Drop %", fatigue['power_drop'], "gauge_pwr")
        ]
        for name, val, key in drops:
            st.markdown(f"**{name}**")
            fig_gauge = create_gauge_chart(abs(val), name, 50)
            st.plotly_chart(fig_gauge, use_container_width=True, key=key)

    with col2:
        st.markdown("#### 📊 Consistency Metrics")
        cons_metrics = [
            ("Speed CV", consistency_scores['speed_cv'], '#0ea5e9'),
            ("Impact CV", consistency_scores['impact_cv'], '#f472b6'),
            ("Power CV", consistency_scores['power_cv'], '#34d399'),
            ("Overall Consistency Score", consistency_scores['consistency_score'], '#fbbf24')
        ]
        for name, val, color in cons_metrics:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                 background:linear-gradient(145deg,#1e293b 0%,#0f172a 100%);border-radius:10px;
                 padding:12px 20px;margin:8px 0;border:1px solid rgba(56,189,248,0.1);">
                <span style="color:#94a3b8;font-weight:600;">{name}</span>
                <span style="color:{color};font-weight:bold;font-size:1.2rem;">{val}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📉 Performance Indices Across Session (grouped)")
    n = len(df_filtered)
    if n >= 10:
        df_tmp = df_filtered.copy()
        df_tmp['swing_group'] = pd.cut(range(len(df_tmp)), bins=10, labels=False)
        grouped = df_tmp.groupby('swing_group').agg(
            {'speed': 'mean', 'impact': 'mean', 'power': 'mean'}
        ).reset_index()

        fat_col1, fat_col2, fat_col3 = st.columns(3)
        with fat_col1:
            st.markdown("<p style='text-align:center;color:#0ea5e9;font-weight:bold;'>⚡ Speed Trend</p>",
                        unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=grouped['swing_group'], y=grouped['speed'], mode='lines+markers',
                line=dict(color='#0ea5e9', width=3), marker=dict(size=8, color='#0ea5e9')
            ))
            fig.update_layout(
                template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
                xaxis_title="Session Progress", yaxis_title="Avg Swing Speed Index",
                height=320, showlegend=False, margin=dict(l=30, r=30, t=30, b=30)
            )
            st.plotly_chart(fig, use_container_width=True, key="fat_speed")

        with fat_col2:
            st.markdown("<p style='text-align:center;color:#f472b6;font-weight:bold;'>💥 Impact Trend</p>",
                        unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=grouped['swing_group'], y=grouped['impact'], mode='lines+markers',
                line=dict(color='#f472b6', width=3), marker=dict(size=8, color='#f472b6')
            ))
            fig.update_layout(
                template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
                xaxis_title="Session Progress", yaxis_title="Avg Impact Index",
                height=320, showlegend=False, margin=dict(l=30, r=30, t=30, b=30)
            )
            st.plotly_chart(fig, use_container_width=True, key="fat_impact")

        with fat_col3:
            st.markdown("<p style='text-align:center;color:#34d399;font-weight:bold;'>🔋 Power Trend</p>",
                        unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=grouped['swing_group'], y=grouped['power'], mode='lines+markers',
                line=dict(color='#34d399', width=3), marker=dict(size=8, color='#34d399')
            ))
            fig.update_layout(
                template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.3)', font=dict(color='#e2e8f0'),
                xaxis_title="Session Progress", yaxis_title="Avg Swing Power Index",
                height=320, showlegend=False, margin=dict(l=30, r=30, t=30, b=30)
            )
            st.plotly_chart(fig, use_container_width=True, key="fat_power")
    else:
        st.info("📊 Not enough data for trend analysis (need at least 10 swings)")

# ==================== TAB 7: EXPORT ====================
with tabs[6]:
    st.markdown("### 📥 Data Export & Raw Data")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 💾 Export Options")
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Filtered Data (CSV)", data=csv,
            file_name="badminton_filtered_data.csv", mime="text/csv", use_container_width=True
        )
        csv_full = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Full Session Data (CSV)", data=csv_full,
            file_name="badminton_full_data.csv", mime="text/csv", use_container_width=True
        )

        summary_report = f"""
BADMINTON AI SESSION REPORT
{'='*50}

SESSION SUMMARY:
- Total Swings: {summary_filtered['total_swings']}
- Weak: {summary_filtered['weak_count']} | Medium: {summary_filtered['medium_count']} | Strong: {summary_filtered['strong_count']}

PERFORMANCE INDICES (project-defined):
- Avg Swing Speed Index: {summary_filtered['avg_speed']:.2f}
- Avg Impact Index: {summary_filtered['avg_impact']:.2f}
- Avg Swing Power Index: {summary_filtered['avg_power']:.2f}
- Consistency Score: {consistency_scores['consistency_score']:.2f}/100
- Stability Score: {stability_score}/10

PRO COMPARISON (performance gap):
- Speed Gap: {comparison['gap_speed']:.2f}
- Impact Gap: {comparison['gap_impact']:.2f}
- Power Gap: {comparison['gap_power']:.2f}

PLAYER LEVEL: {level}
FATIGUE-RELATED STATUS: {fatigue['status']}
PLAYER TYPE: {player_profile['player_type']}

AI COACH RECOMMENDATIONS:
"""
        for i, s in enumerate(suggestions, 1):
            summary_report += f"{i}. {s}\n"
        summary_report += "\nNote: All indices are racket-derived project-defined performance indicators, not physiological measurements.\n"

        st.download_button(
            "📄 Download Summary Report (TXT)", data=summary_report,
            file_name="badminton_session_report.txt", mime="text/plain", use_container_width=True
        )

        st.markdown("---")
        st.markdown("#### 📄 PDF Report")
        if st.button("📄 Generate Full PDF Report", use_container_width=True):
            with st.spinner("📄 Generating PDF..."):
                try:
                    pdf_buffer = generate_pdf_report(
                        df_filtered, summary_filtered, comparison, gap_analysis, level,
                        consistency_scores, stability_score, fatigue, player_profile, suggestions
                    )
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_buffer,
                        file_name="badminton_ai_full_report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("✅ PDF report generated successfully!")
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {e}")

    with col2:
        st.markdown("#### 📋 Session Quick Stats")
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 16px;
             padding: 20px; border: 1px solid rgba(56, 189, 248, 0.2);">
            <p style="color:#94a3b8;margin:5px 0;"><b>Total Swings:</b> <span style="color:#e2e8f0;">{summary_filtered['total_swings']}</span></p>
            <p style="color:#94a3b8;margin:5px 0;"><b>Weak:</b> <span style="color:#ef4444;">{summary_filtered['weak_count']}</span></p>
            <p style="color:#94a3b8;margin:5px 0;"><b>Medium:</b> <span style="color:#fbbf24;">{summary_filtered['medium_count']}</span></p>
            <p style="color:#94a3b8;margin:5px 0;"><b>Strong:</b> <span style="color:#34d399;">{summary_filtered['strong_count']}</span></p>
            <p style="color:#94a3b8;margin:5px 0;"><b>Player Level:</b> <span style="color:#38bdf8;">{level}</span></p>
            <p style="color:#94a3b8;margin:5px 0;"><b>Player Type:</b> <span style="color:#38bdf8;">{player_profile['player_type']}</span></p>
            <p style="color:#94a3b8;margin:5px 0;"><b>Stability:</b> <span style="color:#38bdf8;">{stability_score}/10</span></p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📊 Raw Data Table")
    display_cols = ["speed", "impact", "duration", "power", "efficiency", "stroke_type", "final_prediction"]
    available_cols = [c for c in display_cols if c in df_filtered.columns]
    st.dataframe(
        df_filtered[available_cols], use_container_width=True, height=500,
        column_config={
            "speed": st.column_config.NumberColumn("Swing Speed Index", format="%.2f"),
            "impact": st.column_config.NumberColumn("Impact Index", format="%.2f"),
            "duration": st.column_config.NumberColumn("Duration", format="%.2f"),
            "power": st.column_config.NumberColumn("Swing Power Index", format="%.2f"),
            "efficiency": st.column_config.NumberColumn("Impact Efficiency Index", format="%.2f"),
            "stroke_type": st.column_config.TextColumn("Stroke Type"),
            "final_prediction": st.column_config.TextColumn("Intensity")
        }
    )

# ==================== TAB 8: LONGITUDINAL ====================
with tabs[7]:
    st.markdown("### 📅 Longitudinal Fitness & Performance Analysis")
    st.markdown(
        "Track how the player's badminton-specific performance and fitness-related indicators "
        "change across multiple sessions. Analysis uses the player's **own historical baseline**. "
        "All metrics are project-defined performance indicators derived from racket movement data."
    )

    selected_player_id = st.text_input(
        "Player ID to analyse",
        value=player_id,
        key="longitudinal_player_id"
    ).strip()

    history = load_player_history(selected_player_id) if selected_player_id else pd.DataFrame(columns=LONGITUDINAL_COLUMNS)

    # Always offer Session Level Performance when current-session analytics exist
    if st.session_state.get("analysis_done"):
        st.markdown("---")
        st.markdown("#### 🏸 Current Session — Session Level Performance")
        st.caption(
            "Even if no longitudinal history exists yet, you can open the detailed "
            "player-friendly report for the session you just analysed."
        )
        if st.button(
            "🏸 OPEN SESSION LEVEL PERFORMANCE REPORT",
            use_container_width=True,
            key="open_slp_from_empty_hist"
        ):
            st.session_state.show_session_level = True
            st.success(
                "✅ Report ready — switch to the **🏸 Session Level Performance** tab."
            )

    if history.empty:
        st.info(
            "📭 No saved sessions found for this player yet. "
            "Complete a session with Player ID + Name and successful analytics to create the longitudinal CSV."
        )
    else:
        history = add_longitudinal_derived_metrics(history)
        feedback_preview = generate_longitudinal_feedback(history)

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sessions Tracked", len(history))
        c2.metric("Latest Swing Power Index", f"{history.iloc[-1]['avg_power']:.1f}")
        c3.metric("Latest Consistency", f"{history.iloc[-1]['consistency_score']:.1f}/100")
        c4.metric("Progress Indicator", f"{feedback_preview['progress_score']:.1f}/100")

        st.markdown("---")
        gen_col1, gen_col2 = st.columns(2)
        with gen_col1:
            generate_long = st.button(
                "📊 GENERATE COMPLETE PLAYER ANALYSIS",
                use_container_width=True,
                key="generate_longitudinal_btn"
            )
        with gen_col2:
            open_session_level = st.button(
                "🏸 OPEN SESSION LEVEL PERFORMANCE",
                use_container_width=True,
                key="open_session_level_btn",
                help="Opens the detailed player-friendly Session Level Performance report for the current analysed session."
            )

        if open_session_level:
            st.session_state.show_session_level = True
            st.success(
                "✅ Session Level Performance is ready. "
                "Switch to the **🏸 Session Level Performance** tab to view the full report."
            )

        if generate_long or st.session_state.get("long_analysis_shown"):
            st.session_state.long_analysis_shown = True
            # Also surface the Session Level Performance when the main longitudinal analysis is run
            st.session_state.show_session_level = True
            feedback = generate_longitudinal_feedback(history)
            st.info(
                "📌 Longitudinal analysis generated. "
                "A detailed **Session Level Performance** report for the current session is also available "
                "in the **🏸 Session Level Performance** tab."
            )

            st.markdown("#### 📈 Swing Power Index & Swing Speed Index Progression")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=history["session_id"], y=history["avg_power"],
                mode="lines+markers", name="Swing Power Index", line=dict(width=3)
            ))
            fig.add_trace(go.Scatter(
                x=history["session_id"], y=history["avg_speed"],
                mode="lines+markers", name="Swing Speed Index",
                yaxis="y2", line=dict(width=3)
            ))
            fig.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
                xaxis_title="Session ID",
                yaxis=dict(title="Swing Power Index"),
                yaxis2=dict(title="Swing Speed Index", overlaying="y", side="right"),
                height=450, hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True, key="long_perf")

            st.markdown("#### 🎯 Consistency & Training Workload")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=history["session_id"], y=history["consistency_score"],
                mode="lines+markers", name="Consistency Score"
            ))
            fig2.add_trace(go.Scatter(
                x=history["session_id"], y=history["workload_per_swing"] * 30,
                mode="lines+markers", name="Workload / Swing ×30"
            ))
            fig2.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
                xaxis_title="Session ID", yaxis_title="Index / Score",
                height=380, hovermode="x unified"
            )
            st.plotly_chart(fig2, use_container_width=True, key="long_consistency")

            st.markdown("#### 💪 Training Workload & Intensity Profile (stacked)")
            st.caption("Project-defined Training Workload Index: Weak=1, Medium=2, Strong=3")
            workload_fig = go.Figure()
            workload_fig.add_trace(go.Bar(x=history["session_id"], y=history["weak_count"], name="Weak"))
            workload_fig.add_trace(go.Bar(x=history["session_id"], y=history["medium_count"], name="Medium"))
            workload_fig.add_trace(go.Bar(x=history["session_id"], y=history["strong_count"], name="Strong"))
            workload_fig.update_layout(
                barmode="stack", template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
                xaxis_title="Session ID", yaxis_title="Number of Swings", height=400
            )
            st.plotly_chart(workload_fig, use_container_width=True, key="long_workload")

            st.markdown("#### 🔋 Endurance-Related Performance Maintenance")
            endurance_fig = go.Figure()
            endurance_fig.add_trace(go.Scatter(
                x=history["session_id"], y=history["endurance_maintenance_pct"],
                mode="lines+markers", name="Late / Early Power (%)"
            ))
            endurance_fig.add_hline(
                y=100, line_dash="dash",
                annotation_text="100% = late-session power matches early-session power"
            )
            endurance_fig.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
                xaxis_title="Session ID", yaxis_title="Performance Maintenance (%)", height=380
            )
            st.plotly_chart(endurance_fig, use_container_width=True)

            st.markdown("#### 😮‍💨 Fatigue-Related Performance Change Across Sessions")
            fatigue_fig = go.Figure()
            fatigue_fig.add_trace(go.Scatter(
                x=history["session_id"], y=history["fatigue_related_change"],
                mode="lines+markers", name="Fatigue-Related Change"
            ))
            fatigue_fig.add_hline(
                y=0, line_dash="dash",
                annotation_text="0% = no observed decline in tracked performance indicators"
            )
            fatigue_fig.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
                xaxis_title="Session ID", yaxis_title="Observed Performance Change (%)", height=380
            )
            st.plotly_chart(fatigue_fig, use_container_width=True)

            st.markdown("#### 🏸 Stroke Development Across Sessions")
            stroke_long = longitudinal_stroke_long_table(history)
            stroke_fig = go.Figure()
            for stroke in ["DROP", "CLEAR", "SMASH", "DRIVE"]:
                stroke_fig.add_trace(go.Scatter(
                    x=stroke_long["Session"], y=stroke_long[stroke],
                    mode="lines+markers", name=stroke
                ))
            stroke_fig.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
                xaxis_title="Session ID", yaxis_title="Stroke Count", height=420
            )
            st.plotly_chart(stroke_fig, use_container_width=True)

            st.markdown("#### 📦 Total Training Volume (swings per session)")
            vol_fig = go.Figure()
            vol_fig.add_trace(go.Bar(
                x=history["session_id"], y=history["total_swings"], name="Total Swings",
                marker_color="#0ea5e9"
            ))
            vol_fig.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,41,59,0.3)", font=dict(color="#e2e8f0"),
                xaxis_title="Session ID", yaxis_title="Total Swings", height=350
            )
            st.plotly_chart(vol_fig, use_container_width=True)

            st.markdown("---")
            st.markdown("#### 📊 First Session vs Latest Session")
            first = history.iloc[0]
            latest = history.iloc[-1]
            comparison_rows = []
            for col, label in [
                ("avg_speed", "Swing Speed Index"),
                ("avg_impact", "Impact Index"),
                ("avg_power", "Swing Power Index"),
                ("consistency_score", "Consistency Score"),
                ("strong_percentage", "Strong-Intensity %"),
                ("total_swings", "Total Swings"),
                ("workload_index", "Training Workload Index"),
                ("endurance_maintenance_pct", "Endurance Maintenance %"),
                ("fatigue_related_change", "Fatigue-Related Change %")
            ]:
                first_val = float(first[col]) if pd.notna(first[col]) else 0.0
                latest_val = float(latest[col]) if pd.notna(latest[col]) else 0.0
                change = percentage_change(first_val, latest_val)
                comparison_rows.append({
                    "Metric": label,
                    f"Session {int(first['session_id'])}": round(first_val, 2),
                    f"Session {int(latest['session_id'])}": round(latest_val, 2),
                    "Change %": round(change, 2) if pd.notna(change) else np.nan
                })
            st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

            st.markdown("#### 🔗 Consecutive Session Changes")
            consec = consecutive_session_changes(history)
            if consec.empty:
                st.info("Need at least 2 sessions for consecutive-session analysis.")
            else:
                st.dataframe(consec, use_container_width=True, hide_index=True)

            st.markdown("---")
            fb1, fb2 = st.columns(2)
            with fb1:
                st.markdown("#### ✅ Strengths")
                for item in feedback["strengths"]:
                    st.success(item)
                st.markdown("#### ⚠ Areas to Improve")
                for item in feedback["improvements"]:
                    st.warning(item)

            with fb2:
                st.markdown("#### 🎯 Recommended Training Focus")
                for item in feedback["training_focus"]:
                    st.info(item)
                st.markdown("#### 📝 Final Longitudinal Feedback")
                st.markdown(f"""
                <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
                            border-radius: 16px; padding: 22px;
                            border: 1px solid rgba(56,189,248,0.3);">
                    <p style="color:#e2e8f0; line-height:1.7; margin:0;">
                        {feedback["final_feedback"]}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"**Readiness / Recovery Trend:** {feedback['readiness_trend']}")

            st.markdown("---")
            st.markdown("#### 📋 Complete Session History")
            st.dataframe(history, use_container_width=True, hide_index=True)

            history_csv = history[LONGITUDINAL_COLUMNS].to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Player Longitudinal CSV",
                data=history_csv,
                file_name=f"{safe_filename(selected_player_id)}_longitudinal_history.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.caption(
                "Note: Workload, Swing Power Index, Impact Efficiency Index, endurance-maintenance, "
                "fatigue-related change and progress are project-defined performance indicators. "
                "They are not direct physiological measurements or medical diagnoses."
            )

# ==================== TAB 9: SESSION LEVEL PERFORMANCE (NEW) ====================
with tabs[8]:
    st.markdown(
        "This view provides a **player-friendly Session Level Performance report** for the "
        "session that was just analysed. All values reuse the existing calculations from the main pipeline."
    )
    if not st.session_state.get("analysis_done"):
        st.info(
            "Run session analytics first (upload both CSVs and press **▶ START SESSION ANALYTICS**), "
            "then return here or press **🏸 OPEN SESSION LEVEL PERFORMANCE** in the Longitudinal tab."
        )
    else:
        # Use the already-computed objects from session state (no re-calculation of ML / thresholds)
        render_session_level_performance(
            df=st.session_state.df,
            summary=st.session_state.summary,
            consistency_scores=st.session_state.consistency_scores,
            fatigue=st.session_state.fatigue,
            player_profile=st.session_state.player_profile,
            level=st.session_state.level
        )

# =====================================================
# FOOTER
# =====================================================
st.markdown("""
<div style="text-align: center; padding: 30px 0 10px 0; margin-top: 40px;
            border-top: 1px solid rgba(56, 189, 248, 0.2);">
    <p style="color: #64748b; font-size: 0.9rem;">
        🏸 Smart Badminton AI System | SIH 2026 — Fitness &amp; Sports (Hardware)
    </p>
    <p style="color: #475569; font-size: 0.8rem;">
        Racket-mounted MPU6050 · Swing detection · ML stroke classification ·
        Project-defined fitness-related performance indicators · Longitudinal player intelligence
    </p>
    <p style="color: #475569; font-size: 0.75rem;">
        Not a medical device. Not direct physiological measurement.
    </p>
</div>
""", unsafe_allow_html=True)