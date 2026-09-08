import streamlit as st
import pandas as pd
import joblib
import os
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
# CUSTOM CSS - Dark Sports Analytics Theme
# =====================================================
st.markdown("""
<style>
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
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(56, 189, 248, 0.15);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
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
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(145deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: white !important;
        border: 1px solid rgba(56, 189, 248, 0.5) !important;
    }
    .css-1d391kg, .css-1lcbmhc {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    h1, h2, h3 {
        color: #f8fafc !important;
        font-weight: 700 !important;
    }
    h1 {
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.3);
    }
    .stContainer {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid rgba(56, 189, 248, 0.15);
    }
    .stButton>button {
        background: linear-gradient(145deg, #0ea5e9 0%, #0284c7 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(145deg, #38bdf8 0%, #0ea5e9 100%);
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);
        transform: translateY(-2px);
    }
    .stDataFrame {
        background: #1e293b;
        border-radius: 12px;
        border: 1px solid rgba(56, 189, 248, 0.2);
    }
    .stProgress > div > div {
        background: linear-gradient(90deg, #0ea5e9 0%, #38bdf8 100%);
        border-radius: 10px;
    }
    .stAlert {
        border-radius: 12px;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .stSelectbox > div > div {
        background: #1e293b;
        border-radius: 10px;
        border: 1px solid rgba(56, 189, 248, 0.2);
        color: white;
    }
    .stSlider > div > div > div {
        background: #0ea5e9;
    }
    hr {
        border-color: rgba(56, 189, 248, 0.2);
    }
</style>
""", unsafe_allow_html=True)

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
        st.warning("⚠ Threshold file not found. Running calibration...")
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
        st.success("✅ Calibration completed & threshold created")
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
    drop_pct = stroke_dist.get("DROP", 0)
    clear_pct = stroke_dist.get("CLEAR", 0)
    drive_pct = stroke_dist.get("DRIVE", 0)
    avg_power = summary["avg_power"]
    std_power = summary["std_power"]
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
    n = len(df)
    if n < 10:
        return {
            "fatigue_score": 0,
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
    speed_drop = ((early_speed - late_speed) / (early_speed + 1e-6)) * 100
    impact_drop = ((early_impact - late_impact) / (early_impact + 1e-6)) * 100
    power_drop = ((early_power - late_power) / (early_power + 1e-6)) * 100
    fatigue_score = np.mean([speed_drop, impact_drop, power_drop])
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
    speed_low = df["speed"].quantile(0.25)
    speed_high = df["speed"].quantile(0.75)
    impact_low = df["impact"].quantile(0.25)
    impact_high = df["impact"].quantile(0.75)
    power_std = summary["std_power"]
    power_mean = summary["avg_power"]
    ratio = summary["avg_speed"] / (summary["avg_impact"] + 1e-6)
    if ratio > 1.4:
        feedback.append("⚠ Timing Issue: High swing speed but low impact → late shuttle contact likely")
    elif ratio < 0.8:
        feedback.append("⚠ Timing Issue: Strong impact but low speed → early contact / poor acceleration")
    else:
        feedback.append("✔ Timing between speed and impact is balanced")
    if summary["avg_impact"] < impact_low:
        feedback.append("⚠ Impact Weakness: Below your normal baseline → inconsistent racket contact")
    elif summary["avg_impact"] < impact_high:
        feedback.append("ℹ Impact: Moderate but improvable contact strength")
    else:
        feedback.append("✔ Strong and stable shuttle impact")
    speed_std = df["speed"].std()
    if speed_std > df["speed"].mean() * 0.35:
        feedback.append("⚠ Speed inconsistency: Swing speed varies too much between shots")
    else:
        feedback.append("✔ Stable swing speed across sessions")
    if power_std > power_mean * 0.35:
        feedback.append("⚠ Power inconsistency: Unstable shot strength across rallies")
    else:
        feedback.append("✔ Consistent power output")
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
@st.cache_data
def classify():
    df = pd.read_csv(NEW_DATA_CSV)
    df = df.dropna()
    df = add_features(df)
    df = add_stroke_features(df)
    th = load_or_create_threshold()
    weak_th = th["weak_threshold"][0]
    strong_th = th["strong_threshold"][0]
    swing_model, swing_features = load_swing_model()
    stroke_model, stroke_features = load_stroke_model()
    X_swing = df[swing_features]
    df["ml_swing"] = swing_model.predict(X_swing)
    missing = [f for f in stroke_features if f not in df.columns]
    if missing:
        raise Exception(f"Missing stroke features: {missing}")
    X_stroke = df.reindex(columns=stroke_features)
    df["stroke_type"] = stroke_model.predict(X_stroke)
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
    return df, summary, comparison, gap_analysis, level, consistency_scores, stability_score, fatigue, player_profile, suggestions

# =====================================================
# HELPER FUNCTIONS FOR UI
# =====================================================
def create_radar_chart(categories, values, title, color="#0ea5e9"):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor=f'rgba(14, 165, 233, 0.3)',
        line=dict(color=color, width=3),
        name=title
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(values) * 1.2],
                gridcolor='rgba(148, 163, 184, 0.2)',
                tickfont=dict(color='#94a3b8')
            ),
            angularaxis=dict(
                tickfont=dict(color='#e2e8f0', size=14),
                gridcolor='rgba(148, 163, 184, 0.2)'
            ),
            bgcolor='rgba(30, 41, 59, 0.5)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'),
        title=dict(
            text=title,
            font=dict(size=20, color='#f8fafc'),
            x=0.5
        ),
        showlegend=False
    )
    return fig

