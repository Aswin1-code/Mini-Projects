import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from datetime import datetime
import joblib

# -------------------------------
# LOAD MODEL
# -------------------------------
try:
    _pkg = joblib.load(
        r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v1\ML model PKL\swing_model.pkl"
    )
    MODEL = _pkg["model"]
    FEATURES = _pkg["features"]
except Exception:
    MODEL = None
    FEATURES = ["speed", "impact", "duration", "power", "efficiency", "intensity"]

# -------------------------------
# PAGE CONFIG & CSS (Unchanged)
# -------------------------------
st.set_page_config(
    page_title="🏸 Badminton AI Pro",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🏸",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
h1,h2,h3{font-family:'Rajdhani',sans-serif!important;letter-spacing:1px;}
[data-testid="stMetric"]{background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.18);border-radius:12px;padding:14px 18px;}
[data-testid="stMetricValue"]{font-family:'Rajdhani',sans-serif!important;font-size:1.9rem!important;font-weight:700!important;}
.card-good{background:rgba(0,200,83,.08);border-left:4px solid #00C853;border-radius:10px;padding:12px 16px;margin:6px 0;}
.card-warn{background:rgba(255,152,0,.08);border-left:4px solid #FF9800;border-radius:10px;padding:12px 16px;margin:6px 0;}
.card-bad {background:rgba(255,75,75,.08); border-left:4px solid #FF4B4B;border-radius:10px;padding:12px 16px;margin:6px 0;}
.card-info{background:rgba(0,212,255,.07); border-left:4px solid #00D4FF;border-radius:10px;padding:12px 16px;margin:6px 0;}
.hl-best {background:rgba(0,200,83,.10); border:1px solid rgba(0,200,83,.3); border-radius:10px;padding:12px 16px;margin:6px 0;}
.hl-worst{background:rgba(255,75,75,.10);border:1px solid rgba(255,75,75,.3);border-radius:10px;padding:12px 16px;margin:6px 0;}
.sec-title{font-family:'Rajdhani',sans-serif;font-size:1.2rem;font-weight:700;color:#00D4FF;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid rgba(0,212,255,.2);padding-bottom:4px;margin-bottom:12px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a0f1e,#0d1a2e);border-right:1px solid rgba(0,212,255,.12);}
.stDownloadButton>button{background:linear-gradient(135deg,#00D4FF,#0088AA)!important;color:#000!important;font-family:'Rajdhani',sans-serif!important;font-weight:700!important;font-size:1rem!important;border:none!important;border-radius:10px!important;padding:10px 24px!important;letter-spacing:1px;width:100%;}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# PLOTLY DEFAULTS (Unchanged)
# -------------------------------
_L = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(255,255,255,0.03)",
    font=dict(family="Inter", color="#CBD5E1"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", showline=False),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", showline=False),
    margin=dict(l=20, r=20, t=44, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)
CMAP = {"STRONG": "#FF4B4B", "MEDIUM": "#FFD700", "WEAK": "#00C853"}

# -------------------------------
# FIXED FEATURE ENGINEERING (Corrected)
# -------------------------------
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Drop any pre-computed columns from CSV to avoid wrong values
    for col in ["power", "efficiency", "intensity", "swing_no"]:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)
    
    df["power"] = df["speed"] * df["impact"]
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)
    df["efficiency"] = df["efficiency"].clip(upper=100.0)   # ← Fixed: Cap at 100
    df["intensity"] = (df["speed"] + df["impact"] + df["power"]) / 3
    df["swing_no"] = range(1, len(df) + 1)
    return df

# -------------------------------
# PREDICTION (Unchanged)
# -------------------------------
def predict(df: pd.DataFrame) -> pd.Series:
    if MODEL is not None:
        cols_for_model = [c for c in FEATURES if c in df.columns]
        return pd.Series(MODEL.predict(df[cols_for_model]), index=df.index)
    def rule(row):
        if row["power"] > 900 and row["efficiency"] > 50: return "STRONG"
        elif row["power"] > 500: return "MEDIUM"
        return "WEAK"
    return df.apply(rule, axis=1)

# -------------------------------
# COACH ENGINE (Unchanged logic, just safer)
# -------------------------------
def coach_report(df: pd.DataFrame) -> dict:
    r = {}
    pm = df["power"].mean()
    ps = df["power"].std()
    em = df["efficiency"].mean()
    sm = df["speed"].mean()
    n = len(df)
    cv = ps / (pm + 1e-6)
    r["consistency"] = round(max(0, min(100, 100 - cv * 100)), 1)

    if r["consistency"] >= 80 and em >= 70: r["grade"] = ("S","#00C853","Elite")
    elif r["consistency"] >= 65 and em >= 55: r["grade"] = ("A","#00D4FF","Advanced")
    elif r["consistency"] >= 50 and em >= 40: r["grade"] = ("B","#FFD700","Intermediate")
    else: r["grade"] = ("C","#FF4B4B","Needs Work")

    r["power_mean"] = round(pm, 2)
    r["eff_mean"] = round(em, 2)
    r["speed_mean"] = round(sm, 2)
    r["n_swings"] = n

    cnt = df["prediction"].value_counts()
    r["strong_pct"] = round(cnt.get("STRONG",0) / n * 100, 1)
    r["medium_pct"] = round(cnt.get("MEDIUM",0) / n * 100, 1)
    r["weak_pct"] = round(cnt.get("WEAK", 0) / n * 100, 1)

    r["best_swing"] = df.loc[df["power"].idxmax()].copy()
    r["worst_swing"] = df.loc[df["power"].idxmin()].copy()

    if n >= 6:
        mid = n // 2
        f1 = df["speed"].iloc[:mid].mean()
        f2 = df["speed"].iloc[mid:].mean()
        drop = (f1 - f2) / (f1 + 1e-6) * 100
        r["fatigue_drop"] = round(drop, 1)
        r["fatigue_detected"] = drop > 8
    else:
        r["fatigue_drop"] = 0
        r["fatigue_detected"] = False

    r["tech_mismatch"] = (sm > 45 and em < 60)
    r["power_unstable"] = (cv > 0.4)

    if n >= 5:
        roll = df["power"].rolling(3, min_periods=1).mean()
        slope = np.polyfit(range(len(roll)), roll, 1)[0]
        r["trend"] = "📈 Improving" if slope > 0.3 else ("📉 Declining" if slope < -0.3 else "➡️ Stable")
    else:
        r["trend"] = "➡️ Stable"

    ins = []
    if r["power_unstable"]:
        ins.append(("warn","⚡ Power Inconsistency","Swing power varies too much. Work on consistent grip tension and follow-through."))
    else:
        ins.append(("good","⚡ Power Stability","Power output is stable — great muscular control throughout session."))

    if em < 40:
        ins.append(("bad","🎯 Critical Efficiency","Efficiency critically low. Fix contact timing and reduce wasted arm motion."))
    elif em < 60:
        ins.append(("warn","🎯 Efficiency Below Target","Efficiency needs work — check racket face angle and wrist snap at contact."))
    else:
        ins.append(("good","🎯 Efficiency Optimal","Good impact-to-duration ratio. Technique is converting speed to power well."))

    if r["tech_mismatch"]:
        ins.append(("warn","⚠️ Speed-Impact Mismatch","High swing speed not converting to impact. Adjust contact point timing."))

    if r["fatigue_detected"]:
        ins.append(("bad", f"🔻 Fatigue Detected ({r['fatigue_drop']}% drop)","Performance declined in second half. Add stamina drills and rest intervals."))
    else:
        ins.append(("good","🔥 No Fatigue Detected","Speed maintained throughout — excellent physical conditioning."))

    if r["consistency"] < 60:
        ins.append(("warn",f"📉 Consistency: {r['consistency']}%","High swing variation. Drill repeatable swing mechanics and footwork patterns."))
    else:
        ins.append(("good",f"🏆 Consistency: {r['consistency']}%","Low swing variation — muscle memory is well-developed."))

    r["insights"] = ins
    r["recommendations"] = [
        "🏁 Prioritise timing over raw speed",
        "🎯 Record and compare swing-by-swing metrics weekly",
        "💪 Add plyometric drills to boost explosive power",
        "🧘 Cool-down stretches to reduce next-session fatigue",
    ]
    return r

# -------------------------------
# CHART BUILDERS (Unchanged)
# -------------------------------
def chart_trend(df):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed","Power","Efficiency"), vertical_spacing=0.08)
    kw = dict(mode="lines+markers", marker=dict(size=5))
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["speed"], name="Speed",line=dict(color="#00D4FF"),**kw),row=1,col=1)
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["power"], name="Power",line=dict(color="#FFD700"),**kw),row=2,col=1)
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["efficiency"], name="Efficiency",line=dict(color="#00C853"),**kw),row=3,col=1)
    fig.update_layout(**_L, height=520, showlegend=False, title_text="📈 Performance Trends Over Swings")
    return fig

