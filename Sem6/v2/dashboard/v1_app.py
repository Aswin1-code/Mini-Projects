import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from datetime import datetime

# ── Optional model loading ──────────────────────────────────────────────────
try:
    import joblib, os
    SWING_MODEL_FILE  = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\performanceClassify ml train\swing_model.pkl"
    STROKE_MODEL_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\strokeClassifierModel\stroke classifier pkl\stroke_model.pkl"
    THRESHOLD_FILE    = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\thresholdFile.csv"
    PRO_DATASET_FILE  = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\matlab generate pro data\pro_benchmark_dataset.csv"

    _sp   = joblib.load(SWING_MODEL_FILE)
    SWING_MODEL    = _sp["model"]
    SWING_FEATURES = _sp["features"]

    _stp  = joblib.load(STROKE_MODEL_FILE)
    STROKE_MODEL    = _stp["model"]
    STROKE_FEATURES = _stp["features"]

    TH_DF = pd.read_csv(THRESHOLD_FILE) if os.path.exists(THRESHOLD_FILE) else None
    PRO_DF = pd.read_csv(PRO_DATASET_FILE) if os.path.exists(PRO_DATASET_FILE) else None

    MODELS_LOADED = True
except Exception:
    SWING_MODEL = STROKE_MODEL = TH_DF = PRO_DF = None
    SWING_FEATURES  = ["speed","impact","duration","power","efficiency"]
    STROKE_FEATURES = ["speed","impact","duration","power","efficiency",
                       "acc_mag","gyro_mag","peak_acc","peak_gyro","energy"]
    MODELS_LOADED = False

# ── PDF ─────────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors as rlc
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image as RLImage, Flowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="🏸 Badminton AI Pro",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🏸",
)