def create_gauge_chart(value, title, max_val=100):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 18, 'color': '#e2e8f0'}},
        gauge={
            'axis': {'range': [0, max_val], 'tickcolor': '#94a3b8'},
            'bar': {'color': '#0ea5e9'},
            'bgcolor': 'rgba(30, 41, 59, 0.5)',
            'borderwidth': 2,
            'bordercolor': 'rgba(56, 189, 248, 0.3)',
            'steps': [
                {'range': [0, max_val*0.33], 'color': 'rgba(239, 68, 68, 0.2)'},
                {'range': [max_val*0.33, max_val*0.66], 'color': 'rgba(234, 179, 8, 0.2)'},
                {'range': [max_val*0.66, max_val], 'color': 'rgba(34, 197, 94, 0.2)'}
            ],
            'threshold': {
                'line': {'color': '#38bdf8', 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'),
        height=250
    )
    return fig

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-size: 2.5rem; margin-bottom: 0;">🏸</h1>
        <h2 style="font-size: 1.2rem; color: #38bdf8; margin-top: 5px;">BADMINTON AI</h2>
        <p style="color: #94a3b8; font-size: 0.8rem;">Smart Swing Analytics</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🎮 Controls")

    session_option = st.selectbox(
        "📁 Session",
        ["Current Session", "Session 1", "Session 2", "Session 3"],
        index=0
    )

    stroke_filter = st.multiselect(
        "🏸 Stroke Filter",
        ["SMASH", "DROP", "CLEAR", "DRIVE"],
        default=["SMASH", "DROP", "CLEAR", "DRIVE"]
    )

    metric_toggle = st.segmented_control(
        "📊 Primary Metric",
        options=["Speed", "Impact", "Power"],
        default="Power"
    )

    player_mode = st.toggle("🔬 Advanced Analytics", value=False)

    st.markdown("---")
    st.subheader("⚡ Quick Stats")

    if 'summary' in st.session_state:
        s = st.session_state.summary
        st.metric("Total Swings", s["total_swings"])
        st.metric("Avg Power", f"{s['avg_power']:.1f}")
        st.metric("Stability", f"{st.session_state.stability_score}/10")

    st.markdown("---")
    st.caption("© 2024 Badminton AI v2.0")

# =====================================================
# MAIN CONTENT
# =====================================================
st.markdown("""
<div style="text-align: center; padding: 10px 0 30px 0;">
    <h1 style="font-size: 2.8rem; background: linear-gradient(90deg, #0ea5e9, #38bdf8, #22d3ee); 
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🏸 SMART BADMINTON AI DASHBOARD
    </h1>
    <p style="color: #94a3b8; font-size: 1.1rem;">Advanced Swing Analytics & AI Coaching System</p>
</div>
""", unsafe_allow_html=True)

# Run classification
with st.spinner("🤖 Analyzing your swings with AI..."):
    try:
        df, summary, comparison, gap_analysis, level, consistency_scores, stability_score, fatigue, player_profile, suggestions = classify()

        st.session_state.summary = summary
        st.session_state.stability_score = stability_score
        st.session_state.df = df
        st.session_state.comparison = comparison
        st.session_state.gap_analysis = gap_analysis
        st.session_state.level = level
        st.session_state.consistency_scores = consistency_scores
        st.session_state.fatigue = fatigue
        st.session_state.player_profile = player_profile
        st.session_state.suggestions = suggestions
    except Exception as e:
        st.error(f"❌ Error during classification: {e}")
        st.stop()

# Apply stroke filter
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
    "📊 Overview",
    "📈 Performance",
    "🏆 Pro Comparison",
    "🧠 AI Coach",
    "🧬 Player Profile",
    "⚡ Fatigue & Consistency",
    "📥 Export Data"
])