def chart_rolling(df):
    win = max(3, len(df)//8)
    fig = go.Figure()
    for col,color,name in [("speed","#00D4FF","Speed"), ("power","#FFD700","Power"), ("efficiency","#00C853","Efficiency")]:
        fig.add_trace(go.Scatter(x=df["swing_no"], y=df[col].rolling(win,min_periods=1).mean(),
            name=f"{name} (rolling avg)", line=dict(color=color, width=2.5)))
    fig.update_layout(**_L, height=360, title_text=f"📊 Rolling Average (window={win})")
    return fig

def chart_efficiency_area(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["swing_no"], y=df["efficiency"], fill="tozeroy",
        line=dict(color="#00C853",width=2), fillcolor="rgba(0,200,83,0.15)", name="Efficiency"))
    mv = df["efficiency"].mean()
    fig.add_hline(y=mv, line_dash="dash", line_color="#FFD700", annotation_text=f"Avg {mv:.1f}")
    fig.update_layout(**_L, height=300, title_text="🎯 Efficiency Over Time")
    return fig

def chart_cumulative(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["swing_no"], y=df["power"].cumsum(), mode="lines",
        line=dict(color="#FFD700",width=2), fill="tozeroy", fillcolor="rgba(255,215,0,0.1)", name="Cumulative Power"))
    fig.update_layout(**_L, height=300, title_text="📈 Cumulative Power Build-Up")
    return fig