# ═══════════════════════════════════════════════════════════════════════════
# CSS  — identical dark-sport theme from Code 1
# ═══════════════════════════════════════════════════════════════════════════
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
.profile-card{background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.2);border-radius:14px;padding:20px;margin:8px 0;text-align:center;}
.pro-bar-player{background:linear-gradient(90deg,#00D4FF,#0088AA);height:18px;border-radius:4px;}
.pro-bar-pro   {background:linear-gradient(90deg,#FFD700,#FFA000);height:18px;border-radius:4px;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PLOTLY LAYOUT DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════
_L = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(255,255,255,0.03)",
    font=dict(family="Inter", color="#CBD5E1"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", showline=False),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", showline=False),
    margin=dict(l=20, r=20, t=44, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)
CMAP   = {"STRONG":"#FF4B4B","MEDIUM":"#FFD700","WEAK":"#00C853"}
SCMAP  = {"SMASH":"#FF4B4B","DROP":"#FFD700","CLEAR":"#00C853","DRIVE":"#00D4FF"}

# ═══════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["power","efficiency","intensity","swing_no","energy",
                "acc_mag","gyro_mag","peak_acc","peak_gyro"]:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)
    df["power"]      = df["speed"] * df["impact"]
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)
    df["intensity"]  = (df["speed"] + df["impact"] + df["power"]) / 3
    # stroke features
    df["acc_mag"]    = df["speed"]
    df["gyro_mag"]   = df["impact"]
    df["peak_acc"]   = df["speed"] * 1.2
    df["peak_gyro"]  = df["impact"] * 1.1
    df["energy"]     = df["power"] * df["duration"]
    df["swing_no"]   = range(1, len(df)+1)
    return df

# ═══════════════════════════════════════════════════════════════════════════
# PREDICTION
# ═══════════════════════════════════════════════════════════════════════════
def predict_swing(df: pd.DataFrame) -> pd.Series:
    if SWING_MODEL is not None:
        cols = [c for c in SWING_FEATURES if c in df.columns]
        return pd.Series(SWING_MODEL.predict(df[cols]), index=df.index)
    # rule-based fallback
    def rule(row):
        if row["power"] > 900 and row["efficiency"] > 50: return "STRONG"
        elif row["power"] > 500:                          return "MEDIUM"
        return "WEAK"
    return df.apply(rule, axis=1)

def predict_stroke(df: pd.DataFrame) -> pd.Series:
    if STROKE_MODEL is not None:
        cols = [c for c in STROKE_FEATURES if c in df.columns]
        return pd.Series(STROKE_MODEL.predict(df[cols]), index=df.index)
    # rule-based fallback
    def rule(row):
        if row["power"] > 1200:           return "SMASH"
        elif row["efficiency"] > 60:      return "DRIVE"
        elif row["speed"] < 25:           return "DROP"
        return "CLEAR"
    return df.apply(rule, axis=1)

def get_thresholds(df: pd.DataFrame):
    if TH_DF is not None:
        return TH_DF["weak_threshold"][0], TH_DF["strong_threshold"][0]
    return df["power"].quantile(0.25), df["power"].quantile(0.75)

def classify_final(df: pd.DataFrame) -> pd.Series:
    wt, st = get_thresholds(df)
    def rule(row):
        if row["power"] < wt:  return "WEAK"
        elif row["power"] < st: return "MEDIUM"
        return "STRONG"
    return df.apply(rule, axis=1)

# ═══════════════════════════════════════════════════════════════════════════
# ANALYTICS ENGINE  (Code 2 logic)
# ═══════════════════════════════════════════════════════════════════════════
def get_session_summary(df: pd.DataFrame) -> dict:
    return {
        "total_swings":  len(df),
        "weak_count":   (df["final_prediction"]=="WEAK").sum(),
        "medium_count": (df["final_prediction"]=="MEDIUM").sum(),
        "strong_count": (df["final_prediction"]=="STRONG").sum(),
        "avg_speed":    round(df["speed"].mean(),  2),
        "avg_impact":   round(df["impact"].mean(), 2),
        "avg_power":    round(df["power"].mean(),  2),
        "avg_eff":      round(df["efficiency"].mean(), 2),
        "std_power":    round(df["power"].std(),   2),
        "std_speed":    round(df["speed"].std(),   2),
        "best_swing":   df.loc[df["power"].idxmax()].copy(),
        "worst_swing":  df.loc[df["power"].idxmin()].copy(),
    }

def compute_consistency_scores(df: pd.DataFrame) -> dict:
    sc = {}
    sc["speed_cv"]  = round(df["speed"].std()  / (df["speed"].mean()  + 1e-6), 3)
    sc["impact_cv"] = round(df["impact"].std() / (df["impact"].mean() + 1e-6), 3)
    sc["power_cv"]  = round(df["power"].std()  / (df["power"].mean()  + 1e-6), 3)
    sc["consistency_score"] = round(100*(1-min(1,(sc["speed_cv"]+sc["impact_cv"]+sc["power_cv"])/3)),2)
    return sc

def compute_stability_score(df, summary, cs) -> float:
    ps = summary["avg_power"] / (summary["avg_power"] + summary["std_power"] + 1e-6)
    return round(min(10, (0.6*ps*10) + (0.4*cs["consistency_score"]/10)), 2)

def compute_fatigue(df: pd.DataFrame) -> dict:
    n = len(df)
    if n < 10:
        return {"fatigue_score":0,"speed_drop":0,"impact_drop":0,"power_drop":0,
                "status":"Insufficient data (need ≥10 swings)"}
    e, l = df.iloc[:int(n*0.4)], df.iloc[int(n*0.6):]
    def drop(a, b): return round(((a-b)/(a+1e-6))*100, 2)
    sd = drop(e["speed"].mean(),  l["speed"].mean())
    id_ = drop(e["impact"].mean(), l["impact"].mean())
    pd_ = drop(e["power"].mean(),  l["power"].mean())
    fs = round(np.mean([sd, id_, pd_]), 2)
    if   fs < 10: status = "✅ Fresh performance throughout session"
    elif fs < 25: status = "⚠️ Mild fatigue detected"
    else:         status = "🔴 High fatigue — significant performance drop"
    return {"fatigue_score":fs,"speed_drop":sd,"impact_drop":id_,
            "power_drop":pd_,"status":status}

def compare_with_pro(df: pd.DataFrame) -> dict:
    cols = ["speed","impact","duration","power","efficiency"]
    if PRO_DF is not None:
        pro = PRO_DF
    else:
        # synthetic pro benchmark
        pro = pd.DataFrame({
            "speed":    [55,58,52,60,57],
            "impact":   [45,48,43,50,46],
            "duration": [0.4,0.38,0.42,0.36,0.39],
            "power":    [2475,2784,2236,3000,2622],
            "efficiency":[112,126,102,138,117],
        })
    pa = df[cols].mean(); pra = pro[cols].mean()
    out = {}
    for c in cols:
        p = pa[c]; pr = pra[c]
        gap = (pr-p) if c=="duration" else (p-pr)
        out[f"player_avg_{c}"] = round(p,2)
        out[f"pro_avg_{c}"]    = round(pr,2)
        out[f"gap_{c}"]        = round(gap,2)
    return out

def generate_gap_analysis(comp: dict):
    a = []
    if comp["gap_speed"]  < -5:  a.append(("Speed",  "Major deficit in swing acceleration"))
    elif comp["gap_speed"] < -2: a.append(("Speed",  "Moderate speed improvement needed"))
    else:                         a.append(("Speed",  "Close to pro level ✅"))
    if comp["gap_impact"] < -8:  a.append(("Impact", "Weak shuttle contact force"))
    elif comp["gap_impact"]< -3: a.append(("Impact", "Timing needs refinement"))
    else:                         a.append(("Impact", "Good striking control ✅"))
    if comp["gap_power"]  < -700: a.append(("Power", "Very low explosive strength"))
    elif comp["gap_power"]< -300: a.append(("Power", "Power generation needs work"))
    else:                          a.append(("Power", "Strong power output ✅"))
    tg = comp["gap_power"]
    level = "Near Pro Level 🏆" if tg>-200 else ("Intermediate Player" if tg>-600 else "Needs Major Improvement")
    return a, level

def generate_ai_coaching(summary, comp) -> list:
    s = []
    if comp["gap_speed"]  < -3:  s.append(("warn","🚀 Swing Speed","Increase racket swing speed using forearm acceleration drills."))
    if comp["gap_impact"] < -5:  s.append(("warn","🎯 Contact Timing","Improve shuttle contact timing with shadow practice."))
    if comp["gap_power"]  < -500:s.append(("bad", "💥 Explosive Power","Focus on explosive smash power with plyometric training."))
    if summary["std_power"] > 400: s.append(("warn","📊 Consistency","Improve consistency — drill repeatable swing mechanics."))
    if comp["gap_speed"]  >= -3 and comp["gap_impact"] >= -5 and comp["gap_power"] >= -500:
        s.append(("good","🏆 Elite Performance","Performance is close to pro level — maintain conditioning!"))
    s.append(("info","🏁 General","Prioritise timing over raw speed in every drill session."))
    s.append(("info","📹 Tracking","Record and compare swing metrics weekly to monitor progress."))
    return s

def classify_player_type(df, summary) -> dict:
    if "stroke_type" not in df.columns:
        return {"player_type":"⚖ All-Rounder","explanation":"Stroke data not available.",
                "smash_pct":25,"clear_pct":25,"drop_pct":25,"drive_pct":25}
    dist = df["stroke_type"].value_counts(normalize=True)*100
    smash = dist.get("SMASH",0); drop = dist.get("DROP",0)
    clear = dist.get("CLEAR",0); drive = dist.get("DRIVE",0)
    atk = (smash*0.6) + (summary["avg_power"]/100)
    dfn = (clear*0.6) + (1/(summary["avg_power"]+1e-6))*1000
    if atk > dfn and smash > 40:
        pt,ex = "🔥 Attacker","You rely heavily on smashes and high-power shots."
    elif dfn > atk and clear > 35:
        pt,ex = "🛡️ Defensive Player","You focus on rallies, clears, and controlled gameplay."
    elif 100-abs(smash-clear)-abs(drop-drive) > 60:
        pt,ex = "⚖️ All-Rounder","Balanced mix of attacking and defensive strokes."
    else:
        pt,ex = "🎯 Mixed Style","No dominant pattern detected clearly."
    return {"player_type":pt,"explanation":ex,
            "smash_pct":round(smash,2),"clear_pct":round(clear,2),
            "drop_pct":round(drop,2),"drive_pct":round(drive,2)}

def technique_feedback(df, summary) -> list:
    fb = []
    ratio = summary["avg_speed"]/(summary["avg_impact"]+1e-6)
    if   ratio > 1.4: fb.append(("warn","⚠️ Timing Issue","High swing speed but low impact — late shuttle contact likely."))
    elif ratio < 0.8: fb.append(("warn","⚠️ Timing Issue","Strong impact but low speed — early contact / poor acceleration."))
    else:             fb.append(("good","✅ Timing","Speed-to-impact ratio is balanced."))
    if df["speed"].std() > df["speed"].mean()*0.35:
        fb.append(("warn","📉 Speed Inconsistency","Swing speed varies too much between shots."))
    else:
        fb.append(("good","✅ Speed Stability","Stable swing speed across the session."))
    if summary["std_power"] > summary["avg_power"]*0.35:
        fb.append(("bad","📉 Power Inconsistency","Unstable shot strength — drill consistent follow-through."))
    else:
        fb.append(("good","✅ Power Stability","Consistent power output — good muscular control."))
    return fb

# ═══════════════════════════════════════════════════════════════════════════
# CHART BUILDERS
# ═══════════════════════════════════════════════════════════════════════════
def chart_trend(df):
    fig = make_subplots(rows=3,cols=1,shared_xaxes=True,
                        subplot_titles=("Speed","Power","Efficiency"),
                        vertical_spacing=0.08)
    kw = dict(mode="lines+markers",marker=dict(size=5))
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["speed"],   name="Speed",     line=dict(color="#00D4FF"),**kw),row=1,col=1)
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["power"],   name="Power",     line=dict(color="#FFD700"),**kw),row=2,col=1)
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["efficiency"],name="Efficiency",line=dict(color="#00C853"),**kw),row=3,col=1)
    fig.update_layout(**_L,height=520,showlegend=False,title_text="📈 Performance Trends Over Swings")
    return fig