# ==================== TAB 1: OVERVIEW ====================
# ==================== TAB 1: OVERVIEW ====================
with tabs[0]:
    st.markdown("### 📊 Session Overview Dashboard")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(label="Total Swings", value=int(summary_filtered["total_swings"]))
    with col2:
        st.metric(label="Avg Speed", value=f"{summary_filtered['avg_speed']:.1f}", delta=f"{comparison['gap_speed']:.1f} vs Pro")
    with col3:
        st.metric(label="Avg Impact", value=f"{summary_filtered['avg_impact']:.1f}", delta=f"{comparison['gap_impact']:.1f} vs Pro")
    with col4:
        st.metric(label="Avg Power", value=f"{summary_filtered['avg_power']:.1f}", delta=f"{comparison['gap_power']:.1f} vs Pro")
    with col5:
        st.metric(label="Consistency", value=f"{consistency_scores['consistency_score']:.1f}")
    with col6:
        st.metric(label="Stability", value=f"{stability_score}/10")

    st.markdown("---")

    # =====================================================
    # PERFORMANCE OVER TIME (3 SEPARATE GRAPHS)
    # =====================================================
    st.markdown("### 📈 Performance Over Time")

    col_speed, col_impact, col_power = st.columns(3)

    x_axis = list(range(len(df_filtered)))

    with col_speed:
        st.markdown("#### ⚡ Speed Trend")
        fig_speed = go.Figure()
        fig_speed.add_trace(go.Scatter(
            x=x_axis,
            y=df_filtered["speed"],
            mode='lines',
            line=dict(width=3),
            fill='tozeroy'
        ))
        fig_speed.update_layout(
            template='plotly_dark',
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title="Swing",
            yaxis_title="Speed"
        )
        st.plotly_chart(fig_speed, use_container_width=True)

    with col_impact:
        st.markdown("#### 💥 Impact Trend")
        fig_impact = go.Figure()
        fig_impact.add_trace(go.Scatter(
            x=x_axis,
            y=df_filtered["impact"],
            mode='lines',
            line=dict(width=3),
            fill='tozeroy'
        ))
        fig_impact.update_layout(
            template='plotly_dark',
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title="Swing",
            yaxis_title="Impact"
        )
        st.plotly_chart(fig_impact, use_container_width=True)

    with col_power:
        st.markdown("#### 🔋 Power Trend")
        fig_power = go.Figure()
        fig_power.add_trace(go.Scatter(
            x=x_axis,
            y=df_filtered["power"],
            mode='lines',
            line=dict(width=3),
            fill='tozeroy'
        ))
        fig_power.update_layout(
            template='plotly_dark',
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title="Swing",
            yaxis_title="Power"
        )
        st.plotly_chart(fig_power, use_container_width=True)

    st.markdown("---")

    # Stroke Distribution (unchanged)
    st.markdown("#### 🏸 Stroke Distribution")
    stroke_counts = df_filtered["stroke_type"].value_counts()
    fig_pie = go.Figure(data=[go.Pie(
        labels=stroke_counts.index,
        values=stroke_counts.values,
        hole=0.5
    )])
    fig_pie.update_layout(template='plotly_dark')
    st.plotly_chart(fig_pie, use_container_width=True)

    # =====================================================
    # RADAR (unchanged)
    # =====================================================
    st.markdown("#### 🎯 Player Radar")
    radar_categories = ["Speed", "Impact", "Power", "Consistency", "Efficiency"]
    radar_values = [
        summary_filtered["avg_speed"],
        summary_filtered["avg_impact"],
        summary_filtered["avg_power"],
        consistency_scores["consistency_score"],
        summary_filtered.get("avg_efficiency", 50)
    ]

    fig_radar = create_radar_chart(radar_categories, radar_values, "Player Profile")
    st.plotly_chart(fig_radar, use_container_width=True)


