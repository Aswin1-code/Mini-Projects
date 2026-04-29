import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import joblib
import os

# =====================================================
# FILE PATHS
# =====================================================
CALIBRATION_CSV = r"C:\Users\aswin\Downloads\data 1\badminton_data.csv"
NEW_DATA_CSV = r"C:\Users\aswin\Downloads\data 1\badminton_data (1).csv"
THRESHOLD_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\thresholdFile.csv"
SWING_MODEL_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\performanceClassify ml train\swing_model.pkl"
STROKE_MODEL_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\strokeClassifierModel\stroke classifier pkl\stroke_model.pkl"
PRO_DATASET_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\matlab generate pro data\pro_benchmark_dataset.csv"

# =====================================================
# STREAMLIT + PREMIUM DARK THEME
# =====================================================
st.set_page_config(
    page_title="🏸 Badminton AI Pro",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🏸",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@300;400;500;600&display=swap');
html,body,[class*="css"] {font-family:'Inter',sans-serif;}
h1,h2,h3 {font-family:'Rajdhani',sans-serif!important; letter-spacing:1px;}
.sec-title {font-family:'Rajdhani',sans-serif; font-size:1.35rem; font-weight:700; color:#00D4FF; 
            text-transform:uppercase; letter-spacing:1.5px; border-bottom:2px solid rgba(0,212,255,.25); 
            padding-bottom:8px; margin:20px 0 15px 0;}
.hl-best {background:rgba(0,200,83,.12); border:1px solid #00C853; border-radius:12px; padding:16px; margin:8px 0;}
.hl-worst {background:rgba(255,75,75,.12); border:1px solid #FF4B4B; border-radius:12px; padding:16px; margin:8px 0;}
.card-info {background:rgba(0,212,255,.08); border-left:4px solid #00D4FF; border-radius:10px; padding:12px 16px; margin:8px 0;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# ORIGINAL FUNCTIONS (Full Logic - Unchanged)
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
        st.warning("⚠ Threshold file not found. Running calibration...")
        df_cal = pd.read_csv(CALIBRATION_CSV)
        df_cal = df_cal[["speed", "impact", "duration"]].dropna().head(30)
        df_cal = add_features(df_cal)
        weak_th = df_cal["power"].quantile(0.25)
        strong_th = df_cal["power"].quantile(0.75)
        threshold_df = pd.DataFrame([{
            "weak_threshold": weak_th, "strong_threshold": strong_th,
            "avg_speed": df_cal["speed"].mean(), "avg_impact": df_cal["impact"].mean(),
            "avg_power": df_cal["power"].mean(), "avg_duration": df_cal["duration"].mean(),
            "avg_efficiency": df_cal["efficiency"].mean()
        }])
        threshold_df.to_csv(THRESHOLD_FILE, index=False)
        st.success("✅ Calibration completed!")
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
    level = "Near Pro Level 🏆" if total_gap > -200 else "Intermediate Player" if total_gap > -600 else "Needs Major Improvement"
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
    if comparison.get("gap_speed", 0) < -3:
        s.append("Increase racket swing speed using forearm acceleration")
    if comparison.get("gap_impact", 0) < -5:
        s.append("Improve shuttle contact timing")
    if comparison.get("gap_power", 0) < -500:
        s.append("Focus on explosive smash power")
    if summary.get("std_power", 0) > 400:
        s.append("Improve consistency in swing power")
    if len(s) == 0:
        s.append("Performance is close to pro level 🚀")
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

def compute_stability_score(summary, consistency_scores):
    power_score = summary["avg_power"] / (summary["avg_power"] + summary["std_power"] + 1e-6)
    power_component = power_score * 10
    consistency_component = consistency_scores["consistency_score"] / 10
    stability = (0.6 * power_component) + (0.4 * consistency_component)
    return round(min(10, stability), 2)

def classify_player_type(df, summary):
    stroke_dist = df["stroke_type"].value_counts(normalize=True) * 100
    smash_pct = stroke_dist.get("SMASH", 0)
    drop_pct = stroke_dist.get("DROP", 0)
    clear_pct = stroke_dist.get("CLEAR", 0)
    drive_pct = stroke_dist.get("DRIVE", 0)

    attacker_score = (smash_pct * 0.6) + (summary["avg_power"] / 100)
    defender_score = (clear_pct * 0.6) + (1000 / (summary["avg_power"] + 1e-6))
    balance = 100 - abs(smash_pct - clear_pct) - abs(drop_pct - drive_pct)

    if attacker_score > defender_score and smash_pct > 40:
        return {"player_type": "🔥 Attacker", "explanation": "You rely heavily on smashes and high power shots."}
    elif defender_score > attacker_score and clear_pct > 35:
        return {"player_type": "🛡 Defensive Player", "explanation": "You focus on rallies, clears, and controlled gameplay."}
    elif balance > 60:
        return {"player_type": "⚖ All-Rounder", "explanation": "Balanced mix of attacking and defensive strokes."}
    else:
        return {"player_type": "🎯 Mixed Style Player", "explanation": "No dominant pattern detected clearly."}

def fatigue_detection(df):
    n = len(df)
    if n < 10:
        return {"fatigue_score": 0, "status": "Insufficient data", "speed_drop":0, "impact_drop":0, "power_drop":0}
    early = df.iloc[:int(n * 0.4)]
    late = df.iloc[int(n * 0.6):]
    speed_drop = ((early["speed"].mean() - late["speed"].mean()) / (early["speed"].mean() + 1e-6)) * 100
    impact_drop = ((early["impact"].mean() - late["impact"].mean()) / (early["impact"].mean() + 1e-6)) * 100
    power_drop = ((early["power"].mean() - late["power"].mean()) / (early["power"].mean() + 1e-6)) * 100
    fatigue_score = np.mean([speed_drop, impact_drop, power_drop])
    status = "Fresh performance throughout session" if fatigue_score < 10 else "Mild fatigue detected" if fatigue_score < 25 else "High fatigue detected – performance drop significant"
    return {
        "fatigue_score": round(fatigue_score, 2),
        "speed_drop": round(speed_drop, 2),
        "impact_drop": round(impact_drop, 2),
        "power_drop": round(power_drop, 2),
        "status": status
    }

# =====================================================
# DATA PROCESSING
# =====================================================
@st.cache_data
def process_data():
    df = pd.read_csv(NEW_DATA_CSV).dropna()
    df = add_features(df)
    df = add_stroke_features(df)

    th = load_or_create_threshold()
    weak_th = th["weak_threshold"][0]
    strong_th = th["strong_threshold"][0]

    swing_model, swing_features = load_swing_model()
    stroke_model, stroke_features = load_stroke_model()

    df["ml_swing"] = swing_model.predict(df[swing_features])
    df["stroke_type"] = stroke_model.predict(df.reindex(columns=stroke_features))

    def rule(row):
        if row["power"] < weak_th: return "WEAK"
        elif row["power"] < strong_th: return "MEDIUM"
        return "STRONG"
    df["final_prediction"] = df.apply(rule, axis=1)
    df["swing_no"] = range(1, len(df) + 1)
    return df

df = process_data()

summary = get_session_summary(df)
comparison = compare_with_pro(df)
gap_analysis, player_level = generate_gap_analysis(comparison)
suggestions = generate_suggestions(summary, comparison)
consistency_scores = compute_consistency_scores(df, summary)
stability_score = compute_stability_score(summary, consistency_scores)
fatigue = fatigue_detection(df)
player_profile = classify_player_type(df, summary)

# =====================================================
# MAIN DASHBOARD
# =====================================================
st.markdown("""
<div style='text-align:center;padding:25px 0 15px'>
  <h1 style='background:linear-gradient(90deg,#00D4FF,#FFD700);-webkit-background-clip:text;
             -webkit-text-fill-color:transparent; font-size:2.8rem; margin:0;'>
    🏸 SMART BADMINTON AI DASHBOARD
  </h1>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🏸 Badminton AI Pro")
    st.metric("Total Swings", summary["total_swings"])
    st.metric("Player Level", player_level)

# ====================== TABS ======================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Overview", 
    "📈 Performance Trends", 
    "🔬 Analysis & Relationships", 
    "🧠 AI Coach Insights", 
    "🧬 Player Intelligence", 
    "📁 Data Explorer"
])

# ==================== TAB 1: OVERVIEW ====================
with tab1:
    st.markdown('<div class="sec-title">1. DASHBOARD TAB (MAIN SUMMARY)</div>', unsafe_allow_html=True)

    st.markdown("#### 🟢 Core Metrics")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Total Swings", summary["total_swings"])
    with c2: st.metric("Avg Speed", f"{summary['avg_speed']:.2f}")
    with c3: st.metric("Avg Impact", f"{summary['avg_impact']:.2f}")
    with c4: st.metric("Avg Power", f"{summary['avg_power']:.1f}")
    with c5: st.metric("Avg Efficiency", f"{df['efficiency'].mean():.2f}")
    with c6: st.metric("W / M / S", f"{summary['weak_count']} / {summary['medium_count']} / {summary['strong_count']}")

    st.markdown("#### 🏆 Player Status")
    colA, colB, colC = st.columns(3)
    with colA: st.metric("Player Level", player_level)
    with colB: st.metric("Stability Score", f"{stability_score}/10")
    with colC: st.metric("Consistency Score", f"{consistency_scores['consistency_score']}/100")

    st.markdown("#### 🧠 Insight Block")
    col_best, col_worst = st.columns(2)
    with col_best:
        b = summary["best_swing"]
        st.markdown(f"""
        <div class="hl-best">
            <b>🔥 BEST SWING</b><br>
            Power: <b>{b['power']:.1f}</b> | Speed: {b['speed']:.2f} | Impact: {b['impact']:.2f}
        </div>""", unsafe_allow_html=True)
    with col_worst:
        w = summary["worst_swing"]
        st.markdown(f"""
        <div class="hl-worst">
            <b>❄ WORST SWING</b><br>
            Power: <b>{w['power']:.1f}</b> | Speed: {w['speed']:.2f} | Impact: {w['impact']:.2f}
        </div>""", unsafe_allow_html=True)

    st.markdown("#### 📊 GRAPHS")
    g1, g2 = st.columns(2)
    with g1:
        fig_pie = px.pie(df, names="final_prediction", title="Swing Quality Distribution",
                        color_discrete_sequence=["#FF4B4B", "#FFD700", "#00C853"], hole=0.4)
        fig_pie.update_layout(template="plotly_dark", height=420)
        st.plotly_chart(fig_pie, use_container_width=True)

    with g2:
        bar_data = pd.DataFrame({
            "Metric": ["Speed", "Impact", "Power"],
            "Average": [summary["avg_speed"], summary["avg_impact"], summary["avg_power"]]
        })
        fig_bar = px.bar(bar_data, x="Metric", y="Average", text="Average",
                        color_discrete_sequence=["#00D4FF", "#00C853", "#FFD700"])
        fig_bar.update_layout(template="plotly_dark", height=420)
        st.plotly_chart(fig_bar, use_container_width=True)

    g3, g4 = st.columns(2)
    with g3:
        fig_stab = go.Figure(go.Indicator(mode="gauge+number", value=stability_score,
            title={"text": "Stability Score"}, gauge={"axis": {"range": [0, 10]}, "bar": {"color": "#00D4FF"}}))
        fig_stab.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_stab, use_container_width=True)

    with g4:
        fig_cons = go.Figure(go.Indicator(mode="gauge+number", value=consistency_scores["consistency_score"],
            title={"text": "Consistency Score"}, gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#FFD700"}}))
        fig_cons.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_cons, use_container_width=True)

# ==================== TAB 2: PERFORMANCE TRENDS ====================
with tab2:
    st.markdown('<div class="sec-title">2. PERFORMANCE TRENDS TAB</div>', unsafe_allow_html=True)

    st.subheader("📈 Line Chart - Performance Over Swings")
    fig_line = px.line(df, x="swing_no", y=["speed", "impact", "power", "efficiency"],
                      markers=True, title="Speed, Impact, Power & Efficiency Trend")
    fig_line.update_layout(template="plotly_dark", height=500)
    st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("📊 Rolling Average Graph")
    window = st.slider("Rolling Window Size", 3, 15, 5)
    rolling = df[["speed", "power", "efficiency"]].rolling(window=window, min_periods=1).mean()
    fig_roll = px.line(rolling, title=f"Rolling Average Trend (Window = {window})")
    fig_roll.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_roll, use_container_width=True)

    st.subheader("📉 Cumulative Power Graph")
    fig_cum = px.line(df, x="swing_no", y=df["power"].cumsum(), 
                     title="Cumulative Power Build-up Over Session")
    fig_cum.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_cum, use_container_width=True)

    st.info(f"**Trend**: {fatigue['status']} | Fatigue Score: {fatigue.get('fatigue_score', 0)}% drop (Early vs Late Swings)")

# ==================== TAB 3: ANALYSIS & RELATIONSHIPS ====================
with tab3:
    st.markdown('<div class="sec-title">3. ANALYSIS & RELATIONSHIPS TAB</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔵 Speed vs Impact Scatter Plot")
        fig_scatter = px.scatter(df, x="speed", y="impact", color="stroke_type", 
                                size="power", hover_data=["final_prediction", "efficiency"],
                                title="Technique Efficiency & Style Clusters")
        fig_scatter.update_layout(template="plotly_dark", height=500)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col2:
        st.subheader("📦 Box Plot - Distributions")
        fig_box = px.box(df, y=["speed", "impact", "power"], title="Consistency & Outliers")
        fig_box.update_layout(template="plotly_dark", height=500)
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("🌡 Power Intensity Heatmap")
    fig_heat = go.Figure(go.Heatmap(
        z=df["power"].values.reshape(1, -1),
        x=df["swing_no"].values,
        colorscale="Viridis",
        colorbar=dict(title="Power")
    ))
    fig_heat.update_layout(template="plotly_dark", height=200, title="Power Intensity Across Swings")
    st.plotly_chart(fig_heat, use_container_width=True)

    st.subheader("🕸 Player Profile Radar Chart")
    radar_values = [
        min(100, summary["avg_power"] / 15),
        min(100, summary["avg_speed"] * 2),
        min(100, df["efficiency"].mean()),
        consistency_scores["consistency_score"],
        min(100, (df["speed"] + df["impact"] + df["power"]).mean() / 30)
    ]
    fig_radar = go.Figure(go.Scatterpolar(
        r=radar_values + [radar_values[0]],
        theta=["Power", "Speed", "Efficiency", "Consistency", "Intensity"],
        fill='toself', line_color='#00D4FF'
    ))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                           template="plotly_dark", height=450, title="Player Capability Radar")
    st.plotly_chart(fig_radar, use_container_width=True)

# ==================== TAB 4: AI COACH INSIGHTS ====================
with tab4:
    st.markdown('<div class="sec-title">4. AI COACH INSIGHTS TAB</div>', unsafe_allow_html=True)

    st.success(f"**Player Level**: {player_level}")

    st.subheader("📉 Gap Comparison vs Pro")
    gap_df = pd.DataFrame({
        "Metric": ["Speed", "Impact", "Power", "Efficiency"],
        "Player": [comparison["player_avg_speed"], comparison["player_avg_impact"], 
                  comparison["player_avg_power"], comparison["player_avg_efficiency"]],
        "Pro": [comparison["pro_avg_speed"], comparison["pro_avg_impact"], 
               comparison["pro_avg_power"], comparison["pro_avg_efficiency"]]
    })
    fig_gap = px.bar(gap_df, x="Metric", y=["Player", "Pro"], barmode="group", 
                    title="Player vs Pro Benchmark")
    fig_gap.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_gap, use_container_width=True)

    st.subheader("🔋 Fatigue Drop Analysis")
    st.metric("Fatigue Status", fatigue["status"], f"{fatigue.get('fatigue_score', 0)}% drop")
    st.write(f"Speed Drop: {fatigue.get('speed_drop', 0)}% | Power Drop: {fatigue.get('power_drop', 0)}%")

    st.subheader("🧠 Gap Analysis")
    for feat, msg in gap_analysis:
        st.info(f"**{feat}** → {msg}")

    st.subheader("🎯 AI Coach Suggestions")
    for sug in suggestions:
        st.markdown(f"<div class='card-info'>✔ {sug}</div>", unsafe_allow_html=True)

# ==================== TAB 5: PLAYER INTELLIGENCE ====================
with tab5:
    st.markdown('<div class="sec-title">5. PLAYER INTELLIGENCE TAB</div>', unsafe_allow_html=True)

    st.markdown(f"### 🏸 Player Type: **{player_profile['player_type']}**")
    st.write(player_profile['explanation'])

    st.subheader("🥧 Stroke Distribution")
    fig_stroke = px.pie(df, names="stroke_type", title="Stroke Type Distribution")
    fig_stroke.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_stroke, use_container_width=True)

    st.subheader("📊 Player Style Scores")
    attacker_score = round((df["stroke_type"].value_counts(normalize=True).get("SMASH", 0) * 60) + 
                          (summary["avg_power"] / 100), 1)
    
    col_score1, col_score2, col_score3 = st.columns(3)
    with col_score1:
        st.progress(min(attacker_score/100, 1.0), text=f"🔥 Attacker: {attacker_score}")
    with col_score2:
        st.progress(0.65, text="🛡 Defender: 65")
    with col_score3:
        st.progress(0.75, text="⚖ Balance: 75")

# ==================== TAB 6: DATA EXPLORER ====================
with tab6:
    st.markdown('<div class="sec-title">6. DATA EXPLORER TAB</div>', unsafe_allow_html=True)

    # Filter options
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        stroke_filter = st.multiselect("Filter by Stroke Type", options=df["stroke_type"].unique(), 
                                      default=df["stroke_type"].unique())
    with col_f2:
        pred_filter = st.multiselect("Filter by Prediction", options=df["final_prediction"].unique(), 
                                    default=df["final_prediction"].unique())

    filtered_df = df[(df["stroke_type"].isin(stroke_filter)) & (df["final_prediction"].isin(pred_filter))]

    st.dataframe(filtered_df, use_container_width=True, height=650)

    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=filtered_df.to_csv(index=False).encode(),
        file_name="badminton_analysis_filtered.csv",
        mime="text/csv"
    )

st.caption("🏸 Smart Badminton AI Dashboard | Premium Dark Sports Analytics Theme")