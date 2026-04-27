import streamlit as st
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import numpy as np

# -------------------------------
# LOAD MODEL
# -------------------------------
model_package = joblib.load(
    r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\ML model PKL\swing_model.pkl"
)

model = model_package["model"]
features = model_package["features"]

st.set_page_config(
    page_title="🏸 AI Badminton Performance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------
# TITLE HEADER
# -------------------------------
st.title("🏸 Smart Badminton AI Performance System")
st.caption("AI-powered swing analysis, consistency tracking & coaching insights")

mode = st.sidebar.selectbox("Select Mode", ["Simulation Mode", "Real-Time Mode"])

# -------------------------------
# FEATURE ENGINEERING
# -------------------------------
def add_features(df):
    df["power"] = df["speed"] * df["impact"]
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)
    df["intensity"] = (df["speed"] + df["impact"] + df["power"]) / 3
    return df


# -------------------------------
# AI COACH ENGINE
# -------------------------------
def generate_feedback(df):

    feedback = []

    power_mean = df["power"].mean()
    power_std = df["power"].std()
    eff_mean = df["efficiency"].mean()

    # Performance
    if power_std > power_mean * 0.4:
        feedback.append("⚠️ Power is unstable → focus on consistency")
    else:
        feedback.append("⚡ Power is stable across session")

    # Efficiency
    if eff_mean < 60:
        feedback.append("⚠️ Efficiency needs improvement (timing/control issue)")
    else:
        feedback.append("🎯 Efficiency is in good range")

    # Technique
    if df["speed"].mean() > 45 and eff_mean < 60:
        feedback.append("⚠️ High speed not converting to impact → technique mismatch")

    # Fatigue
    if len(df) > 10:
        first = df["speed"].iloc[:len(df)//2].mean()
        second = df["speed"].iloc[len(df)//2:].mean()

        if second < first:
            feedback.append("🔻 Fatigue detected in later swings")
        else:
            feedback.append("🔥 No fatigue drop detected")

    # Consistency
    consistency = 100 - (power_std / (power_mean + 1e-6)) * 100

    if consistency < 60:
        feedback.append("⚠️ Low consistency → swing variation is high")
    else:
        feedback.append("🏆 Good consistency across session")

    feedback.append("🏁 Focus: timing + control + repeatable swing execution")

    return feedback, consistency


# ======================================================
# SIMULATION MODE (FULL DASHBOARD)
# ======================================================
if mode == "Simulation Mode":

    st.header("📊 Performance Analytics Dashboard")

    file = st.file_uploader("Upload Session CSV", type=["csv"])

    if file is not None:

        df = pd.read_csv(file)

        for col in ["speed", "impact", "duration"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()

        df = add_features(df)
        df["prediction"] = model.predict(df[features])

        # ---------------- KPIs ----------------
        strong = (df["prediction"] == "STRONG").sum()
        medium = (df["prediction"] == "MEDIUM").sum()
        weak = (df["prediction"] == "WEAK").sum()

        avg_power = df["power"].mean()
        avg_eff = df["efficiency"].mean()

        feedback, consistency = generate_feedback(df)

        # ---------------- HEADER METRICS ----------------
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("🔴 Strong", strong)
        col2.metric("🟡 Medium", medium)
        col3.metric("🟢 Weak", weak)
        col4.metric("⚡ Avg Power", round(avg_power, 2))

        st.divider()

        # ---------------- CHART SECTION ----------------
        tab1, tab2, tab3 = st.tabs([
            "📈 Performance Trends",
            "📊 Distribution",
            "🧩 Analysis"
        ])

        # TAB 1 - Trends
        with tab1:
            c1, c2 = st.columns(2)

            with c1:
                st.subheader("Speed Trend")
                st.line_chart(df["speed"])

            with c2:
                st.subheader("Power Trend")
                st.line_chart(df["power"])

            st.subheader("Efficiency Trend")
            st.line_chart(df["efficiency"])

        # TAB 2 - Distribution
        with tab2:
            st.subheader("Swing Power Distribution")
            fig, ax = plt.subplots()
            ax.hist(df["power"], bins=12)
            st.pyplot(fig)

            st.subheader("Efficiency Spread")
            fig, ax = plt.subplots()
            ax.hist(df["efficiency"], bins=12)
            st.pyplot(fig)

        # TAB 3 - Analysis
        with tab3:
            st.subheader("Speed vs Impact")
            fig, ax = plt.subplots()
            ax.scatter(df["speed"], df["impact"])
            ax.set_xlabel("Speed")
            ax.set_ylabel("Impact")
            st.pyplot(fig)

            st.metric("🎯 Consistency Score", round(consistency, 2))

        st.divider()

        # ---------------- DATA TABLE ----------------
        st.subheader("📋 Session Data")
        st.dataframe(df, use_container_width=True)

        st.divider()

        # ---------------- AI COACH PANEL ----------------
        st.subheader("🧠 AI Coach Panel")

        c1, c2 = st.columns(2)
        c1.metric("⚖️ Consistency Score", round(consistency, 2))
        c2.metric("🔥 Avg Efficiency", round(avg_eff, 2))

        st.subheader("💡 Coaching Insights")

        for f in feedback:
            st.success(f)


# ======================================================
# REAL-TIME MODE
# ======================================================
else:

    st.header("⚡ Real-Time Swing Analyzer")

    speed = st.number_input("Speed", value=40.0)
    impact = st.number_input("Impact", value=30.0)
    duration = st.number_input("Duration", value=0.5)

    if st.button("Analyze Swing"):

        df = pd.DataFrame([{
            "speed": speed,
            "impact": impact,
            "duration": duration
        }])

        df = add_features(df)
        df["prediction"] = model.predict(df[features])

        st.success(f"🏸 Result: {df['prediction'][0]}")

        col1, col2, col3 = st.columns(3)

        col1.metric("⚡ Power", round(df["power"][0], 2))
        col2.metric("🎯 Efficiency", round(df["efficiency"][0], 2))
        col3.metric("🔥 Intensity", round(df["intensity"][0], 2))

        st.subheader("🧠 AI Feedback")

        feedback, _ = generate_feedback(df)

        for f in feedback:
            st.success(f)