def chart_rolling(df):
    win = max(3, len(df)//8)
    fig = go.Figure()
    for col,color,name in [("speed","#00D4FF","Speed"),("power","#FFD700","Power"),("efficiency","#00C853","Efficiency")]:
        fig.add_trace(go.Scatter(x=df["swing_no"],y=df[col].rolling(win,min_periods=1).mean(),
                                 name=f"{name} (rolling avg)",line=dict(color=color,width=2.5)))
    fig.update_layout(**_L,height=360,title_text=f"📊 Rolling Average (window={win})")
    return fig

def chart_stroke_pie(df):
    if "stroke_type" not in df.columns:
        return go.Figure()
    cnt = df["stroke_type"].value_counts().reset_index()
    cnt.columns = ["Stroke","Count"]
    fig = px.pie(cnt,names="Stroke",values="Count",color="Stroke",
                 color_discrete_map=SCMAP,title="🏸 Stroke Type Distribution",hole=0.45)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",font=dict(family="Inter",color="#CBD5E1"),
                      height=340,margin=dict(l=20,r=20,t=44,b=20),legend=dict(bgcolor="rgba(0,0,0,0)"))
    return fig

def chart_radar(summary, cs, fatigue):
    cats = ["Power","Efficiency","Consistency","Speed","Stability"]
    vals = [
        min(100, summary["avg_power"]/20),
        min(100, summary["avg_eff"]),
        cs["consistency_score"],
        min(100, summary["avg_speed"]*2),
        min(100, max(0, 100 - fatigue["fatigue_score"]*2)),
    ]
    fig = go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],
        fill="toself",line=dict(color="#00D4FF",width=2),fillcolor="rgba(0,212,255,0.15)"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True,range=[0,100],gridcolor="rgba(255,255,255,0.1)"),
                   angularaxis=dict(gridcolor="rgba(255,255,255,0.1)"),bgcolor="rgba(0,0,0,0)"),
        paper_bgcolor="rgba(0,0,0,0)",font=dict(family="Inter",color="#CBD5E1"),
        height=360,margin=dict(l=40,r=40,t=60,b=40),title_text="🕸️ Performance Radar")
    return fig

def chart_histogram(df):
    fig = make_subplots(rows=1,cols=2,subplot_titles=("Power Distribution","Efficiency Distribution"))
    fig.add_trace(go.Histogram(x=df["power"],nbinsx=14,name="Power",marker_color="#FFD700",opacity=0.85),row=1,col=1)
    fig.add_trace(go.Histogram(x=df["efficiency"],nbinsx=14,name="Efficiency",marker_color="#00C853",opacity=0.85),row=1,col=2)
    fig.update_layout(**_L,height=360,showlegend=False,title_text="📊 Distributions")
    return fig

def chart_box(df):
    fig = go.Figure()
    for col,color in [("speed","#00D4FF"),("power","#FFD700"),("efficiency","#00C853")]:
        fig.add_trace(go.Box(y=df[col],name=col.title(),marker_color=color,boxmean=True))
    fig.update_layout(**_L,height=360,title_text="📦 Box Plot — Spread & Outliers")
    return fig

def chart_scatter(df):
    color_col = "stroke_type" if "stroke_type" in df.columns else "final_prediction"
    cmap = SCMAP if color_col == "stroke_type" else CMAP
    fig = px.scatter(df,x="speed",y="impact",color=color_col,size="power",
                     hover_data=["efficiency","swing_no"],color_discrete_map=cmap,
                     title="🔵 Speed vs Impact (bubble = power)")
    fig.update_layout(**_L,height=400)
    return fig

def chart_category(df):
    col = "final_prediction"
    cnt = df[col].value_counts().reset_index(); cnt.columns = ["Category","Count"]
    fig = px.bar(cnt,x="Category",y="Count",color="Category",
                 color_discrete_map=CMAP,text="Count",title="🏸 Swing Category Breakdown")
    fig.update_traces(textposition="outside")
    fig.update_layout(**_L,height=340,showlegend=False)
    return fig

def chart_pro_comparison(comp):
    metrics = ["speed","impact","power"]
    labels  = ["Speed","Impact","Power"]
    player  = [comp[f"player_avg_{m}"] for m in metrics]
    pro     = [comp[f"pro_avg_{m}"] for m in metrics]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="You",  x=labels, y=player, marker_color="#00D4FF",opacity=0.9))
    fig.add_trace(go.Bar(name="Pro",  x=labels, y=pro,    marker_color="#FFD700",opacity=0.9))
    fig.update_layout(**_L,height=360,barmode="group",title_text="🏆 Player vs Pro Benchmark")
    return fig

