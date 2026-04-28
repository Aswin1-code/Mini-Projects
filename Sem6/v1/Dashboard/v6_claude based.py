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
    import joblib
    _pkg     = joblib.load(
        r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\ML model PKL\swing_model.pkl"
    )
    MODEL    = _pkg["model"]
    FEATURES = _pkg["features"]
except Exception:
    MODEL    = None
    FEATURES = ["speed", "impact", "duration", "power", "efficiency", "intensity"]

# ── PDF ─────────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors as rlc
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image as RLImage
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
# CSS
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
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PLOTLY DEFAULTS
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
CMAP = {"STRONG": "#FF4B4B", "MEDIUM": "#FFD700", "WEAK": "#00C853"}

# ═══════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ── IMPORTANT: Only compute features that are NOT already in the CSV.
# ── The CSV may already have power/efficiency with different precision.
# ── We always recompute from raw inputs to ensure consistency.
# ═══════════════════════════════════════════════════════════════════════════
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Always recompute derived features from the three raw inputs.
    Drop any pre-existing power/efficiency/intensity columns first
    so the CSV's pre-computed values don't interfere.
    """
    df = df.copy()
    # Drop pre-computed columns from CSV if present — we recompute from scratch
    for col in ["power", "efficiency", "intensity", "swing_no"]:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)

    df["power"]      = df["speed"] * df["impact"]
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)
    df["intensity"]  = (df["speed"] + df["impact"] + df["power"]) / 3
    df["swing_no"]   = range(1, len(df) + 1)
    return df

# ═══════════════════════════════════════════════════════════════════════════
# PREDICTION
# ═══════════════════════════════════════════════════════════════════════════
def predict(df: pd.DataFrame) -> pd.Series:
    if MODEL is not None:
        cols_for_model = [c for c in FEATURES if c in df.columns]
        return pd.Series(MODEL.predict(df[cols_for_model]), index=df.index)
    def rule(row):
        if row["power"] > 900 and row["efficiency"] > 50:  return "STRONG"
        elif row["power"] > 500:                             return "MEDIUM"
        return "WEAK"
    return df.apply(rule, axis=1)

# ═══════════════════════════════════════════════════════════════════════════
# COACH ENGINE
# ═══════════════════════════════════════════════════════════════════════════
def coach_report(df: pd.DataFrame) -> dict:
    r  = {}
    pm = df["power"].mean();      ps = df["power"].std()
    em = df["efficiency"].mean(); sm = df["speed"].mean()
    n  = len(df)

    cv               = ps / (pm + 1e-6)
    r["consistency"] = round(max(0, min(100, 100 - cv * 100)), 1)

    if   r["consistency"] >= 80 and em >= 70: r["grade"] = ("S","#00C853","Elite")
    elif r["consistency"] >= 65 and em >= 55: r["grade"] = ("A","#00D4FF","Advanced")
    elif r["consistency"] >= 50 and em >= 40: r["grade"] = ("B","#FFD700","Intermediate")
    else:                                      r["grade"] = ("C","#FF4B4B","Needs Work")

    r["power_mean"]  = round(pm, 2); r["eff_mean"]  = round(em, 2)
    r["speed_mean"]  = round(sm, 2); r["n_swings"]  = n

    cnt = df["prediction"].value_counts()
    r["strong_pct"] = round(cnt.get("STRONG",0) / n * 100, 1)
    r["medium_pct"] = round(cnt.get("MEDIUM",0) / n * 100, 1)
    r["weak_pct"]   = round(cnt.get("WEAK",  0) / n * 100, 1)

    # Best / worst based on recomputed power (consistent source of truth)
    r["best_swing"]  = df.loc[df["power"].idxmax()].copy()
    r["worst_swing"] = df.loc[df["power"].idxmin()].copy()

    if n >= 6:
        mid  = n // 2
        f1   = df["speed"].iloc[:mid].mean()
        f2   = df["speed"].iloc[mid:].mean()
        drop = (f1 - f2) / (f1 + 1e-6) * 100
        r["fatigue_drop"]     = round(drop, 1)
        r["fatigue_detected"] = drop > 8
    else:
        r["fatigue_drop"] = 0; r["fatigue_detected"] = False

    r["tech_mismatch"]  = (sm > 45 and em < 60)
    r["power_unstable"] = (cv > 0.4)

    if n >= 5:
        roll  = df["power"].rolling(3, min_periods=1).mean()
        slope = np.polyfit(range(len(roll)), roll, 1)[0]
        r["trend"] = "📈 Improving" if slope > 0.3 else ("📉 Declining" if slope < -0.3 else "➡️ Stable")
    else:
        r["trend"] = "➡️ Stable"

    ins = []
    if r["power_unstable"]:
        ins.append(("warn","⚡ Power Inconsistency",
            "Swing power varies too much. Work on consistent grip tension and follow-through."))
    else:
        ins.append(("good","⚡ Power Stability",
            "Power output is stable — great muscular control throughout session."))

    if em < 40:
        ins.append(("bad","🎯 Critical Efficiency",
            "Efficiency critically low. Fix contact timing and reduce wasted arm motion."))
    elif em < 60:
        ins.append(("warn","🎯 Efficiency Below Target",
            "Efficiency needs work — check racket face angle and wrist snap at contact."))
    else:
        ins.append(("good","🎯 Efficiency Optimal",
            "Good impact-to-duration ratio. Technique is converting speed to power well."))

    if r["tech_mismatch"]:
        ins.append(("warn","⚠️ Speed-Impact Mismatch",
            "High swing speed not converting to impact. Adjust contact point timing."))

    if r["fatigue_detected"]:
        ins.append(("bad", f"🔻 Fatigue Detected ({r['fatigue_drop']}% drop)",
            "Performance declined in second half. Add stamina drills and rest intervals."))
    else:
        ins.append(("good","🔥 No Fatigue Detected",
            "Speed maintained throughout — excellent physical conditioning."))

    if r["consistency"] < 60:
        ins.append(("warn",f"📉 Consistency: {r['consistency']}%",
            "High swing variation. Drill repeatable swing mechanics and footwork patterns."))
    else:
        ins.append(("good",f"🏆 Consistency: {r['consistency']}%",
            "Low swing variation — muscle memory is well-developed."))

    r["insights"] = ins
    r["recommendations"] = [
        "🏁 Prioritise timing over raw speed",
        "🎯 Record and compare swing-by-swing metrics weekly",
        "💪 Add plyometric drills to boost explosive power",
        "🧘 Cool-down stretches to reduce next-session fatigue",
    ]
    return r

# ═══════════════════════════════════════════════════════════════════════════
# CHART BUILDERS
# ═══════════════════════════════════════════════════════════════════════════
def chart_trend(df):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        subplot_titles=("Speed","Power","Efficiency"),
                        vertical_spacing=0.08)
    kw = dict(mode="lines+markers", marker=dict(size=5))
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["speed"],
        name="Speed",line=dict(color="#00D4FF"),**kw),row=1,col=1)
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["power"],
        name="Power",line=dict(color="#FFD700"),**kw),row=2,col=1)
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["efficiency"],
        name="Efficiency",line=dict(color="#00C853"),**kw),row=3,col=1)
    fig.update_layout(**_L,height=520,showlegend=False,
                      title_text="📈 Performance Trends Over Swings")
    return fig

def chart_rolling(df):
    win = max(3, len(df)//8)
    fig = go.Figure()
    for col,color,name in [("speed","#00D4FF","Speed"),
                            ("power","#FFD700","Power"),
                            ("efficiency","#00C853","Efficiency")]:
        fig.add_trace(go.Scatter(
            x=df["swing_no"],y=df[col].rolling(win,min_periods=1).mean(),
            name=f"{name} (rolling avg)",line=dict(color=color,width=2.5)))
    fig.update_layout(**_L,height=360,
                      title_text=f"📊 Rolling Average (window={win})")
    return fig

def chart_efficiency_area(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["efficiency"],
        fill="tozeroy",line=dict(color="#00C853",width=2),
        fillcolor="rgba(0,200,83,0.15)",name="Efficiency"))
    mv = df["efficiency"].mean()
    fig.add_hline(y=mv,line_dash="dash",line_color="#FFD700",
                  annotation_text=f"Avg {mv:.1f}",
                  annotation_font_color="#FFD700")
    fig.update_layout(**_L,height=300,title_text="🎯 Efficiency Over Time")
    return fig

def chart_cumulative(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["swing_no"],y=df["power"].cumsum(),
        mode="lines",line=dict(color="#FFD700",width=2),
        fill="tozeroy",fillcolor="rgba(255,215,0,0.1)",
        name="Cumulative Power"))
    fig.update_layout(**_L,height=300,title_text="📈 Cumulative Power Build-Up")
    return fig

def chart_histogram(df):
    fig = make_subplots(rows=1,cols=2,
        subplot_titles=("Power Distribution","Efficiency Distribution"))
    fig.add_trace(go.Histogram(x=df["power"],nbinsx=14,name="Power",
        marker_color="#FFD700",opacity=0.85),row=1,col=1)
    fig.add_trace(go.Histogram(x=df["efficiency"],nbinsx=14,name="Efficiency",
        marker_color="#00C853",opacity=0.85),row=1,col=2)
    fig.update_layout(**_L,height=360,showlegend=False,
                      title_text="📊 Distributions")
    return fig

def chart_box(df):
    fig = go.Figure()
    for col,color in [("speed","#00D4FF"),("power","#FFD700"),("efficiency","#00C853")]:
        fig.add_trace(go.Box(y=df[col],name=col.title(),
                             marker_color=color,boxmean=True))
    fig.update_layout(**_L,height=360,title_text="📦 Box Plot — Spread & Outliers")
    return fig

def chart_category(df):
    cnt = df["prediction"].value_counts().reset_index()
    cnt.columns = ["Category","Count"]
    fig = px.bar(cnt,x="Category",y="Count",color="Category",
                 color_discrete_map=CMAP,text="Count",
                 title="🏸 Swing Category Breakdown")
    fig.update_traces(textposition="outside")
    fig.update_layout(**_L,height=340,showlegend=False)
    return fig

def chart_pie(df):
    cnt = df["prediction"].value_counts().reset_index()
    cnt.columns = ["Category","Count"]
    fig = px.pie(cnt,names="Category",values="Count",
                 color="Category",color_discrete_map=CMAP,
                 title="🍩 Swing Type Distribution",hole=0.45)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter",color="#CBD5E1"),
                      height=340,margin=dict(l=20,r=20,t=44,b=20),
                      legend=dict(bgcolor="rgba(0,0,0,0)"))
    return fig

def chart_scatter(df):
    fig = px.scatter(df,x="speed",y="impact",color="prediction",
                     size="power",hover_data=["efficiency","swing_no"],
                     color_discrete_map=CMAP,
                     title="🔵 Speed vs Impact (bubble = power)")
    fig.update_layout(**_L,height=400)
    return fig

def chart_radar(r):
    cats = ["Power","Efficiency","Consistency","Speed","Intensity"]
    vals = [
        min(100, r["power_mean"]/20),
        min(100, r["eff_mean"]),
        r["consistency"],
        min(100, r["speed_mean"]*2),
        min(100, r["power_mean"]/15),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=vals+[vals[0]],theta=cats+[cats[0]],
        fill="toself",line=dict(color="#00D4FF",width=2),
        fillcolor="rgba(0,212,255,0.15)"))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True,range=[0,100],
                            gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            bgcolor="rgba(0,0,0,0)"),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter",color="#CBD5E1"),
        height=360,margin=dict(l=40,r=40,t=60,b=40),
        title_text="🕸️ Performance Radar")
    return fig

def chart_fatigue(df):
    n = len(df); mid = n//2
    fig = go.Figure()
    fig.add_trace(go.Box(y=df["speed"].iloc[:mid].values,name="First Half",
                          marker_color="#00D4FF",boxmean=True))
    fig.add_trace(go.Box(y=df["speed"].iloc[mid:].values,name="Second Half",
                          marker_color="#FF4B4B",boxmean=True))
    fig.update_layout(**_L,height=340,
                      title_text="🔋 Fatigue Analysis — Speed by Half")
    return fig

def chart_heatmap(df):
    rows = min(len(df),50)
    d    = df.tail(rows)
    fig  = go.Figure(go.Heatmap(
        z=d["power"].values.reshape(1,-1),x=d["swing_no"].values,
        colorscale=[[0,"#00C853"],[0.5,"#FFD700"],[1,"#FF4B4B"]],
        colorbar=dict(title="Power")))
    fig.update_layout(**_L,height=180,
                      title_text="🌡️ Power Heat Map (last swings)")
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# CHART → PNG  (for PDF)
# ═══════════════════════════════════════════════════════════════════════════
def fig_bytes(fig) -> bytes:
    try:
        return fig.to_image(format="png",width=900,height=440,scale=1.8)
    except Exception:
        return b""

# ═══════════════════════════════════════════════════════════════════════════
# PDF BUILDER  — DARK SPORT THEME
# ═══════════════════════════════════════════════════════════════════════════
# Colour palette
PDF_BG        = rlc.HexColor("#0D1117")   # page background
PDF_CARD      = rlc.HexColor("#161B22")   # card / table row background
PDF_CARD_ALT  = rlc.HexColor("#1C2128")   # alternating row
PDF_HEADER    = rlc.HexColor("#00D4FF")   # cyan accent (headers)
PDF_HEADER_BG = rlc.HexColor("#003344")   # table header bg
PDF_TEXT      = rlc.HexColor("#E6EDF3")   # main text
PDF_SUBTEXT   = rlc.HexColor("#8B949E")   # muted text
PDF_GOLD      = rlc.HexColor("#FFD700")   # power / highlight
PDF_GREEN     = rlc.HexColor("#00C853")   # good
PDF_ORANGE    = rlc.HexColor("#FF9800")   # warn
PDF_RED       = rlc.HexColor("#FF4B4B")   # bad / strong
PDF_BORDER    = rlc.HexColor("#30363D")   # subtle border

INSIGHT_COLORS = {
    "good": (rlc.HexColor("#0D2818"), PDF_GREEN),
    "warn": (rlc.HexColor("#2D1B00"), PDF_ORANGE),
    "bad":  (rlc.HexColor("#2D0D0D"), PDF_RED),
    "info": (rlc.HexColor("#001A2D"), PDF_HEADER),
}


def _dark_tbl_style(header_bg=PDF_HEADER_BG, even=PDF_CARD, odd=PDF_CARD_ALT):
    """Return a TableStyle with dark theme."""
    return TableStyle([
        # Header row
        ("BACKGROUND",    (0,0), (-1,0), header_bg),
        ("TEXTCOLOR",     (0,0), (-1,0), PDF_HEADER),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 9),
        # Body rows
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [even, odd]),
        ("TEXTCOLOR",     (0,1), (-1,-1), PDF_TEXT),
        ("FONTSIZE",      (0,1), (-1,-1), 8.5),
        # Grid
        ("GRID",          (0,0), (-1,-1), 0.4, PDF_BORDER),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ])


def build_pdf(df: pd.DataFrame, r: dict, imgs: dict) -> bytes:

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=1.8*cm, rightMargin=1.8*cm,
                             topMargin=2*cm,    bottomMargin=2*cm)

    # ── Page background canvas override ──────────────────────────────────
    # We paint the background by adding an on-page rect via a custom flowable.
    from reportlab.platypus import Flowable

    class DarkBackground(Flowable):
        """Fills the entire page with the dark background colour."""
        def draw(self):
            c = self.canv
            pw, ph = A4
            c.saveState()
            c.setFillColor(PDF_BG)
            c.rect(0, 0, pw, ph, fill=1, stroke=0)
            c.restoreState()
        def wrap(self, *args): return (0, 0)

    # ── Styles ────────────────────────────────────────────────────────────
    def P(name, **kw):
        base = kw.pop("parent", None)
        s = ParagraphStyle(name, **({"parent": base} if base else {}))
        for k, v in kw.items(): setattr(s, k, v)
        return s

    sty = getSampleStyleSheet()

    TITLE_S = P("ts", fontSize=22, textColor=PDF_HEADER,
                alignment=TA_CENTER, fontName="Helvetica-Bold",
                spaceAfter=4, backColor=PDF_BG)
    SUB_S   = P("ss", fontSize=10, textColor=PDF_SUBTEXT,
                alignment=TA_CENTER, spaceAfter=10)
    H1_S    = P("h1s", fontSize=13, textColor=PDF_HEADER,
                fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    H2_S    = P("h2s", fontSize=11, textColor=PDF_GOLD,
                fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)
    BODY_S  = P("bs", fontSize=9, textColor=PDF_TEXT, leading=14, spaceAfter=4)
    FOOT_S  = P("fs", fontSize=8, textColor=PDF_SUBTEXT, alignment=TA_CENTER)

    def colored_para(text, fg, size=9, bold=False):
        fn = "Helvetica-Bold" if bold else "Helvetica"
        return P(f"cp_{id(text)}", fontSize=size, textColor=fg,
                 fontName=fn, leading=14)

    story = []

    # ── Cover ─────────────────────────────────────────────────────────────
    story.append(DarkBackground())
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("BADMINTON AI PERFORMANCE REPORT", TITLE_S))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y  •  %H:%M')}", SUB_S))

    # Cyan divider
    story.append(HRFlowable(width="100%", thickness=2,
                             color=PDF_HEADER, spaceAfter=16))

    # ── KPI Summary Table ─────────────────────────────────────────────────
    story.append(Paragraph("SESSION KPI SUMMARY", H1_S))

    kpi_data = [
        ["Metric", "Value", "Metric", "Value"],
        ["Total Swings",   str(r["n_swings"]),
         "Avg Power",      str(r["power_mean"])],
        ["Avg Efficiency", str(r["eff_mean"]),
         "Avg Speed",      str(r["speed_mean"])],
        ["Consistency %",  str(r["consistency"]),
         "Trend",          r["trend"].replace("📈","").replace("📉","").replace("➡️","").strip()],
        ["Strong %",       f"{r['strong_pct']}%",
         "Medium %",       f"{r['medium_pct']}%"],
        ["Weak %",         f"{r['weak_pct']}%",
         "Fatigue Drop",   f"{r['fatigue_drop']}%"],
    ]
    kpi_t = Table(kpi_data, colWidths=[4*cm, 2.8*cm, 4*cm, 2.8*cm])
    kpi_t.setStyle(_dark_tbl_style())
    story.append(kpi_t)
    story.append(Spacer(1, 0.4*cm))

    # Grade badge
    grade, gcolor, glabel = r["grade"]
    gb_data = [[f"  PERFORMANCE GRADE:  {grade}  —  {glabel}  "]]
    gb = Table(gb_data, colWidths=[13.6*cm])
    gb.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), rlc.HexColor(gcolor)),
        ("TEXTCOLOR",     (0,0),(-1,-1), rlc.HexColor("#0D1117")),
        ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 13),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 9),
        ("BOTTOMPADDING", (0,0),(-1,-1), 9),
    ]))
    story.append(gb)
    story.append(Spacer(1, 0.5*cm))

    # ── Best / Worst Swings ───────────────────────────────────────────────
    story.append(Paragraph("HIGHLIGHT SWINGS", H1_S))

    def swing_row(label, s):
        return [
            label,
            str(int(s.get("swing_no", 0))),
            str(round(float(s["speed"]),      2)),
            str(round(float(s["impact"]),     2)),
            str(round(float(s["power"]),      2)),
            str(round(float(s["efficiency"]), 2)),
            str(s.get("prediction", "—")),
        ]

    bw_data = [
        ["", "Swing #", "Speed", "Impact", "Power", "Efficiency", "Category"],
        swing_row("BEST",  r["best_swing"]),
        swing_row("WORST", r["worst_swing"]),
    ]
    bw_t = Table(bw_data, colWidths=[2*cm,2*cm,2*cm,2*cm,2.3*cm,2.5*cm,2*cm])
    bw_style = _dark_tbl_style()
    # Override row backgrounds for best/worst
    bw_style.add("BACKGROUND", (0,1), (-1,1), rlc.HexColor("#0D2818"))  # green tint
    bw_style.add("TEXTCOLOR",  (0,1), (-1,1), PDF_GREEN)
    bw_style.add("BACKGROUND", (0,2), (-1,2), rlc.HexColor("#2D0D0D"))  # red tint
    bw_style.add("TEXTCOLOR",  (0,2), (-1,2), PDF_RED)
    bw_style.add("FONTNAME",   (0,1), (0,1),  "Helvetica-Bold")
    bw_style.add("FONTNAME",   (0,2), (0,2),  "Helvetica-Bold")
    bw_t.setStyle(bw_style)
    story.append(bw_t)
    story.append(Spacer(1, 0.5*cm))

    # ── Charts ────────────────────────────────────────────────────────────
    story.append(Paragraph("PERFORMANCE CHARTS", H1_S))
    for key, label in [("trend",    "Performance Trends"),
                        ("scatter",  "Speed vs Impact"),
                        ("category", "Swing Category Breakdown"),
                        ("radar",    "Performance Radar"),
                        ("fatigue",  "Fatigue Analysis")]:
        if imgs.get(key):
            story.append(Paragraph(label, H2_S))
            story.append(RLImage(io.BytesIO(imgs[key]), width=14*cm, height=7*cm))
            story.append(Spacer(1, 0.3*cm))

    story.append(PageBreak())
    story.append(DarkBackground())

    # ── AI Coach Panel ────────────────────────────────────────────────────
    story.append(Paragraph("AI COACH PANEL", H1_S))

    for t, title, desc in r["insights"]:
        bg_col, fg_col = INSIGHT_COLORS.get(t, (PDF_CARD, PDF_HEADER))
        title_p = Paragraph(
            title,
            P(f"ip_{id(title)}", fontSize=9.5, textColor=fg_col,
              fontName="Helvetica-Bold", leading=14))
        desc_p  = Paragraph(
            desc,
            P(f"dp_{id(desc)}", fontSize=8.8, textColor=PDF_TEXT, leading=13))
        ins_t = Table([[title_p, desc_p]], colWidths=[4.2*cm, 9.4*cm])
        ins_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg_col),
            ("BOX",           (0,0),(-1,-1), 0.8, fg_col),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ]))
        story.append(ins_t)
        story.append(Spacer(1, 0.2*cm))

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("RECOMMENDATIONS", H1_S))
    for rec in r["recommendations"]:
        rec_clean = rec.replace("🏁","").replace("🎯","").replace("💪","").replace("🧘","").strip()
        rec_t = Table([[Paragraph(f"►  {rec_clean}",
                                  P(f"rp_{id(rec)}", fontSize=9, textColor=PDF_TEXT,
                                    leading=14))]],
                       colWidths=[13.6*cm])
        rec_t.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,-1), PDF_CARD),
            ("BOX",          (0,0),(-1,-1), 0.4, PDF_BORDER),
            ("LEFTPADDING",  (0,0),(-1,-1), 12),
            ("TOPPADDING",   (0,0),(-1,-1), 6),
            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ]))
        story.append(rec_t)
        story.append(Spacer(1, 0.15*cm))

    # ── Full Session Data ─────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(DarkBackground())
    story.append(Paragraph("FULL SESSION DATA", H1_S))

    cols = [c for c in ["swing_no","speed","impact","duration",
                          "power","efficiency","prediction"] if c in df.columns]
    header = [c.replace("_"," ").title() for c in cols]
    rows   = [header] + [
        [str(round(float(row[c]),2)) if isinstance(row[c],(float,int,np.floating,np.integer))
         and c != "swing_no" else str(int(row[c])) if c == "swing_no" else str(row[c])
         for c in cols]
        for _, row in df.iterrows()
    ]
    cw  = [13.6*cm / len(cols)] * len(cols)
    dt  = Table(rows, colWidths=cw, repeatRows=1)
    dt.setStyle(_dark_tbl_style())
    story.append(dt)

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=PDF_BORDER))
    story.append(Paragraph(
        "Generated by Badminton AI Pro  •  AI-powered swing analysis system",
        FOOT_S))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# SESSION-STATE HELPERS  (clears everything when a new file is uploaded)
# ═══════════════════════════════════════════════════════════════════════════
if "file_id" not in st.session_state:
    st.session_state.file_id  = None
    st.session_state.df       = None
    st.session_state.report   = None
    st.session_state.pdf_ready = False
    st.session_state.pdf_bytes = None


def reset_session():
    st.session_state.df        = None
    st.session_state.report    = None
    st.session_state.pdf_ready = False
    st.session_state.pdf_bytes = None


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🏸 Badminton AI Pro")
    st.markdown("---")
    mode = st.selectbox("Select Mode", ["📊 Simulation Mode","⚡ Real-Time Mode"])
    st.markdown("---")
    st.caption("AI-powered swing analysis · fatigue detection · "
               "consistency tracking · dark-theme PDF export")
    if MODEL is None:
        st.warning("⚠️ Model file not found.\nUsing rule-based fallback.", icon="🤖")

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
    AI-powered swing analysis · consistency tracking · coaching insights · PDF export
  </p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# ════════════════════  SIMULATION MODE  ════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
if "Simulation" in mode:

    st.markdown('<div class="sec-title">📊 Performance Analytics Dashboard</div>',
                unsafe_allow_html=True)

    file = st.file_uploader("Upload Session CSV", type=["csv"])

    # ── Detect new file upload → reset all state ─────────────────────────
    if file is not None:
        file_id = (file.name, file.size)
        if st.session_state.file_id != file_id:
            reset_session()
            st.session_state.file_id = file_id

            # Process new file
            df_raw = pd.read_csv(file)
            for col in ["speed","impact","duration"]:
                if col in df_raw.columns:
                    df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")
            df_raw.dropna(subset=["speed","impact","duration"], inplace=True)

            df = add_features(df_raw)   # always recomputes from raw inputs
            df["prediction"] = predict(df)

            st.session_state.df     = df
            st.session_state.report = coach_report(df)

    elif file is None and st.session_state.file_id is not None:
        # File was removed → wipe state
        reset_session()
        st.session_state.file_id = None

    # ── Only render dashboard if we have data ─────────────────────────────
    if st.session_state.df is not None:
        df = st.session_state.df
        r  = st.session_state.report

        # ── KPI ROW ──────────────────────────────────────────────────────
        k1,k2,k3,k4,k5,k6 = st.columns(6)
        k1.metric("🔴 Strong",     f"{r['strong_pct']}%")
        k2.metric("🟡 Medium",     f"{r['medium_pct']}%")
        k3.metric("🟢 Weak",       f"{r['weak_pct']}%")
        k4.metric("⚡ Avg Power",   r["power_mean"])
        k5.metric("🎯 Efficiency",  r["eff_mean"])
        k6.metric("🏆 Consistency", f"{r['consistency']}%")

        st.divider()

        # ── HIGHLIGHT SWINGS ─────────────────────────────────────────────
        hc1, hc2 = st.columns(2)
        with hc1:
            bs = r["best_swing"]
            st.markdown(f"""
            <div class="hl-best">
              <b>🔥 Best Swing — #{int(bs.get('swing_no',0))}</b><br>
              Speed: <b>{round(float(bs['speed']),2)}</b> &nbsp;|&nbsp;
              Impact: <b>{round(float(bs['impact']),2)}</b> &nbsp;|&nbsp;
              Power: <b>{round(float(bs['power']),2)}</b> &nbsp;|&nbsp;
              Efficiency: <b>{round(float(bs['efficiency']),2)}</b>
            </div>""", unsafe_allow_html=True)
        with hc2:
            ws = r["worst_swing"]
            st.markdown(f"""
            <div class="hl-worst">
              <b>⚠️ Worst Swing — #{int(ws.get('swing_no',0))}</b><br>
              Speed: <b>{round(float(ws['speed']),2)}</b> &nbsp;|&nbsp;
              Impact: <b>{round(float(ws['impact']),2)}</b> &nbsp;|&nbsp;
              Power: <b>{round(float(ws['power']),2)}</b> &nbsp;|&nbsp;
              Efficiency: <b>{round(float(ws['efficiency']),2)}</b>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # ── TABS ─────────────────────────────────────────────────────────
        tab1,tab2,tab3,tab4,tab5 = st.tabs([
            "📈 Trends","📊 Distributions","🔬 Relationships","🧠 AI Coach","📋 Data"
        ])

        with tab1:
            st.plotly_chart(chart_trend(df),          use_container_width=True)
            st.plotly_chart(chart_rolling(df),         use_container_width=True)
            st.plotly_chart(chart_efficiency_area(df), use_container_width=True)
            st.plotly_chart(chart_cumulative(df),      use_container_width=True)

        with tab2:
            st.plotly_chart(chart_histogram(df), use_container_width=True)
            c21, c22 = st.columns(2)
            with c21: st.plotly_chart(chart_category(df), use_container_width=True)
            with c22: st.plotly_chart(chart_pie(df),      use_container_width=True)
            st.plotly_chart(chart_box(df),    use_container_width=True)
            st.plotly_chart(chart_heatmap(df),use_container_width=True)

        with tab3:
            st.plotly_chart(chart_scatter(df), use_container_width=True)
            c31, c32 = st.columns(2)
            with c31: st.plotly_chart(chart_radar(r),    use_container_width=True)
            with c32: st.plotly_chart(chart_fatigue(df), use_container_width=True)

        with tab4:
            gc1, gc2, gc3 = st.columns(3)
            gc1.metric("⚖️ Consistency",   f"{r['consistency']}%")
            gc2.metric("🔥 Avg Efficiency", r["eff_mean"])
            gc3.metric("📊 Trend",          r["trend"])

            grade, gcolor, glabel = r["grade"]
            st.markdown(f"""
            <div style='text-align:center;margin:16px 0;background:{gcolor}22;
                        border:2px solid {gcolor};border-radius:12px;padding:16px;'>
              <span style='font-family:Rajdhani,sans-serif;font-size:2.4rem;
                           font-weight:700;color:{gcolor};'>{grade}</span>
              <span style='font-size:1.1rem;color:{gcolor};margin-left:12px;'>{glabel}</span>
            </div>""", unsafe_allow_html=True)

            st.markdown('<div class="sec-title">💡 Coaching Insights</div>',
                        unsafe_allow_html=True)
            for t, title, desc in r["insights"]:
                css = {"good":"card-good","warn":"card-warn",
                       "bad":"card-bad","info":"card-info"}.get(t,"card-info")
                st.markdown(f"""
                <div class="{css}">
                  <b>{title}</b><br>
                  <span style='font-size:0.88rem;color:#CBD5E1;'>{desc}</span>
                </div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown('<div class="sec-title">🏆 Recommendations</div>',
                        unsafe_allow_html=True)
            for rec in r["recommendations"]:
                st.markdown(f"<div class='card-info'>{rec}</div>",
                            unsafe_allow_html=True)

        with tab5:
            # Show only cleanly recomputed columns
            display_cols = [c for c in
                ["swing_no","speed","impact","duration","power","efficiency","intensity","prediction"]
                if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True)
            st.download_button("⬇️ Download CSV",
                               df[display_cols].to_csv(index=False).encode(),
                               "session_data.csv", "text/csv")

        st.divider()

        # ── PDF EXPORT ───────────────────────────────────────────────────
        st.markdown('<div class="sec-title">📄 Export Full Report as PDF</div>',
                    unsafe_allow_html=True)
        st.caption("Generates a dark-themed multi-page PDF with KPIs, charts, "
                   "AI insights, highlight swings and full data table.")

        if st.button("🖨️ Generate PDF Report", type="primary"):
            with st.spinner("Rendering charts and compiling dark-theme PDF…"):
                imgs = {
                    "trend":    fig_bytes(chart_trend(df)),
                    "scatter":  fig_bytes(chart_scatter(df)),
                    "category": fig_bytes(chart_category(df)),
                    "radar":    fig_bytes(chart_radar(r)),
                    "fatigue":  fig_bytes(chart_fatigue(df)),
                }
                imgs = {k:v for k,v in imgs.items() if v}
                st.session_state.pdf_bytes = build_pdf(df, r, imgs)
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
        st.info("👆 Upload a CSV file to begin analysis.")

# ═══════════════════════════════════════════════════════════════════════════
# ════════════════════  REAL-TIME MODE  ═════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
else:
    st.markdown('<div class="sec-title">⚡ Real-Time Swing Analyzer</div>',
                unsafe_allow_html=True)

    with st.form("rt_form"):
        c1, c2, c3 = st.columns(3)
        speed    = c1.number_input("Speed",    min_value=0.0, value=40.0, step=0.5)
        impact   = c2.number_input("Impact",   min_value=0.0, value=30.0, step=0.5)
        duration = c3.number_input("Duration", min_value=0.01,value=0.5,  step=0.05)
        submitted = st.form_submit_button("🏸 Analyze Swing", type="primary")

    if submitted:
        df_rt = pd.DataFrame([{"speed":speed,"impact":impact,"duration":duration}])
        df_rt = add_features(df_rt)
        df_rt["prediction"] = predict(df_rt)

        pred = df_rt["prediction"][0]
        bcol = CMAP.get(pred, "#888")

        st.markdown(f"""
        <div style='text-align:center;margin:18px 0;background:{bcol}22;
                    border:2px solid {bcol};border-radius:14px;padding:20px;'>
          <span style='font-family:Rajdhani,sans-serif;font-size:2rem;
                       font-weight:700;color:{bcol};'>
            🏸 Swing Result: {pred}
          </span>
        </div>""", unsafe_allow_html=True)

        m1,m2,m3,m4 = st.columns(4)
        m1.metric("⚡ Power",      round(float(df_rt["power"][0]),      2))
        m2.metric("🎯 Efficiency", round(float(df_rt["efficiency"][0]), 2))
        m3.metric("🔥 Intensity",  round(float(df_rt["intensity"][0]),  2))
        m4.metric("📏 Duration",   duration)

        # Power gauge
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=round(float(df_rt["power"][0]),1),
            title={"text":"Power Level","font":{"color":"#CBD5E1"}},
            gauge={
                "axis":      {"range":[0,2000],"tickcolor":"#CBD5E1"},
                "bar":       {"color": bcol},
                "steps":     [{"range":[0,600],   "color":"rgba(0,200,83,0.15)"},
                              {"range":[600,1200], "color":"rgba(255,215,0,0.15)"},
                              {"range":[1200,2000],"color":"rgba(255,75,75,0.15)"}],
                "threshold": {"line":{"color":"white","width":2},
                              "value": float(df_rt["power"][0])}
            }))
        gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#CBD5E1"),
                            height=280,margin=dict(l=30,r=30,t=40,b=20))
        st.plotly_chart(gauge, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🧠 AI Feedback")
        r_rt = coach_report(df_rt)
        for t, title, desc in r_rt["insights"]:
            css = {"good":"card-good","warn":"card-warn",
                   "bad":"card-bad","info":"card-info"}.get(t,"card-info")
            st.markdown(f"""
            <div class="{css}">
              <b>{title}</b><br>
              <span style='font-size:0.88rem;color:#CBD5E1;'>{desc}</span>
            </div>""", unsafe_allow_html=True)