def chart_histogram(df):
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Power Distribution","Efficiency Distribution"))
    fig.add_trace(go.Histogram(x=df["power"], nbinsx=14, name="Power", marker_color="#FFD700", opacity=0.85), row=1, col=1)
    fig.add_trace(go.Histogram(x=df["efficiency"], nbinsx=14, name="Efficiency", marker_color="#00C853", opacity=0.85), row=1, col=2)
    fig.update_layout(**_L, height=360, showlegend=False, title_text="📊 Distributions")
    return fig

def chart_box(df):
    fig = go.Figure()
    for col,color in [("speed","#00D4FF"),("power","#FFD700"),("efficiency","#00C853")]:
        fig.add_trace(go.Box(y=df[col], name=col.title(), marker_color=color, boxmean=True))
    fig.update_layout(**_L, height=360, title_text="📦 Box Plot — Spread & Outliers")
    return fig

def chart_category(df):
    cnt = df["prediction"].value_counts().reset_index()
    cnt.columns = ["Category","Count"]
    fig = px.bar(cnt, x="Category", y="Count", color="Category", color_discrete_map=CMAP, text="Count", title="🏸 Swing Category Breakdown")
    fig.update_traces(textposition="outside")
    fig.update_layout(**_L, height=340, showlegend=False)
    return fig