def chart_pro_heatmap(comp):
    metrics = ["speed","impact","power","efficiency","duration"]
    gaps    = [comp[f"gap_{m}"] for m in metrics]
    fig = go.Figure(go.Bar(x=metrics,y=gaps,
        marker_color=["#00C853" if g>=0 else "#FF4B4B" for g in gaps],
        text=[f"{g:+.2f}" for g in gaps],textposition="outside"))
    fig.add_hline(y=0,line_color="#888",line_dash="dash")
    fig.update_layout(**_L,height=340,title_text="📊 Performance Gap (You − Pro)  [positive = ahead]")
    return fig

def chart_fatigue_line(df):
    win = max(3, len(df)//8)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["speed"].rolling(win,min_periods=1).mean(),
        name="Speed (rolling)",line=dict(color="#00D4FF",width=2)))
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["power"].rolling(win,min_periods=1).mean(),
        name="Power (rolling)",line=dict(color="#FFD700",width=2)))
    fig.update_layout(**_L,height=340,title_text="🔋 Fatigue — Performance Decay Over Session")
    return fig

def chart_fatigue_box(df):
    n = len(df); mid = n//2
    fig = go.Figure()
    fig.add_trace(go.Box(y=df["speed"].iloc[:mid].values,name="First Half", marker_color="#00D4FF",boxmean=True))
    fig.add_trace(go.Box(y=df["speed"].iloc[mid:].values,name="Second Half",marker_color="#FF4B4B",boxmean=True))
    fig.update_layout(**_L,height=340,title_text="🔋 Fatigue Analysis — Speed by Half")
    return fig

def chart_stroke_bar(df):
    if "stroke_type" not in df.columns:
        return go.Figure()
    cnt = df["stroke_type"].value_counts().reset_index(); cnt.columns=["Stroke","Count"]
    fig = px.bar(cnt,x="Stroke",y="Count",color="Stroke",color_discrete_map=SCMAP,
                 text="Count",title="🏸 Stroke Distribution")
    fig.update_traces(textposition="outside")
    fig.update_layout(**_L,height=340,showlegend=False)
    return fig

def chart_heatmap(df):
    rows = min(len(df),50)
    d    = df.tail(rows)
    fig  = go.Figure(go.Heatmap(z=d["power"].values.reshape(1,-1),x=d["swing_no"].values,
        colorscale=[[0,"#00C853"],[0.5,"#FFD700"],[1,"#FF4B4B"]],colorbar=dict(title="Power")))
    fig.update_layout(**_L,height=180,title_text="🌡️ Power Heat Map (last swings)")
    return fig

def fig_bytes(fig) -> bytes:
    try: return fig.to_image(format="png",width=900,height=440,scale=1.8)
    except: return b""

# ═══════════════════════════════════════════════════════════════════════════
# PDF BUILDER — dark sport theme
# ═══════════════════════════════════════════════════════════════════════════
PDF_BG=rlc.HexColor("#0D1117"); PDF_CARD=rlc.HexColor("#161B22")
PDF_CARD_ALT=rlc.HexColor("#1C2128"); PDF_HEADER=rlc.HexColor("#00D4FF")
PDF_HEADER_BG=rlc.HexColor("#003344"); PDF_TEXT=rlc.HexColor("#E6EDF3")
PDF_SUBTEXT=rlc.HexColor("#8B949E"); PDF_GOLD=rlc.HexColor("#FFD700")
PDF_GREEN=rlc.HexColor("#00C853"); PDF_ORANGE=rlc.HexColor("#FF9800")
PDF_RED=rlc.HexColor("#FF4B4B"); PDF_BORDER=rlc.HexColor("#30363D")
INSIGHT_COLORS={"good":(rlc.HexColor("#0D2818"),PDF_GREEN),
                "warn":(rlc.HexColor("#2D1B00"),PDF_ORANGE),
                "bad": (rlc.HexColor("#2D0D0D"),PDF_RED),
                "info":(rlc.HexColor("#001A2D"),PDF_HEADER)}

def _dark_tbl_style(header_bg=PDF_HEADER_BG,even=PDF_CARD,odd=PDF_CARD_ALT):
    return TableStyle([
        ("BACKGROUND",(0,0),(-1,0),header_bg),("TEXTCOLOR",(0,0),(-1,0),PDF_HEADER),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[even,odd]),("TEXTCOLOR",(0,1),(-1,-1),PDF_TEXT),
        ("FONTSIZE",(0,1),(-1,-1),8.5),("GRID",(0,0),(-1,-1),0.4,PDF_BORDER),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ])

class DarkBackground(Flowable):
    def draw(self):
        c=self.canv; pw,ph=A4; c.saveState(); c.setFillColor(PDF_BG)
        c.rect(0,0,pw,ph,fill=1,stroke=0); c.restoreState()
    def wrap(self,*a): return (0,0)

