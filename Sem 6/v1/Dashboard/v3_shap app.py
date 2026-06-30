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

# -------------------------------
# PAGE CONFIG
# -------------------------------
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
# STABILITY SCORE
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
# AI COACH ENGINE (SESSION LEVEL)
# -------------------------------
def generate_session_feedback(df):

    feedback = []

    power_mean = df["power"].mean()
    power_std = df["power"].std()
    eff_mean = df["efficiency"].mean()

    # Power consistency
    if power_std > power_mean * 0.4:
        feedback.append("⚠️ Power trend is unstable → focus on consistency")
    else:
        feedback.append("⚡ Power trend is stable across session")

    # Efficiency
    if eff_mean < 60:
        feedback.append("⚠️ Efficiency is low → improve timing & control")
    else:
        feedback.append("🎯 Efficiency is good")

    # Technique check
    if df["speed"].mean() > 45 and eff_mean < 60:
        feedback.append("⚠️ Speed not converting into impact → technique issue")

    if df["impact"].mean() < 30:
        feedback.append("⚠️ Weak impact → improve racket control")

    # Fatigue detection
    if len(df) > 10:
        first_half = df["speed"].iloc[:len(df)//2].mean()
        second_half = df["speed"].iloc[len(df)//2:].mean()

        if second_half < first_half:
            feedback.append("🔻 Fatigue detected in later swings")
        else:
            feedback.append("🔥 No fatigue detected")

    # Consistency
    consistency = 100 - (power_std / (power_mean + 1e-6)) * 100

    if consistency < 60:
        feedback.append("⚠️ Low consistency → swing variation high")
    else:
        feedback.append("🏆 Good consistency across session")

    # Final summary
    feedback.append("🏁 Focus on timing + control + repeatable swing")

    return feedback

# ======================================================
# SIMULATION MODE
# ======================================================
if mode == "Simulation Mode":

    st.header("📊 Simulation Mode - Full Session Analysis")

    file = st.file_uploader("Upload CSV Dataset", type=["csv"])

    # SAFE DEFAULTS (prevents crash)
    stab = 0
    streak = 0

    if file is not None:

        df = pd.read_csv(file)

        # CLEAN DATA
        for col in ["speed", "impact", "duration"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()

        # FEATURE ENGINEERING
        df = add_features(df)

        # PREDICTION
        df["prediction"] = model.predict(df[features])

        # METRICS
        stab = stability_score(df)
        streak = best_streak(df)

        strong = (df["prediction"] == "STRONG").sum()
        medium = (df["prediction"] == "MEDIUM").sum()
        weak = (df["prediction"] == "WEAK").sum()

        # HEADER
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔴 Strong", strong)
        c2.metric("🟡 Medium", medium)
        c3.metric("🟢 Weak", weak)
        c4.metric("⚡ Avg Power", round(df["power"].mean(), 2))

        st.divider()

        # GRAPHS
        col1, col2, col3 = st.columns(3)

        with col1:
            fig, ax = plt.subplots()
            ax.plot(df["speed"])
            ax.set_title("Speed Trend")
            st.pyplot(fig)

        with col2:
            fig, ax = plt.subplots()
            ax.plot(df["power"])
            ax.set_title("Power Trend")
            st.pyplot(fig)

        with col3:
            fig, ax = plt.subplots()
            ax.hist(df["efficiency"], bins=10)
            ax.set_title("Efficiency Distribution")
            st.pyplot(fig)

        st.divider()

        # TABLE
        st.subheader("📋 Dataset")
        st.dataframe(df, use_container_width=True)

        st.divider()

        # AI COACH PANEL
        st.subheader("🧠 AI Coach Panel")

        st.write(f"⚖️ Stability Score: {round(stab,2)}")
        st.write(f"🔥 Best Streak: {streak}")

        st.subheader("💡 Session Feedback")

        feedback_list = generate_session_feedback(df)

        st.success("AI Coaching Insights Generated 🚀")

        for f in feedback_list:
            st.markdown(f"• {f}")

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

        st.subheader("🧠 AI Feedback")

        feedback = []

        if df["efficiency"][0] < 60:
            feedback.append("⚠️ Improve timing → low efficiency")

        if df["power"][0] < 800:
            feedback.append("⚠️ Increase swing power")

        if df["speed"][0] > 45 and df["impact"][0] < 30:
            feedback.append("⚠️ Speed not converting into impact")

        if not feedback:
            feedback.append("🏆 Balanced strong swing")

        for f in feedback:
            st.write(f)