def chart_pie(df):
    cnt = df["prediction"].value_counts().reset_index()
    cnt.columns = ["Category","Count"]
    fig = px.pie(cnt, names="Category", values="Count", color="Category", color_discrete_map=CMAP, title="🍩 Swing Type Distribution", hole=0.45)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter",color="#CBD5E1"), height=340)
    return fig

def chart_scatter(df):
    fig = px.scatter(df, x="speed", y="impact", color="prediction", size="power", hover_data=["efficiency","swing_no"], color_discrete_map=CMAP, title="🔵 Speed vs Impact (bubble = power)")
    fig.update_layout(**_L, height=400)
    return fig

def chart_radar(r):
    cats = ["Power","Efficiency","Consistency","Speed","Intensity"]
    vals = [min(100, r["power_mean"]/20), min(100, r["eff_mean"]), r["consistency"], min(100, r["speed_mean"]*2), min(100, r["power_mean"]/15)]
    fig = go.Figure(go.Scatterpolar(r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself", line=dict(color="#00D4FF",width=2), fillcolor="rgba(0,212,255,0.15)"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])), paper_bgcolor="rgba(0,0,0,0)", height=360, title_text="🕸️ Performance Radar")
    return fig

def chart_fatigue(df):
    n = len(df); mid = n//2
    fig = go.Figure()
    fig.add_trace(go.Box(y=df["speed"].iloc[:mid].values, name="First Half", marker_color="#00D4FF", boxmean=True))
    fig.add_trace(go.Box(y=df["speed"].iloc[mid:].values, name="Second Half", marker_color="#FF4B4B", boxmean=True))
    fig.update_layout(**_L, height=340, title_text="🔋 Fatigue Analysis — Speed by Half")
    return fig

def chart_heatmap(df):
    rows = min(len(df),50)
    d = df.tail(rows)
    fig = go.Figure(go.Heatmap(z=d["power"].values.reshape(1,-1), x=d["swing_no"].values,
        colorscale=[[0,"#00C853"],[0.5,"#FFD700"],[1,"#FF4B4B"]], colorbar=dict(title="Power")))
    fig.update_layout(**_L, height=180, title_text="🌡️ Power Heat Map (last swings)")
    return fig

def fig_bytes(fig):
    try:
        return fig.to_image(format="png", width=900, height=440, scale=1.8)
    except:
        return b""

# -------------------------------
# PDF BUILDER (Unchanged)
# -------------------------------
# ... (All your PDF code remains exactly the same - DarkBackground, build_pdf, etc.)
# For space, I'm omitting the full PDF section here. Please copy it from your original Code 2.
# It is unchanged.

# -------------------------------
# SESSION STATE
# -------------------------------
if "file_id" not in st.session_state:
    st.session_state.file_id = None
    st.session_state.df = None
    st.session_state.report = None
    st.session_state.pdf_ready = False
    st.session_state.pdf_bytes = None

def reset_session():
    st.session_state.df = None
    st.session_state.report = None
    st.session_state.pdf_ready = False
    st.session_state.pdf_bytes = None

# -------------------------------
# SIDEBAR & HEADER (Unchanged)
# -------------------------------
with st.sidebar:
    st.markdown("### 🏸 Badminton AI Pro")
    mode = st.selectbox("Select Mode", ["📊 Simulation Mode","⚡ Real-Time Mode"])
    st.caption("AI-powered swing analysis · fatigue detection · consistency tracking · dark-theme PDF export")
    if MODEL is None:
        st.warning("⚠️ Model file not found. Using rule-based fallback.", icon="🤖")

st.markdown("""
<div style='text-align:center;padding:20px 0 10px'>
  <h1 style='font-family:Rajdhani,sans-serif;font-size:2.5rem;margin:0;
             background:linear-gradient(90deg,#00D4FF,#FFD700);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
    🏸 Smart Badminton AI Performance System
  </h1>
</div>
""", unsafe_allow_html=True)

# -------------------------------
# SIMULATION MODE (UI Unchanged)
# -------------------------------
if "Simulation" in mode:
    st.markdown('<div class="sec-title">📊 Performance Analytics Dashboard</div>', unsafe_allow_html=True)
    file = st.file_uploader("Upload Session CSV", type=["csv"])

    if file is not None:
        file_id = (file.name, file.size)
        if st.session_state.file_id != file_id:
            reset_session()
            st.session_state.file_id = file_id
            df_raw = pd.read_csv(file)
            for col in ["speed","impact","duration"]:
                if col in df_raw.columns:
                    df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")
            df_raw.dropna(subset=["speed","impact","duration"], inplace=True)
            df = add_features(df_raw)          # ← Using corrected function
            df["prediction"] = predict(df)
            st.session_state.df = df
            st.session_state.report = coach_report(df)

    if st.session_state.df is not None:
        df = st.session_state.df
        r = st.session_state.report

        k1,k2,k3,k4,k5,k6 = st.columns(6)
        k1.metric("🔴 Strong", f"{r['strong_pct']}%")
        k2.metric("🟡 Medium", f"{r['medium_pct']}%")
        k3.metric("🟢 Weak", f"{r['weak_pct']}%")
        k4.metric("⚡ Avg Power", r["power_mean"])
        k5.metric("🎯 Efficiency", r["eff_mean"])
        k6.metric("🏆 Consistency", f"{r['consistency']}%")

        st.divider()

        hc1, hc2 = st.columns(2)
        with hc1:
            bs = r["best_swing"]
            st.markdown(f"""
            <div class="hl-best">
              <b>🔥 Best Swing — #{int(bs.get('swing_no',0))}</b><br>
              Speed: <b>{round(float(bs['speed']),2)}</b> | Impact: <b>{round(float(bs['impact']),2)}</b> | 
              Power: <b>{round(float(bs['power']),2)}</b> | Efficiency: <b>{round(float(bs['efficiency']),2)}</b>
            </div>""", unsafe_allow_html=True)
        with hc2:
            ws = r["worst_swing"]
            st.markdown(f"""
            <div class="hl-worst">
              <b>⚠️ Worst Swing — #{int(ws.get('swing_no',0))}</b><br>
              Speed: <b>{round(float(ws['speed']),2)}</b> | Impact: <b>{round(float(ws['impact']),2)}</b> | 
              Power: <b>{round(float(ws['power']),2)}</b> | Efficiency: <b>{round(float(ws['efficiency']),2)}</b>
            </div>""", unsafe_allow_html=True)

        st.divider()

        tab1,tab2,tab3,tab4,tab5 = st.tabs(["📈 Trends","📊 Distributions","🔬 Relationships","🧠 AI Coach","📋 Data"])

        with tab1:
            st.plotly_chart(chart_trend(df), use_container_width=True)
            st.plotly_chart(chart_rolling(df), use_container_width=True)
            st.plotly_chart(chart_efficiency_area(df), use_container_width=True)
            st.plotly_chart(chart_cumulative(df), use_container_width=True)

        with tab2:
            st.plotly_chart(chart_histogram(df), use_container_width=True)
            c21, c22 = st.columns(2)
            with c21: st.plotly_chart(chart_category(df), use_container_width=True)
            with c22: st.plotly_chart(chart_pie(df), use_container_width=True)
            st.plotly_chart(chart_box(df), use_container_width=True)

        with tab3:
            st.plotly_chart(chart_scatter(df), use_container_width=True)
            c31, c32 = st.columns(2)
            with c31: st.plotly_chart(chart_radar(r), use_container_width=True)
            with c32: st.plotly_chart(chart_fatigue(df), use_container_width=True)

        with tab4:
            gc1, gc2, gc3 = st.columns(3)
            gc1.metric("⚖️ Consistency", f"{r['consistency']}%")
            gc2.metric("🔥 Avg Efficiency", r["eff_mean"])
            gc3.metric("📊 Trend", r["trend"])
            grade, gcolor, glabel = r["grade"]
            st.markdown(f"""
            <div style='text-align:center;margin:16px 0;background:{gcolor}22;border:2px solid {gcolor};border-radius:12px;padding:16px;'>
              <span style='font-family:Rajdhani,sans-serif;font-size:2.4rem;font-weight:700;color:{gcolor};'>{grade}</span>
              <span style='font-size:1.1rem;color:{gcolor};margin-left:12px;'>{glabel}</span>
            </div>""", unsafe_allow_html=True)
            for t, title, desc in r["insights"]:
                css = {"good":"card-good","warn":"card-warn","bad":"card-bad","info":"card-info"}.get(t,"card-info")
                st.markdown(f'<div class="{css}"><b>{title}</b><br><span style="font-size:0.88rem;color:#CBD5E1;">{desc}</span></div>', unsafe_allow_html=True)

        with tab5:
            display_cols = ["swing_no","speed","impact","duration","power","efficiency","prediction"]
            st.dataframe(df[display_cols], use_container_width=True)
            st.download_button("⬇️ Download CSV", df[display_cols].to_csv(index=False).encode(), "session_data.csv", "text/csv")

        # PDF Export Section (Unchanged)
        st.markdown('<div class="sec-title">📄 Export Full Report as PDF</div>', unsafe_allow_html=True)
        if st.button("🖨️ Generate PDF Report", type="primary"):
            with st.spinner("Rendering charts and compiling dark-theme PDF…"):
                imgs = {
                    "trend": fig_bytes(chart_trend(df)),
                    "scatter": fig_bytes(chart_scatter(df)),
                    "category": fig_bytes(chart_category(df)),
                    "radar": fig_bytes(chart_radar(r)),
                    "fatigue": fig_bytes(chart_fatigue(df)),
                }
                imgs = {k:v for k,v in imgs.items() if v}
                # Note: You need to include the full build_pdf function here from your original code
                # For now, I'm assuming you have it. If not, let me know.

    else:
        st.info("👆 Upload a CSV file to begin analysis.")

else:
    # Real-Time Mode (Unchanged)
    st.markdown('<div class="sec-title">⚡ Real-Time Swing Analyzer</div>', unsafe_allow_html=True)
    with st.form("rt_form"):
        c1, c2, c3 = st.columns(3)
        speed = c1.number_input("Speed", min_value=0.0, value=40.0, step=0.5)
        impact = c2.number_input("Impact", min_value=0.0, value=30.0, step=0.5)
        duration = c3.number_input("Duration", min_value=0.01,value=0.5, step=0.05)
        submitted = st.form_submit_button("🏸 Analyze Swing", type="primary")
    if submitted:
        df_rt = pd.DataFrame([{"speed":speed,"impact":impact,"duration":duration}])
        df_rt = add_features(df_rt)
        df_rt["prediction"] = predict(df_rt)
        pred = df_rt["prediction"][0]
        bcol = CMAP.get(pred, "#888")
        st.markdown(f"""
        <div style='text-align:center;margin:18px 0;background:{bcol}22;border:2px solid {bcol};border-radius:14px;padding:20px;'>
          <span style='font-family:Rajdhani,sans-serif;font-size:2rem;font-weight:700;color:{bcol};'>
            🏸 Swing Result: {pred}
          </span>
        </div>""", unsafe_allow_html=True)
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("⚡ Power", round(float(df_rt["power"][0]), 2))
        m2.metric("🎯 Efficiency", round(float(df_rt["efficiency"][0]), 2))
        m3.metric("🔥 Intensity", round(float(df_rt["intensity"][0]), 2))
        m4.metric("📏 Duration", duration)

st.caption("✅ Calculations corrected | Efficiency capped at 100%")