def build_pdf(df,summary,comp,gap_analysis,level,cs,stability,fatigue,player_profile,insights,imgs) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf,pagesize=A4,leftMargin=1.8*cm,rightMargin=1.8*cm,
                             topMargin=2*cm,bottomMargin=2*cm)
    def P(name,**kw):
        s=ParagraphStyle(name)
        for k,v in kw.items(): setattr(s,k,v)
        return s
    TITLE_S=P("ts",fontSize=22,textColor=PDF_HEADER,alignment=TA_CENTER,fontName="Helvetica-Bold",spaceAfter=4)
    SUB_S  =P("ss",fontSize=10,textColor=PDF_SUBTEXT,alignment=TA_CENTER,spaceAfter=10)
    H1_S   =P("h1s",fontSize=13,textColor=PDF_HEADER,fontName="Helvetica-Bold",spaceBefore=14,spaceAfter=6)
    H2_S   =P("h2s",fontSize=11,textColor=PDF_GOLD,fontName="Helvetica-Bold",spaceBefore=8,spaceAfter=4)
    FOOT_S =P("fs",fontSize=8,textColor=PDF_SUBTEXT,alignment=TA_CENTER)

    story=[]
    story.append(DarkBackground())
    story.append(Spacer(1,0.5*cm))
    story.append(Paragraph("SMART BADMINTON AI PERFORMANCE REPORT",TITLE_S))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y  •  %H:%M')}",SUB_S))
    story.append(HRFlowable(width="100%",thickness=2,color=PDF_HEADER,spaceAfter=16))

    # KPI
    story.append(Paragraph("SESSION KPI SUMMARY",H1_S))
    kpi=[["Metric","Value","Metric","Value"],
         ["Total Swings",str(summary["total_swings"]),"Avg Power",str(summary["avg_power"])],
         ["Avg Speed",str(summary["avg_speed"]),"Avg Impact",str(summary["avg_impact"])],
         ["Consistency",f"{cs['consistency_score']}%","Stability",f"{stability}/10"],
         ["Strong %",f"{round(summary['strong_count']/summary['total_swings']*100,1)}%",
          "Fatigue Score",f"{fatigue['fatigue_score']}%"],
         ["Player Level",level,"Player Type",player_profile["player_type"].replace("🔥","").replace("🛡️","").replace("⚖️","").replace("🎯","").strip()]]
    kt=Table(kpi,colWidths=[4*cm,2.8*cm,4*cm,2.8*cm]); kt.setStyle(_dark_tbl_style())
    story.append(kt); story.append(Spacer(1,0.4*cm))

    # Pro comparison
    story.append(Paragraph("PRO COMPARISON",H1_S))
    pro_d=[["Metric","Your Avg","Pro Avg","Gap"]]+[
        [m.title(),str(comp[f"player_avg_{m}"]),str(comp[f"pro_avg_{m}"]),str(comp[f"gap_{m}"])]
        for m in ["speed","impact","power","efficiency"]]
    pt=Table(pro_d,colWidths=[3.4*cm,3.4*cm,3.4*cm,3.4*cm]); pt.setStyle(_dark_tbl_style())
    story.append(pt); story.append(Spacer(1,0.4*cm))

    # Charts
    story.append(Paragraph("PERFORMANCE CHARTS",H1_S))
    for key,label in [("trend","Trends"),("scatter","Speed vs Impact"),
                       ("pro","Pro Comparison"),("radar","Performance Radar"),("fatigue","Fatigue")]:
        if imgs.get(key):
            story.append(Paragraph(label,H2_S))
            story.append(RLImage(io.BytesIO(imgs[key]),width=14*cm,height=7*cm))
            story.append(Spacer(1,0.3*cm))

    story.append(PageBreak()); story.append(DarkBackground())

    # AI Coach
    story.append(Paragraph("AI COACH INSIGHTS",H1_S))
    for t,title,desc in insights:
        bg_col,fg_col=INSIGHT_COLORS.get(t,(PDF_CARD,PDF_HEADER))
        tp=Paragraph(title,P(f"ip_{id(title)}",fontSize=9.5,textColor=fg_col,fontName="Helvetica-Bold",leading=14))
        dp=Paragraph(desc, P(f"dp_{id(desc)}",fontSize=8.8,textColor=PDF_TEXT,leading=13))
        it=Table([[tp,dp]],colWidths=[4.2*cm,9.4*cm])
        it.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg_col),("BOX",(0,0),(-1,-1),0.8,fg_col),
            ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
            ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        story.append(it); story.append(Spacer(1,0.2*cm))

    # Full data
    story.append(PageBreak()); story.append(DarkBackground())
    story.append(Paragraph("FULL SESSION DATA",H1_S))
    cols=[c for c in ["swing_no","speed","impact","duration","power","efficiency",
                        "stroke_type","final_prediction"] if c in df.columns]
    header=[c.replace("_"," ").title() for c in cols]
    rows=[header]+[[str(int(row[c])) if c=="swing_no"
                    else str(round(float(row[c]),2)) if isinstance(row[c],(float,int,np.floating,np.integer))
                    else str(row[c]) for c in cols] for _,row in df.iterrows()]
    cw=[13.6*cm/len(cols)]*len(cols)
    dt=Table(rows,colWidths=cw,repeatRows=1); dt.setStyle(_dark_tbl_style())
    story.append(dt)

    story.append(Spacer(1,0.8*cm))
    story.append(HRFlowable(width="100%",thickness=1,color=PDF_BORDER))
    story.append(Paragraph("Generated by Smart Badminton AI Pro  •  AI-powered swing analysis system",FOOT_S))
    doc.build(story)
    return buf.getvalue()

# ═══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════
for k,v in [("file_id",None),("df",None),("summary",None),("comp",None),("gap_analysis",None),
             ("level",None),("cs",None),("stability",None),("fatigue",None),("player_profile",None),
             ("insights",None),("tech_fb",None),("pdf_ready",False),("pdf_bytes",None)]:
    if k not in st.session_state: st.session_state[k]=v

def reset_session():
    for k in ["df","summary","comp","gap_analysis","level","cs","stability",
               "fatigue","player_profile","insights","tech_fb","pdf_ready","pdf_bytes"]:
        st.session_state[k]=None if k!="pdf_ready" else False

# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🏸 Smart Badminton AI Pro")
    st.markdown("---")

    mode = st.selectbox("Select Mode",["📊 Simulation Mode","⚡ Real-Time Mode"])
    st.markdown("---")

    if st.session_state.df is not None:
        df_all = st.session_state.df
        st.markdown("**🔍 Session Filters**")

        if "stroke_type" in df_all.columns:
            stroke_opts = ["All"] + list(df_all["stroke_type"].unique())
            sel_stroke  = st.selectbox("Stroke Type", stroke_opts)
        else:
            sel_stroke = "All"

        swing_range = st.slider("Swing Range",1,len(df_all),(1,len(df_all)))

        metrics_shown = st.multiselect(
            "Metrics to display",["Speed","Power","Efficiency","Impact"],
            default=["Speed","Power","Efficiency"])
    else:
        sel_stroke   = "All"
        swing_range  = (1, 1)
        metrics_shown = ["Speed","Power","Efficiency"]

    st.markdown("---")
    st.caption("AI-powered swing analysis · fatigue detection · "
               "consistency tracking · pro benchmarking · dark PDF export")
    if not MODELS_LOADED:
        st.warning("⚠️ ML models not found.\nUsing rule-based fallback.", icon="🤖")

