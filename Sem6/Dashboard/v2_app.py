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

st.set_page_config(page_title="🏸 Badminton AI Analytics", layout="wide")

st.title("🏸 Smart Badminton Performance Analytics System")

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
# CONSISTENCY / STABILITY SCORE
# -------------------------------
def stability_score(df):
    return 100 - (df["power"].std() / (df["power"].mean() + 1e-6)) * 100


# -------------------------------
# BEST STREAK
# -------------------------------
def best_streak(df):
    streak = best = 0
    for p in df["prediction"]:
        if p == "STRONG":
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best


# -------------------------------
# FEEDBACK ENGINE
# -------------------------------
def generate_feedback(df):
    feedback = []

    if df["power"].std() > df["power"].mean() * 0.5:
        feedback.append("⚠️ Power improving but inconsistent")

    if df["speed"].mean() > 45 and df["efficiency"].mean() < 60:
        feedback.append("⚠️ High speed but low impact efficiency → technique issue")

    if len(df) > 15:
        first = df["speed"].iloc[:len(df)//2].mean()
        second = df["speed"].iloc[len(df)//2:].mean()
        if second < first:
            feedback.append("⚠️ Fatigue detected after mid-session")

    if not feedback:
        feedback.append("✅ Strong consistent performance")

    return feedback


# ======================================================
# SIMULATION MODE (FULL ANALYTICS)
# ======================================================
if mode == "Simulation Mode":
    st.header("📊 Simulation Mode - Full Analytics Dashboard")

    file = st.file_uploader("Upload CSV Dataset", type=["csv"])

    if file is not None:

        df = pd.read_csv(file)

        # CLEANING
        for col in ["speed", "impact", "duration"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()

        # FEATURE ENGINEERING
        df = add_features(df)

        # PREDICTION
        df["prediction"] = model.predict(df[features])

        # -------------------------------
        # SESSION METRICS
        # -------------------------------
        total = len(df)
        weak = (df["prediction"] == "WEAK").sum()
        medium = (df["prediction"] == "MEDIUM").sum()
        strong = (df["prediction"] == "STRONG").sum()

        strong_percent = (strong / total) * 100

        avg_power = df["power"].mean()
        avg_eff = df["efficiency"].mean()

        stab = stability_score(df)
        streak = best_streak(df)

        # -------------------------------
        # TOP HEADER METRICS
        # -------------------------------
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("🔴 Strong Swings", strong)
        col2.metric("🟡 Medium Swings", medium)
        col3.metric("🟢 Weak Swings", weak)
        col4.metric("⚡ Avg Power", round(avg_power, 2))

        st.divider()

        # -------------------------------
        # GRAPHS ROW
        # -------------------------------
        c1, c2, c3 = st.columns(3)

        with c1:
            fig, ax = plt.subplots()
            ax.plot(df["speed"])
            ax.set_title("Speed Trend")
            st.pyplot(fig)

        with c2:
            fig, ax = plt.subplots()
            ax.plot(df["power"])
            ax.set_title("Power Trend")
            st.pyplot(fig)

        with c3:
            fig, ax = plt.subplots()
            ax.hist(df["efficiency"], bins=10)
            ax.set_title("Efficiency Distribution")
            st.pyplot(fig)

        st.divider()

        # -------------------------------
        # TABLE
        # -------------------------------
        st.subheader("📋 Full Swing Dataset")
        st.dataframe(df, use_container_width=True)

        st.divider()

        # -------------------------------
        # INSIGHTS PANEL
        # -------------------------------
        st.subheader("🧠 AI Insight Panel")

        st.write(f"📊 Strong Swing %: {round(strong_percent,2)}%")
        st.write(f"⚖️ Stability Score: {round(stab,2)}")
        st.write(f"🔥 Best Streak: {streak}")

        st.subheader("💡 Coaching Feedback")
        for f in generate_feedback(df):
            st.write(f)


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

        st.metric("⚡ Power", round(df["power"][0], 2))
        st.metric("🎯 Efficiency", round(df["efficiency"][0], 2))
        st.metric("🔥 Intensity", round(df["intensity"][0], 2))

        st.subheader("🧠 Feedback")
        for f in generate_feedback(df):
            st.write(f)