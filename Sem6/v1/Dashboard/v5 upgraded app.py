import streamlit as st
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import numpy as np
import os
import json

# =========================
# PAGE CONFIG (DARK PRODUCT UI)
# =========================
st.set_page_config(
    page_title="🏸 AI Badminton OS",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
body {
    background-color: #0e1117;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.title("🏸 AI Badminton Performance OS")
st.caption("Player Analytics • AI Coach • Performance Tracking")

# =========================
# LOAD MODEL
# =========================
model_package = joblib.load(
    r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\ML model PKL\swing_model.pkl"
)

model = model_package["model"]
features = model_package["features"]

# =========================
# STORAGE FILES (SIMULATED DATABASE)
# =========================
PLAYER_DB = "players.json"
SESSION_DB = "sessions.csv"

# =========================
# INIT STORAGE
# =========================
if not os.path.exists(PLAYER_DB):
    with open(PLAYER_DB, "w") as f:
        json.dump({}, f)

if not os.path.exists(SESSION_DB):
    pd.DataFrame(columns=["player", "speed", "impact", "duration", "power", "efficiency"]).to_csv(SESSION_DB, index=False)

# =========================
# FEATURE ENGINEERING
# =========================
def add_features(df):
    df["power"] = df["speed"] * df["impact"]
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)
    return df

# =========================
# LOAD PLAYER DB
# =========================
def load_players():
    with open(PLAYER_DB, "r") as f:
        return json.load(f)

def save_players(data):
    with open(PLAYER_DB, "w") as f:
        json.dump(data, f)

# =========================
# SIDEBAR - PLAYER SELECT
# =========================
st.sidebar.header("🎮 Player Control")

players = load_players()

player_name = st.sidebar.text_input("Player Name", "Aswin")

if player_name not in players:
    players[player_name] = {
        "sessions": 0,
        "avg_power": 0,
        "avg_efficiency": 0
    }

save_players(players)

st.sidebar.success(f"Logged in as {player_name}")

mode = st.sidebar.selectbox(
    "Select Mode",
    ["🏠 Dashboard", "📊 New Session", "🏆 Leaderboard"]
)

# =========================
# DASHBOARD HOME
# =========================
if mode == "🏠 Dashboard":

    st.header("📊 Player Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Sessions Played", players[player_name]["sessions"])
    col2.metric("Avg Power", round(players[player_name]["avg_power"], 2))
    col3.metric("Avg Efficiency", round(players[player_name]["avg_efficiency"], 2))

    st.info("Upload a session in 'New Session' to improve stats 🚀")

# =========================
# NEW SESSION MODE
# =========================
elif mode == "📊 New Session":

    st.header("⚡ Upload Training Session")

    file = st.file_uploader("Upload CSV", type=["csv"])

    if file is not None:

        df = pd.read_csv(file)

        for col in ["speed", "impact", "duration"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()

        df = add_features(df)

        df["prediction"] = model.predict(df[features])

        # ---------------- SESSION METRICS ----------------
        avg_power = df["power"].mean()
        avg_eff = df["efficiency"].mean()

        # update player stats
        players[player_name]["sessions"] += 1
        players[player_name]["avg_power"] = (
            players[player_name]["avg_power"] + avg_power
        ) / 2

        players[player_name]["avg_efficiency"] = (
            players[player_name]["avg_efficiency"] + avg_eff
        ) / 2

        save_players(players)

        # save session history
        df["player"] = player_name
        df.to_csv(SESSION_DB, mode="a", header=False, index=False)

        # ---------------- UI ----------------
        st.success("Session Saved 🚀")

        c1, c2, c3 = st.columns(3)

        c1.metric("⚡ Avg Power", round(avg_power, 2))
        c2.metric("🎯 Avg Efficiency", round(avg_eff, 2))
        c3.metric("🏸 Strong Shots", (df["prediction"] == "STRONG").sum())

        st.subheader("📈 Performance Trend")

        st.line_chart(df["power"])

# =========================
# LEADERBOARD
# =========================
elif mode == "🏆 Leaderboard":

    st.header("🏆 Player Rankings")

    df = pd.read_csv(SESSION_DB)

    if len(df) > 0:

        leaderboard = df.groupby("player").agg({
            "power": "mean",
            "efficiency": "mean"
        }).reset_index()

        leaderboard["score"] = (
            leaderboard["power"] * 0.5 +
            leaderboard["efficiency"] * 0.5
        )

        leaderboard = leaderboard.sort_values("score", ascending=False)

        st.dataframe(leaderboard, use_container_width=True)

        st.bar_chart(leaderboard.set_index("player")["score"])

    else:
        st.warning("No session data available yet 🚀")