# ═══════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style='text-align:center;padding:20px 0 10px'>
  <h1 style='font-family:Rajdhani,sans-serif;font-size:2.5rem;margin:0;
             background:linear-gradient(90deg,#00D4FF,#FFD700);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
    🏸 Smart Badminton AI Performance System
  </h1>
  <p style='color:#8899AA;font-size:0.93rem;margin-top:4px;'>
    AI-powered swing analysis · consistency tracking · pro benchmarking · coaching insights · PDF export
  </p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# ════════════════════  SIMULATION MODE  ════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
if "Simulation" in mode:

    st.markdown('<div class="sec-title">📊 Performance Analytics Dashboard</div>', unsafe_allow_html=True)
    file = st.file_uploader("Upload Session CSV  (columns: speed, impact, duration)", type=["csv"])

    # ── New file detection ───────────────────────────────────────────────
    if file is not None:
        fid = (file.name, file.size)
        if st.session_state.file_id != fid:
            reset_session(); st.session_state.file_id = fid
            df_raw = pd.read_csv(file)
            for col in ["speed","impact","duration"]:
                if col in df_raw.columns:
                    df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")
            df_raw.dropna(subset=["speed","impact","duration"], inplace=True)

            df = add_features(df_raw)
            df["final_prediction"] = classify_final(df)
            if "stroke_type" not in df.columns:
                df["stroke_type"] = predict_stroke(df)

            summary       = get_session_summary(df)
            cs            = compute_consistency_scores(df)
            stability     = compute_stability_score(df, summary, cs)
            fatigue       = compute_fatigue(df)
            comp          = compare_with_pro(df)
            gap_analysis, level = generate_gap_analysis(comp)
            insights      = generate_ai_coaching(summary, comp)
            player_profile= classify_player_type(df, summary)
            tech_fb       = technique_feedback(df, summary)

            for k,v in [("df",df),("summary",summary),("cs",cs),("stability",stability),
                         ("fatigue",fatigue),("comp",comp),("gap_analysis",gap_analysis),
                         ("level",level),("insights",insights),("player_profile",player_profile),
                         ("tech_fb",tech_fb)]:
                st.session_state[k]=v

    elif file is None and st.session_state.file_id is not None:
        reset_session(); st.session_state.file_id=None

    # ── Dashboard ────────────────────────────────────────────────────────
    if st.session_state.df is not None:
        df      = st.session_state.df.copy()
        summary = st.session_state.summary
        cs      = st.session_state.cs
        stability= st.session_state.stability
        fatigue = st.session_state.fatigue
        comp    = st.session_state.comp
        gap_analysis = st.session_state.gap_analysis
        level   = st.session_state.level
        insights= st.session_state.insights
        pp      = st.session_state.player_profile
        tech_fb = st.session_state.tech_fb

        # Apply sidebar filters
        df = df.iloc[swing_range[0]-1:swing_range[1]]
        if sel_stroke != "All" and "stroke_type" in df.columns:
            df = df[df["stroke_type"]==sel_stroke]
        if df.empty:
            st.warning("No data after applying filters.")
            st.stop()

        # ── KPI ROW ──────────────────────────────────────────────────────
        k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
        n = summary["total_swings"]
        k1.metric("🏸 Total Swings",  summary["total_swings"])
        k2.metric("⚡ Avg Speed",      summary["avg_speed"])
        k3.metric("💥 Avg Impact",     summary["avg_impact"])
        k4.metric("🔥 Avg Power",      summary["avg_power"])
        k5.metric("🎯 Efficiency",     summary["avg_eff"])
        k6.metric("🏆 Consistency",    f"{cs['consistency_score']}%")
        k7.metric("📊 Stability",      f"{stability}/10")

        st.divider()

        # ── BEST / WORST ─────────────────────────────────────────────────
        hc1,hc2 = st.columns(2)
        with hc1:
            bs = summary["best_swing"]
            st.markdown(f"""<div class="hl-best">
              <b>🔥 Best Swing — #{int(bs.get('swing_no',0))}</b><br>
              Speed: <b>{round(float(bs['speed']),2)}</b> &nbsp;|&nbsp;
              Impact: <b>{round(float(bs['impact']),2)}</b> &nbsp;|&nbsp;
              Power: <b>{round(float(bs['power']),2)}</b>
            </div>""", unsafe_allow_html=True)
        with hc2:
            ws = summary["worst_swing"]
            st.markdown(f"""<div class="hl-worst">
              <b>⚠️ Worst Swing — #{int(ws.get('swing_no',0))}</b><br>
              Speed: <b>{round(float(ws['speed']),2)}</b> &nbsp;|&nbsp;
              Impact: <b>{round(float(ws['impact']),2)}</b> &nbsp;|&nbsp;
              Power: <b>{round(float(ws['power']),2)}</b>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # ═══════════════════════════════════════════════════════════════
        # TABS
        # ═══════════════════════════════════════════════════════════════
        tab1,tab2,tab3,tab4,tab5,tab6,tab7 = st.tabs([
            "📈 Overview","📊 Distributions","🏆 Pro Comparison",
            "🧠 AI Coach","🧬 Player Profile","🔋 Fatigue & Consistency","📋 Data"
        ])

        # ── TAB 1: OVERVIEW ─────────────────────────────────────────────
        with tab1:
            st.plotly_chart(chart_trend(df),         use_container_width=True)
            st.plotly_chart(chart_rolling(df),        use_container_width=True)
            c11,c12 = st.columns(2)
            with c11: st.plotly_chart(chart_stroke_pie(df),          use_container_width=True)
            with c12: st.plotly_chart(chart_radar(summary,cs,fatigue),use_container_width=True)
            st.plotly_chart(chart_heatmap(df), use_container_width=True)

        # ── TAB 2: DISTRIBUTIONS ────────────────────────────────────────
        with tab2:
            st.plotly_chart(chart_histogram(df), use_container_width=True)
            c21,c22 = st.columns(2)
            with c21: st.plotly_chart(chart_category(df), use_container_width=True)
            with c22: st.plotly_chart(chart_scatter(df),  use_container_width=True)
            st.plotly_chart(chart_box(df), use_container_width=True)

        # ── TAB 3: PRO COMPARISON ────────────────────────────────────────
        with tab3:
            st.markdown('<div class="sec-title">🏆 Player vs Pro Benchmark</div>', unsafe_allow_html=True)

            pc1,pc2,pc3 = st.columns(3)
            for col,label,metric_key,sign in [
                (pc1,"Speed",  "speed",  comp["gap_speed"]),
                (pc2,"Impact", "impact", comp["gap_impact"]),
                (pc3,"Power",  "power",  comp["gap_power"]),
            ]:
                delta = f"{sign:+.2f} vs Pro"
                col.metric(f"📊 {label}", comp[f"player_avg_{metric_key}"], delta)

            st.plotly_chart(chart_pro_comparison(comp), use_container_width=True)
            st.plotly_chart(chart_pro_heatmap(comp),    use_container_width=True)

            st.markdown("---")
            st.markdown('<div class="sec-title">📋 Gap Analysis</div>', unsafe_allow_html=True)
            for feat, msg in gap_analysis:
                icon = "card-good" if "✅" in msg else "card-warn" if "needed" in msg.lower() else "card-bad"
                st.markdown(f'<div class="{icon}"><b>{feat}</b> — {msg}</div>', unsafe_allow_html=True)

            st.markdown(f"""
            <div class="card-info" style="margin-top:12px;text-align:center;">
              <span style="font-family:Rajdhani,sans-serif;font-size:1.4rem;font-weight:700;color:#00D4FF;">
                🏆 Player Level: {level}
              </span>
            </div>""", unsafe_allow_html=True)

        # ── TAB 4: AI COACH ──────────────────────────────────────────────
        with tab4:
            gc1,gc2,gc3 = st.columns(3)
            gc1.metric("⚖️ Consistency",    f"{cs['consistency_score']}%")
            gc2.metric("📊 Stability",       f"{stability}/10")
            gc3.metric("🎯 Avg Efficiency",  summary["avg_eff"])

            st.markdown("---")
            st.markdown('<div class="sec-title">💡 AI Coaching Insights</div>', unsafe_allow_html=True)
            for t,title,desc in insights:
                css = {"good":"card-good","warn":"card-warn","bad":"card-bad","info":"card-info"}.get(t,"card-info")
                st.markdown(f'<div class="{css}"><b>{title}</b><br>'
                            f'<span style="font-size:0.88rem;color:#CBD5E1;">{desc}</span></div>',
                            unsafe_allow_html=True)

            st.markdown("---")
            st.markdown('<div class="sec-title">🔧 Technique Feedback</div>', unsafe_allow_html=True)
            for t,title,desc in tech_fb:
                css = {"good":"card-good","warn":"card-warn","bad":"card-bad","info":"card-info"}.get(t,"card-info")
                st.markdown(f'<div class="{css}"><b>{title}</b><br>'
                            f'<span style="font-size:0.88rem;color:#CBD5E1;">{desc}</span></div>',
                            unsafe_allow_html=True)

        # ── TAB 5: PLAYER PROFILE ────────────────────────────────────────
        with tab5:
            st.markdown('<div class="sec-title">🧬 Player Profile Classification</div>', unsafe_allow_html=True)

            st.markdown(f"""
            <div class="profile-card">
              <div style="font-family:Rajdhani,sans-serif;font-size:2.2rem;font-weight:700;color:#00D4FF;">
                {pp['player_type']}
              </div>
              <p style="color:#CBD5E1;margin-top:8px;">{pp['explanation']}</p>
            </div>""", unsafe_allow_html=True)

            st.markdown("---")
            # Stroke %
            p1,p2,p3,p4 = st.columns(4)
            p1.metric("💥 Smash",  f"{pp['smash_pct']}%")
            p2.metric("🍃 Drop",   f"{pp['drop_pct']}%")
            p3.metric("🧹 Clear",  f"{pp['clear_pct']}%")
            p4.metric("⚡ Drive",  f"{pp['drive_pct']}%")

            c51,c52 = st.columns(2)
            with c51: st.plotly_chart(chart_stroke_bar(df),  use_container_width=True)
            with c52: st.plotly_chart(chart_stroke_pie(df),  use_container_width=True)

            # Style score bars
            st.markdown("---")
            st.markdown('<div class="sec-title">📊 Style Score</div>', unsafe_allow_html=True)
            atk_score = min(100, pp["smash_pct"]*1.5)
            dfn_score = min(100, pp["clear_pct"]*1.5)
            bal_score = min(100, max(0, 100 - abs(pp["smash_pct"]-pp["clear_pct"])))

            for label,score,color in [("⚔️ Attack",atk_score,"#FF4B4B"),
                                        ("🛡️ Defense",dfn_score,"#00C853"),
                                        ("⚖️ Balance",bal_score,"#00D4FF")]:
                st.markdown(f"**{label}** — {score:.0f}%")
                st.progress(int(score)/100)

        # ── TAB 6: FATIGUE & CONSISTENCY ────────────────────────────────
        with tab6:
            st.markdown('<div class="sec-title">🔋 Fatigue Analysis</div>', unsafe_allow_html=True)

            fa1,fa2,fa3,fa4 = st.columns(4)
            fa1.metric("🫀 Fatigue Score", f"{fatigue['fatigue_score']}%")
            fa2.metric("⚡ Speed Drop",    f"{fatigue['speed_drop']}%")
            fa3.metric("💥 Impact Drop",   f"{fatigue['impact_drop']}%")
            fa4.metric("🔥 Power Drop",    f"{fatigue['power_drop']}%")

            fstatus_css = "card-good" if fatigue["fatigue_score"]<10 else ("card-warn" if fatigue["fatigue_score"]<25 else "card-bad")
            st.markdown(f'<div class="{fstatus_css}"><b>{fatigue["status"]}</b></div>', unsafe_allow_html=True)

            c61,c62 = st.columns(2)
            with c61: st.plotly_chart(chart_fatigue_line(df), use_container_width=True)
            with c62: st.plotly_chart(chart_fatigue_box(df),  use_container_width=True)

            st.markdown("---")
            st.markdown('<div class="sec-title">📊 Consistency Engine</div>', unsafe_allow_html=True)

            cc1,cc2,cc3,cc4 = st.columns(4)
            cc1.metric("📉 Speed CV",      cs["speed_cv"])
            cc2.metric("📉 Impact CV",     cs["impact_cv"])
            cc3.metric("📉 Power CV",      cs["power_cv"])
            cc4.metric("✅ Consistency",   f"{cs['consistency_score']}/100")

            st.markdown(f"**Consistency Score: {cs['consistency_score']}%**")
            st.progress(int(cs["consistency_score"])/100)
            st.markdown(f"**Stability Score: {stability}/10**")
            st.progress(int(stability*10)/100)

        # ── TAB 7: RAW DATA ──────────────────────────────────────────────
        with tab7:
            display_cols = [c for c in ["swing_no","speed","impact","duration","power",
                                         "efficiency","intensity","stroke_type","final_prediction"]
                            if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True)
            st.download_button("⬇️ Download Filtered CSV",
                               df[display_cols].to_csv(index=False).encode(),
                               "session_data.csv","text/csv")

        st.divider()

        # ── PDF EXPORT ───────────────────────────────────────────────────
        st.markdown('<div class="sec-title">📄 Export Full Report as PDF</div>', unsafe_allow_html=True)
        st.caption("Generates a dark-themed multi-page PDF with KPIs, pro comparison, "
                   "AI insights, player profile, charts, and full session data table.")

        if st.button("🖨️ Generate PDF Report", type="primary"):
            with st.spinner("Rendering charts and compiling dark-theme PDF…"):
                _df = st.session_state.df
                imgs = {
                    "trend":   fig_bytes(chart_trend(_df)),
                    "scatter": fig_bytes(chart_scatter(_df)),
                    "pro":     fig_bytes(chart_pro_comparison(comp)),
                    "radar":   fig_bytes(chart_radar(summary,cs,fatigue)),
                    "fatigue": fig_bytes(chart_fatigue_box(_df)),
                }
                imgs = {k:v for k,v in imgs.items() if v}
                st.session_state.pdf_bytes = build_pdf(
                    _df, summary, comp, gap_analysis, level,
                    cs, stability, fatigue, pp, insights, imgs)
                st.session_state.pdf_ready = True

        if st.session_state.pdf_ready and st.session_state.pdf_bytes:
            fname = f"badminton_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            st.download_button(
                label="📥 Download PDF Report",
                data=st.session_state.pdf_bytes,
                file_name=fname,
                mime="application/pdf",
            )
            st.success("✅ PDF ready — click above to download.")

    else:
        st.info("👆 Upload a CSV file to begin analysis. Required columns: **speed, impact, duration**")

# ═══════════════════════════════════════════════════════════════════════════
# ════════════════════  REAL-TIME MODE  ═════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
else:
    st.markdown('<div class="sec-title">⚡ Real-Time Swing Analyzer</div>', unsafe_allow_html=True)

    with st.form("rt_form"):
        c1,c2,c3 = st.columns(3)
        speed    = c1.number_input("Speed",    min_value=0.0, value=40.0, step=0.5)
        impact   = c2.number_input("Impact",   min_value=0.0, value=30.0, step=0.5)
        duration = c3.number_input("Duration", min_value=0.01,value=0.5,  step=0.05)
        submitted = st.form_submit_button("🏸 Analyze Swing", type="primary")

    if submitted:
        df_rt = pd.DataFrame([{"speed":speed,"impact":impact,"duration":duration}])
        df_rt = add_features(df_rt)
        df_rt["final_prediction"] = classify_final(df_rt)
        df_rt["stroke_type"]      = predict_stroke(df_rt)

        pred  = df_rt["final_prediction"][0]
        stroke= df_rt["stroke_type"][0]
        bcol  = CMAP.get(pred,"#888")
        scol  = SCMAP.get(stroke,"#888")

        # Prediction banner
        st.markdown(f"""
        <div style='text-align:center;margin:18px 0;background:{bcol}22;
                    border:2px solid {bcol};border-radius:14px;padding:20px;'>
          <span style='font-family:Rajdhani,sans-serif;font-size:2rem;font-weight:700;color:{bcol};'>
            🏸 Swing: {pred}
          </span>
          <span style='font-family:Rajdhani,sans-serif;font-size:1.3rem;font-weight:600;
                       color:{scol};margin-left:16px;'>
            │ Stroke: {stroke}
          </span>
        </div>""", unsafe_allow_html=True)

        m1,m2,m3,m4 = st.columns(4)
        m1.metric("⚡ Power",      round(float(df_rt["power"][0]),     2))
        m2.metric("🎯 Efficiency", round(float(df_rt["efficiency"][0]),2))
        m3.metric("🔥 Intensity",  round(float(df_rt["intensity"][0]), 2))
        m4.metric("📏 Duration",   duration)

        # Power gauge
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=round(float(df_rt["power"][0]),1),
            title={"text":"Power Level","font":{"color":"#CBD5E1"}},
            gauge={"axis":{"range":[0,2000],"tickcolor":"#CBD5E1"},
                   "bar":{"color":bcol},
                   "steps":[{"range":[0,600],   "color":"rgba(0,200,83,0.15)"},
                             {"range":[600,1200],"color":"rgba(255,215,0,0.15)"},
                             {"range":[1200,2000],"color":"rgba(255,75,75,0.15)"}],
                   "threshold":{"line":{"color":"white","width":2},"value":float(df_rt["power"][0])}}))
        gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#CBD5E1"),
                            height=280,margin=dict(l=30,r=30,t=40,b=20))
        st.plotly_chart(gauge, use_container_width=True)

        # Quick pro comparison for single swing
        st.markdown("---")
        st.markdown('<div class="sec-title">🏆 Instant Pro Comparison</div>', unsafe_allow_html=True)
        comp_rt = compare_with_pro(df_rt)
        cp1,cp2,cp3 = st.columns(3)
        for col,(metric,lbl) in zip([cp1,cp2,cp3],[("speed","Speed"),("impact","Impact"),("power","Power")]):
            gap = comp_rt[f"gap_{metric}"]
            col.metric(lbl, comp_rt[f"player_avg_{metric}"], f"{gap:+.2f} vs Pro")

        st.markdown("---")
        st.markdown('<div class="sec-title">🧠 AI Feedback</div>', unsafe_allow_html=True)
        sm_rt = get_session_summary(df_rt.assign(final_prediction=df_rt["final_prediction"]))
        for t,title,desc in generate_ai_coaching(sm_rt, comp_rt):
            css = {"good":"card-good","warn":"card-warn","bad":"card-bad","info":"card-info"}.get(t,"card-info")
            st.markdown(f'<div class="{css}"><b>{title}</b><br>'
                        f'<span style="font-size:0.88rem;color:#CBD5E1;">{desc}</span></div>',
                        unsafe_allow_html=True)