import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import joblib
import os

# =====================================================
# FILE PATHS (Update these if needed)
# =====================================================
CALIBRATION_CSV = r"C:\Users\aswin\Downloads\data 1\badminton_data.csv"
NEW_DATA_CSV = r"C:\Users\aswin\Downloads\data 1\badminton_data (1).csv"
THRESHOLD_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\thresholdFile.csv"
SWING_MODEL_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\performanceClassify ml train\swing_model.pkl"
STROKE_MODEL_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\strokeClassifierModel\stroke classifier pkl\stroke_model.pkl"
PRO_DATASET_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\matlab generate pro data\pro_benchmark_dataset.csv"

# =====================================================
# [YOUR ORIGINAL FUNCTIONS - COPIED AS IS]
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

def load_swing_model():
    model_pack = joblib.load(SWING_MODEL_FILE)
    return model_pack["model"], model_pack["features"]

def load_stroke_model():
    model_pack = joblib.load(STROKE_MODEL_FILE)
    return model_pack["model"], model_pack["features"]

def load_or_create_threshold():
    if not os.path.exists(THRESHOLD_FILE):
        st.warning("Threshold file not found. Running calibration...")
        df = pd.read_csv(CALIBRATION_CSV)
        df = df[["speed", "impact", "duration"]].dropna().head(30)
        df = add_features(df)
        weak_th = df["power"].quantile(0.25)
        strong_th = df["power"].quantile(0.75)
        threshold_df = pd.DataFrame([{
            "weak_threshold": weak_th, "strong_threshold": strong_th,
            "avg_speed": df["speed"].mean(), "avg_impact": df["impact"].mean(),
            "avg_power": df["power"].mean(), "avg_duration": df["duration"].mean(),
            "avg_efficiency": df["efficiency"].mean()
        }])
        threshold_df.to_csv(THRESHOLD_FILE, index=False)
        st.success("Calibration completed!")
    return pd.read_csv(THRESHOLD_FILE)

def compare_with_pro(player_df):
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
        s.append("Performance is close to pro level")
    return s[:5]

def compute_consistency_scores(df, summary):
    speed_cv = df["speed"].std() / (df["speed"].mean() + 1e-6)
    impact_cv = df["impact"].std() / (df["impact"].mean() + 1e-6)
    power_cv = df["power"].std() / (df["power"].mean() + 1e-6)
    consistency_score = 100 * (1 - min(1, (speed_cv + impact_cv + power_cv) / 3))
    return {
        "speed_cv": round(speed_cv, 3),
        "impact_cv": round(impact_cv, 3),
        "power_cv": round(power_cv, 3),
        "consistency_score": round(consistency_score, 2)
    }

def compute_stability_score(df, summary, consistency_scores):
    power_score = summary["avg_power"] / (summary["avg_power"] + summary["std_power"] + 1e-6)
    power_component = power_score * 10
    consistency_component = consistency_scores["consistency_score"] / 10
    stability = (0.6 * power_component) + (0.4 * consistency_component)
    return round(min(10, stability), 2)

def classify_player_type(df, summary):
    stroke_dist = df["stroke_type"].value_counts(normalize=True) * 100
    smash_pct = stroke_dist.get("SMASH", 0)
    clear_pct = stroke_dist.get("CLEAR", 0)
    drop_pct = stroke_dist.get("DROP", 0)
    drive_pct = stroke_dist.get("DRIVE", 0)

    attacker_score = (smash_pct * 0.6) + (summary["avg_power"] / 100)
    defender_score = (clear_pct * 0.6) + (1 / (summary["avg_power"] + 1e-6)) * 1000
    balance = 100 - abs(smash_pct - clear_pct) - abs(drop_pct - drive_pct)

    if attacker_score > defender_score and smash_pct > 40:
        return {"player_type": "🔥 Attacker", "explanation": "You rely heavily on smashes and high power shots.", 
                "smash_pct": round(smash_pct, 2), "clear_pct": round(clear_pct, 2)}
    elif defender_score > attacker_score and clear_pct > 35:
        return {"player_type": "🛡 Defensive Player", "explanation": "You focus on rallies, clears, and controlled gameplay.",
                "smash_pct": round(smash_pct, 2), "clear_pct": round(clear_pct, 2)}
    elif balance > 60:
        return {"player_type": "⚖ All-Rounder", "explanation": "Balanced mix of attacking and defensive strokes.",
                "smash_pct": round(smash_pct, 2), "clear_pct": round(clear_pct, 2)}
    else:
        return {"player_type": "🎯 Mixed Style Player", "explanation": "No dominant pattern detected clearly.",
                "smash_pct": round(smash_pct, 2), "clear_pct": round(clear_pct, 2)}