# ==================== TAB 2: PERFORMANCE ====================
with tabs[1]:
    st.markdown("### 📈 Performance Analytics")

    col1, col2, col3 = st.columns(3)

    # =====================================================
    # SPEED BOX PLOT
    # =====================================================
    with col1:
        st.markdown("#### ⚡ Speed Distribution")
        fig_speed_box = go.Figure()
        fig_speed_box.add_trace(go.Box(
            y=df_filtered["speed"],
            name="Speed",
            boxmean=True
        ))
        fig_speed_box.update_layout(template='plotly_dark', height=400)
        st.plotly_chart(fig_speed_box, use_container_width=True)

    # =====================================================
    # IMPACT BOX PLOT
    # =====================================================
    with col2:
        st.markdown("#### 💥 Impact Distribution")
        fig_impact_box = go.Figure()
        fig_impact_box.add_trace(go.Box(
            y=df_filtered["impact"],
            name="Impact",
            boxmean=True
        ))
        fig_impact_box.update_layout(template='plotly_dark', height=400)
        st.plotly_chart(fig_impact_box, use_container_width=True)

    # =====================================================
    # POWER BOX PLOT
    # =====================================================
    with col3:
        st.markdown("#### 🔋 Power Distribution")
        fig_power_box = go.Figure()
        fig_power_box.add_trace(go.Box(
            y=df_filtered["power"],
            name="Power",
            boxmean=True
        ))
        fig_power_box.update_layout(template='plotly_dark', height=400)
        st.plotly_chart(fig_power_box, use_container_width=True)

    st.markdown("---")

    # Scatter plot (unchanged)
    st.markdown("#### 🎯 Speed vs Impact")
    fig_scatter = px.scatter(
        df_filtered,
        x="speed",
        y="impact",
        color="stroke_type",
        size="power",
        template='plotly_dark'
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
# ==================== TAB 3: PRO COMPARISON ====================
with tabs[2]:
    st.markdown("### 🏆 Player vs Pro Comparison")

    col1, col2, col3 = st.columns(3)
    with col1:
        gap_speed_pct = (comparison["gap_speed"] / (comparison["pro_avg_speed"] + 1e-6)) * 100
        st.metric(label="Speed Gap", value=f"{comparison['player_avg_speed']:.1f}",
            delta=f"{gap_speed_pct:.1f}% vs Pro ({comparison['pro_avg_speed']:.1f})", delta_color="inverse")
    with col2:
        gap_impact_pct = (comparison["gap_impact"] / (comparison["pro_avg_impact"] + 1e-6)) * 100
        st.metric(label="Impact Gap", value=f"{comparison['player_avg_impact']:.1f}",
            delta=f"{gap_impact_pct:.1f}% vs Pro ({comparison['pro_avg_impact']:.1f})", delta_color="inverse")
    with col3:
        gap_power_pct = (comparison["gap_power"] / (comparison["pro_avg_power"] + 1e-6)) * 100
        st.metric(label="Power Gap", value=f"{comparison['player_avg_power']:.1f}",
            delta=f"{gap_power_pct:.1f}% vs Pro ({comparison['pro_avg_power']:.1f})", delta_color="inverse")

    st.markdown("---")

    st.markdown("#### 📊 Side-by-Side Comparison")
    metrics = ["Speed", "Impact", "Power", "Efficiency"]
    player_vals = [comparison["player_avg_speed"], comparison["player_avg_impact"],
                   comparison["player_avg_power"], comparison["player_avg_efficiency"]]
    pro_vals = [comparison["pro_avg_speed"], comparison["pro_avg_impact"],
                comparison["pro_avg_power"], comparison["pro_avg_efficiency"]]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(name='You', x=metrics, y=player_vals, marker_color='#0ea5e9',
        text=[f'{v:.1f}' for v in player_vals], textposition='outside', textfont=dict(color='#e2e8f0')))
    fig_bar.add_trace(go.Bar(name='Pro', x=metrics, y=pro_vals, marker_color='rgba(148, 163, 184, 0.5)',
        text=[f'{v:.1f}' for v in pro_vals], textposition='outside', textfont=dict(color='#94a3b8')))
    fig_bar.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(30, 41, 59, 0.3)',
        font=dict(color='#e2e8f0'), barmode='group', height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#e2e8f0')),
        margin=dict(l=40, r=40, t=60, b=40)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    st.markdown("#### 🌡 Gap Heatmap")
    gap_data = {
        'Metric': ['Speed', 'Impact', 'Power', 'Efficiency'],
        'Gap': [comparison['gap_speed'], comparison['gap_impact'], comparison['gap_power'], comparison['gap_efficiency']],
        'Pro_Avg': [comparison['pro_avg_speed'], comparison['pro_avg_impact'], comparison['pro_avg_power'], comparison['pro_avg_efficiency']]
    }
    gap_df = pd.DataFrame(gap_data)
    gap_df['Gap_Pct'] = (gap_df['Gap'] / (gap_df['Pro_Avg'] + 1e-6)) * 100

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=[[gap_df['Gap_Pct'].iloc[i]] for i in range(len(gap_df))], x=['Gap %'], y=gap_df['Metric'],
        colorscale=[[0, '#ef4444'], [0.5, '#fbbf24'], [1, '#34d399']],
        text=[[f'{v:.1f}%' for v in gap_df['Gap_Pct']]], texttemplate='%{text}',
        textfont=dict(size=16, color='white'),
        hovertemplate='<b>%{y}</b><br>Gap: %{z:.1f}%<extra></extra>'
    ))
    fig_heatmap.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0', size=14),
        height=300, margin=dict(l=100, r=40, t=40, b=40)
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.markdown("#### 🧠 Gap Analysis")
    for feature, msg in gap_analysis:
        if "deficit" in msg.lower() or "weak" in msg.lower() or "low" in msg.lower():
            emoji, color = "🔴", "#ef4444"
        elif "improvement" in msg.lower() or "needs" in msg.lower() or "work" in msg.lower():
            emoji, color = "🟡", "#fbbf24"
        else:
            emoji, color = "🟢", "#34d399"
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 12px; padding: 15px; margin: 10px 0; border-left: 4px solid {color};">
            <span style="font-size: 1.2rem;">{emoji}</span>
            <span style="font-weight: bold; color: {color};">{feature}</span>: {msg}
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
        <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; padding: 20px; margin: 15px 0; border: 1px solid rgba(56, 189, 248, 0.2); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);">
            <div style="display: flex; align-items: center; gap: 15px;">
                <div style="background: linear-gradient(145deg, #0ea5e9, #0284c7); width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.3rem; flex-shrink: 0;">
                    {i+1}
                </div>
                <div>
                    <p style="color: #e2e8f0; margin: 0; font-size: 1.1rem; font-weight: 600;">{suggestion}</p>
                </div>
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
        <div style="background: {bg}; border-radius: 12px; padding: 15px; margin: 10px 0; border-left: 4px solid {color};">
            <p style="color: #e2e8f0; margin: 0; font-size: 1rem;">{fb}</p>
        </div>
        """, unsafe_allow_html=True)

# ==================== TAB 5: PLAYER PROFILE ====================
with tabs[4]:
    st.markdown("### 🧬 Player Profile")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### 🎯 Player Type")
        icon = "🔥" if "Attacker" in player_profile['player_type'] else "🛡" if "Defensive" in player_profile['player_type'] else "⚖" if "All" in player_profile['player_type'] else "🎯"
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 20px; padding: 30px; text-align: center; border: 2px solid rgba(56, 189, 248, 0.3); box-shadow: 0 8px 30px rgba(14, 165, 233, 0.2);">
            <div style="font-size: 4rem; margin-bottom: 15px;">{icon}</div>
            <h2 style="color: #38bdf8; margin: 0; font-size: 1.8rem;">{player_profile['player_type']}</h2>
            <p style="color: #94a3b8; margin-top: 15px; font-size: 1rem;">{player_profile['explanation']}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📊 Style Scores")

        stroke_dist = df_filtered["stroke_type"].value_counts(normalize=True) * 100
        smash_pct = stroke_dist.get("SMASH", 0)
        clear_pct = stroke_dist.get("CLEAR", 0)
        avg_power = summary_filtered["avg_power"]

        attack_score = min(100, (smash_pct * 0.6) + (avg_power / 100))
        defense_score = min(100, (clear_pct * 0.6) + 30)
        balance_score = max(0, 100 - abs(smash_pct - clear_pct) * 2)

        st.markdown("**Attack Score**")
        st.progress(int(attack_score), text=f"{attack_score:.1f}/100")
        st.markdown("**Defense Score**")
        st.progress(int(defense_score), text=f"{defense_score:.1f}/100")
        st.markdown("**Balance Score**")
        st.progress(int(balance_score), text=f"{balance_score:.1f}/100")

    with col2:
        st.markdown("#### 🏸 Stroke Distribution")
        labels = ['SMASH', 'CLEAR', 'DROP', 'DRIVE']
        values = [player_profile['smash_pct'], player_profile['clear_pct'], player_profile['drop_pct'], player_profile['drive_pct']]
        colors = ['#ef4444', '#0ea5e9', '#fbbf24', '#34d399']

        fig_donut = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=0.6,
            marker=dict(colors=colors, line=dict(color='#1e293b', width=3)),
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
        st.markdown("#### 🎯 Performance Prediction Distribution")

        pred_counts = df_filtered["final_prediction"].value_counts()
        pred_colors = {"STRONG": "#34d399", "MEDIUM": "#fbbf24", "WEAK": "#ef4444"}

        fig_pred = go.Figure(data=[go.Bar(
            x=pred_counts.index, y=pred_counts.values,
            marker_color=[pred_colors.get(p, '#0ea5e9') for p in pred_counts.index],
            text=pred_counts.values, textposition='outside', textfont=dict(color='#e2e8f0', size=16)
        )])
        fig_pred.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(30, 41, 59, 0.3)',
            font=dict(color='#e2e8f0'), height=300, xaxis_title="Prediction", yaxis_title="Count",
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig_pred, use_container_width=True)

# ==================== TAB 6: FATIGUE & CONSISTENCY ====================
with tabs[5]:
    st.markdown("### ⚡ Fatigue & Consistency Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🫀 Fatigue Indicator")
        fatigue_color = "#34d399" if "Fresh" in fatigue["status"] else "#fbbf24" if "Mild" in fatigue["status"] else "#ef4444"
        fatigue_emoji = "✅" if "Fresh" in fatigue["status"] else "⚠️" if "Mild" in fatigue["status"] else "🔴"

        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 20px; padding: 25px; text-align: center; border: 2px solid {fatigue_color}; box-shadow: 0 8px 30px {fatigue_color}30;">
            <div style="font-size: 3rem; margin-bottom: 10px;">{fatigue_emoji}</div>
            <h3 style="color: {fatigue_color}; margin: 0;">{fatigue['status']}</h3>
            <p style="color: #94a3b8; margin-top: 10px; font-size: 2rem; font-weight: bold;">{fatigue['fatigue_score']:.1f}%</p>
            <p style="color: #64748b; margin: 0;">Fatigue Score</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📉 Drop Metrics")

        drops = [("Speed Drop", fatigue['speed_drop'], '#0ea5e9'), ("Impact Drop", fatigue['impact_drop'], '#f472b6'), ("Power Drop", fatigue['power_drop'], '#34d399')]
        for name, val, color in drops:
            st.markdown(f"**{name}**")
            fig_gauge = create_gauge_chart(abs(val), name, 50)
            st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{name}")

    with col2:
        st.markdown("#### 📊 Consistency Radar")
        consistency_categories = ["Speed CV", "Impact CV", "Power CV"]
        consistency_values = [
            (1 - consistency_scores["speed_cv"]) * 100,
            (1 - consistency_scores["impact_cv"]) * 100,
            (1 - consistency_scores["power_cv"]) * 100
        ]
        fig_cons_radar = create_radar_chart(consistency_categories, consistency_values, "Consistency Profile", "#f472b6")
        st.plotly_chart(fig_cons_radar, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📈 Consistency Metrics")

        cons_metrics = [
            ("Speed CV", consistency_scores['speed_cv'], '#0ea5e9'),
            ("Impact CV", consistency_scores['impact_cv'], '#f472b6'),
            ("Power CV", consistency_scores['power_cv'], '#34d399'),
            ("Overall Score", consistency_scores['consistency_score'], '#fbbf24')
        ]
        for name, val, color in cons_metrics:
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 10px; padding: 12px 20px; margin: 8px 0; border: 1px solid rgba(56, 189, 248, 0.1);">
                <span style="color: #94a3b8; font-weight: 600;">{name}</span>
                <span style="color: {color}; font-weight: bold; font-size: 1.2rem;">{val}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📉 Performance Drop Over Session")

    n = len(df_filtered)
    if n >= 10:
        df_filtered['swing_group'] = pd.cut(range(len(df_filtered)), bins=10, labels=False)
        grouped = df_filtered.groupby('swing_group').agg({'speed': 'mean', 'impact': 'mean', 'power': 'mean'}).reset_index()

        fig_fatigue_line = go.Figure()
        fig_fatigue_line.add_trace(go.Scatter(x=grouped['swing_group'], y=grouped['speed'], mode='lines+markers', name='Speed', line=dict(color='#0ea5e9', width=3), marker=dict(size=8)))
        fig_fatigue_line.add_trace(go.Scatter(x=grouped['swing_group'], y=grouped['impact'], mode='lines+markers', name='Impact', line=dict(color='#f472b6', width=3), marker=dict(size=8)))
        fig_fatigue_line.add_trace(go.Scatter(x=grouped['swing_group'], y=grouped['power'], mode='lines+markers', name='Power', line=dict(color='#34d399', width=3), marker=dict(size=8)))
        fig_fatigue_line.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(30, 41, 59, 0.3)',
            font=dict(color='#e2e8f0'), xaxis_title="Session Progress (Deciles)", yaxis_title="Average Value",
            height=400, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#e2e8f0')),
            margin=dict(l=40, r=40, t=60, b=40)
        )
        st.plotly_chart(fig_fatigue_line, use_container_width=True)
    else:
        st.info("📊 Not enough data for fatigue trend analysis (need at least 10 swings)")

# ==================== TAB 7: EXPORT DATA ====================
with tabs[6]:
    st.markdown("### 📥 Data Export & Raw Data")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 💾 Export Options")

        # Export filtered data
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name="badminton_filtered_data.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Export full data
        csv_full = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full Session Data (CSV)",
            data=csv_full,
            file_name="badminton_full_data.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Export summary report
        summary_report = f"""