def fatigue_detection(df):
    n = len(df)
    if n < 10:
        return {"fatigue_score": 0, "status": "Insufficient data", "speed_drop": 0, "impact_drop": 0, "power_drop": 0}
    
    early = df.iloc[:int(n * 0.4)]
    late = df.iloc[int(n * 0.6):]
    
    speed_drop = ((early["speed"].mean() - late["speed"].mean()) / (early["speed"].mean() + 1e-6)) * 100
    impact_drop = ((early["impact"].mean() - late["impact"].mean()) / (early["impact"].mean() + 1e-6)) * 100
    power_drop = ((early["power"].mean() - late["power"].mean()) / (early["power"].mean() + 1e-6)) * 100
    
    fatigue_score = np.mean([speed_drop, impact_drop, power_drop])
    
    status = "Fresh performance" if fatigue_score < 10 else "Mild fatigue" if fatigue_score < 25 else "High fatigue detected"
    
    return {
        "fatigue_score": round(fatigue_score, 2),
        "speed_drop": round(speed_drop, 2),
        "impact_drop": round(impact_drop, 2),
        "power_drop": round(power_drop, 2),
        "status": status
    }

def technique_feedback(df, summary):
    # You can expand this later
    return ["Timing and consistency analysis completed."]

# =====================================================
# STREAMLIT APP
# =====================================================
st.set_page_config(
    page_title="Badminton AI Dashboard",
    page_icon="🏸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {background-color: #0e1117; color: white;}
    .metric-card {background-color: #1c1f26; border-radius: 10px; padding: 15px;}
    .stPlotlyChart {background-color: #1c1f26; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

st.title("🏸 SMART BADMINTON AI DASHBOARD")
st.markdown("### Real-time Swing Analysis & Pro Coaching System")

# Load and Process Data
@st.cache_data
def load_and_process_data():
    df = pd.read_csv(NEW_DATA_CSV)
    df = df.dropna()
    df = add_features(df)
    df = add_stroke_features(df)

    th = load_or_create_threshold()
    weak_th = th["weak_threshold"][0]
    strong_th = th["strong_threshold"][0]

    swing_model, swing_features = load_swing_model()
    stroke_model, stroke_features = load_stroke_model()

    df["ml_swing"] = swing_model.predict(df[swing_features])
    df["stroke_type"] = stroke_model.predict(df[stroke_features])

    def rule(row):
        if row["power"] < weak_th:
            return "WEAK"
        elif row["power"] < strong_th:
            return "MEDIUM"
        else:
            return "STRONG"
    df["final_prediction"] = df.apply(rule, axis=1)

    return df

df = load_and_process_data()

summary = get_session_summary(df)
comparison = compare_with_pro(df)
gap_analysis, level = generate_gap_analysis(comparison)
suggestions = generate_suggestions(summary, comparison)
consistency_scores = compute_consistency_scores(df, summary)
stability_score = compute_stability_score(df, summary, consistency_scores)
fatigue = fatigue_detection(df)
player_profile = classify_player_type(df, summary)

# ================= SIDEBAR =================
with st.sidebar:
    st.header("🎛 Controls")
    st.markdown("---")
    
    stroke_filter = st.multiselect(
        "Filter by Stroke Type",
        options=df["stroke_type"].unique(),
        default=df["stroke_type"].unique()
    )
    
    view_mode = st.radio("View Mode", ["Beginner", "Advanced"], horizontal=True)
    
    if st.button("🔄 Re-run Analysis"):
        st.rerun()

# Filter data based on sidebar
filtered_df = df[df["stroke_type"].isin(stroke_filter)]

# ================= TABS =================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Overview", "📈 Performance Analytics", "🏆 Pro Comparison", 
    "🧠 AI Coach", "🧬 Player Profile", "⚡ Fatigue & Consistency", "📥 Export"
])

# TAB 1: Overview
with tab1:
    st.subheader("📊 Session Overview")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total Swings", summary["total_swings"])
    with col2:
        st.metric("Avg Speed", f"{summary['avg_speed']:.1f}")
    with col3:
        st.metric("Avg Impact", f"{summary['avg_impact']:.1f}")
    with col4:
        st.metric("Avg Power", f"{summary['avg_power']:.0f}")
    with col5:
        st.metric("Consistency", f"{consistency_scores['consistency_score']}/100", 
                 delta="High" if consistency_scores['consistency_score'] > 70 else "Improve")
    with col6:
        st.metric("Stability", f"{stability_score}/10")

    # Time Series
    st.subheader("Performance Over Swings")
    fig_line = px.line(filtered_df.reset_index(), x=filtered_df.index, 
                       y=["speed", "impact", "power"],
                       labels={"index": "Swing Number", "value": "Value"},
                       title="Swing Metrics Trend")
    fig_line.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_line, use_container_width=True)

    # Stroke Distribution
    col_a, col_b = st.columns(2)
    with col_a:
        fig_pie = px.pie(df, names="stroke_type", title="Stroke Distribution")
        fig_pie.update_traces(textinfo='percent+label')
        fig_pie.update_layout(template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)