BADMINTON AI SESSION REPORT
{'='*50}

SESSION SUMMARY:
- Total Swings: {summary_filtered['total_swings']}
- Weak Swings: {summary_filtered['weak_count']}
- Medium Swings: {summary_filtered['medium_count']}
- Strong Swings: {summary_filtered['strong_count']}

PERFORMANCE METRICS:
- Avg Speed: {summary_filtered['avg_speed']:.2f}
- Avg Impact: {summary_filtered['avg_impact']:.2f}
- Avg Power: {summary_filtered['avg_power']:.2f}
- Consistency Score: {consistency_scores['consistency_score']:.2f}/100
- Stability Score: {stability_score}/10

PRO COMPARISON:
- Speed Gap: {comparison['gap_speed']:.2f}
- Impact Gap: {comparison['gap_impact']:.2f}
- Power Gap: {comparison['gap_power']:.2f}

PLAYER LEVEL: {level}

FATIGUE STATUS: {fatigue['status']}
- Fatigue Score: {fatigue['fatigue_score']:.2f}%

PLAYER TYPE: {player_profile['player_type']}
- Smash: {player_profile['smash_pct']:.1f}%
- Clear: {player_profile['clear_pct']:.1f}%
- Drop: {player_profile['drop_pct']:.1f}%
- Drive: {player_profile['drive_pct']:.1f}%

AI COACH RECOMMENDATIONS:
"""
        for i, s in enumerate(suggestions, 1):
            summary_report += f"{i}. {s}\n"

        st.download_button(
            label="📄 Download Summary Report (TXT)",
            data=summary_report,
            file_name="badminton_session_report.txt",
            mime="text/plain",
            use_container_width=True
        )

    with col2:
        st.markdown("#### 📋 Session Quick Stats")
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; padding: 20px; border: 1px solid rgba(56, 189, 248, 0.2);">
            <p style="color: #94a3b8; margin: 5px 0;"><b>Total Swings:</b> <span style="color: #e2e8f0;">{summary_filtered['total_swings']}</span></p>
            <p style="color: #94a3b8; margin: 5px 0;"><b>Weak:</b> <span style="color: #ef4444;">{summary_filtered['weak_count']}</span></p>
            <p style="color: #94a3b8; margin: 5px 0;"><b>Medium:</b> <span style="color: #fbbf24;">{summary_filtered['medium_count']}</span></p>
            <p style="color: #94a3b8; margin: 5px 0;"><b>Strong:</b> <span style="color: #34d399;">{summary_filtered['strong_count']}</span></p>
            <p style="color: #94a3b8; margin: 5px 0;"><b>Player Level:</b> <span style="color: #38bdf8;">{level}</span></p>
            <p style="color: #94a3b8; margin: 5px 0;"><b>Player Type:</b> <span style="color: #38bdf8;">{player_profile['player_type']}</span></p>
            <p style="color: #94a3b8; margin: 5px 0;"><b>Stability:</b> <span style="color: #38bdf8;">{stability_score}/10</span></p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📊 Raw Data Table")

    # Show dataframe with styling
    display_cols = ["speed", "impact", "duration", "power", "efficiency", "stroke_type", "final_prediction"]
    available_cols = [c for c in display_cols if c in df_filtered.columns]

    st.dataframe(
        df_filtered[available_cols],
        use_container_width=True,
        height=500,
        column_config={
            "speed": st.column_config.NumberColumn("Speed", format="%.2f"),
            "impact": st.column_config.NumberColumn("Impact", format="%.2f"),
            "duration": st.column_config.NumberColumn("Duration", format="%.2f"),
            "power": st.column_config.NumberColumn("Power", format="%.2f"),
            "efficiency": st.column_config.NumberColumn("Efficiency", format="%.2f"),
            "stroke_type": st.column_config.TextColumn("Stroke Type"),
            "final_prediction": st.column_config.TextColumn("Prediction")
        }
    )

# =====================================================
# FOOTER
# =====================================================
st.markdown("""
<div style="text-align: center; padding: 30px 0 10px 0; margin-top: 40px; border-top: 1px solid rgba(56, 189, 248, 0.2);">
    <p style="color: #64748b; font-size: 0.9rem;">
        🏸 Smart Badminton AI System v2.0 | Powered by Machine Learning & Streamlit
    </p>
    <p style="color: #475569; font-size: 0.8rem;">
        Real-time swing analytics, pro comparison, and AI-powered coaching insights
    </p>
</div>
""", unsafe_allow_html=True)