# TAB 2: Performance Analytics
with tab2:
    st.subheader("Detailed Performance Analytics")
    
    col1, col2 = st.columns(2)
    with col1:
        fig_hist = px.histogram(df, x="power", color="final_prediction", 
                               title="Power Distribution by Quality")
        fig_hist.update_layout(template="plotly_dark")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        fig_scatter = px.scatter(df, x="speed", y="impact", color="stroke_type",
                                size="power", hover_data=["final_prediction"],
                                title="Speed vs Impact (Bubble = Power)")
        fig_scatter.update_layout(template="plotly_dark")
        st.plotly_chart(fig_scatter, use_container_width=True)

# TAB 3: Pro Comparison
with tab3:
    st.subheader("🏆 You vs Professional Benchmark")
    
    metrics = ["speed", "impact", "power"]
    for m in metrics:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric(f"{m.capitalize()}", 
                     f"{comparison[f'player_avg_{m}']}", 
                     f"{comparison[f'gap_{m}']}")
        with col2:
            fig = go.Figure()
            fig.add_trace(go.Bar(name='You', x=[m], y=[comparison[f'player_avg_{m}']], marker_color='#00ff88'))
            fig.add_trace(go.Bar(name='Pro', x=[m], y=[comparison[f'pro_avg_{m}']], marker_color='#ff8800'))
            fig.update_layout(template="plotly_dark", height=200, showlegend=False, title=f"{m.capitalize()} Comparison")
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Gap Analysis")
    for feature, message in gap_analysis:
        st.info(f"**{feature}**: {message}")

    st.success(f"**Overall Level: {level}**")

# TAB 4: AI Coach
with tab4:
    st.subheader("🧠 AI Coach Recommendations")
    for i, sug in enumerate(suggestions):
        st.markdown(f"""
        <div style="background-color:#1c1f26; padding:15px; border-radius:10px; margin:10px 0;">
            <strong>💡 Recommendation {i+1}</strong><br>
            {sug}
        </div>
        """, unsafe_allow_html=True)

# TAB 5: Player Profile
with tab5:
    st.subheader("🧬 Your Playing Style")
    st.markdown(f"# {player_profile['player_type']}")
    st.write(player_profile['explanation'])

    # Attack / Defense bars
    attacker_score = (df["stroke_type"].value_counts(normalize=True).get("SMASH", 0) * 100 * 0.6) + (summary["avg_power"] / 100)
    st.progress(min(1.0, attacker_score/100), text="Attack Style")
    st.progress(0.65, text="Defense Style")  # placeholder - can improve

# TAB 6: Fatigue & Consistency
with tab6:
    st.subheader("⚡ Fatigue & Consistency Analysis")
    
    st.metric("Fatigue Status", fatigue["status"], f"{fatigue['fatigue_score']}% drop")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Consistency Metrics**")
        st.write(f"Speed CV: {consistency_scores['speed_cv']}")
        st.write(f"Impact CV: {consistency_scores['impact_cv']}")
        st.write(f"Power CV: {consistency_scores['power_cv']}")
        st.metric("Overall Consistency", f"{consistency_scores['consistency_score']}/100")

    with col2:
        st.write("**Stability Score**")
        st.metric("Stability", f"{stability_score}/10", help="Combines power and consistency")

# TAB 7: Raw Data
with tab7:
    st.subheader("📥 Raw Data & Export")
    st.dataframe(filtered_df, use_container_width=True)
    
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name="badminton_analysis_export.csv",
        mime="text/csv"
    )

st.caption("🏸 Smart Badminton AI Dashboard | Built with ❤️ for performance improvement")