import streamlit as st
import pandas as pd
import joblib
import matplotlib.pyplot as plt

# -------------------------------
# LOAD MODEL
# -------------------------------
model_package = joblib.load(r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\ML model PKL\swing_model.pkl")
model = model_package["model"]
features = model_package["features"]

st.title("🏸 Badminton Swing AI System (Standalone)")

mode = st.sidebar.selectbox("Select Mode", ["Simulation Mode", "Real-Time Mode"])

# -------------------------------
# FEATURE ENGINEERING
# -------------------------------
def add_features(df):
    df["power"] = df["speed"] * df["impact"]
    df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)
    return df


# ======================================================
# SIMULATION MODE
# ======================================================
if mode == "Simulation Mode":
    st.header("📊 Simulation Mode (CSV Analysis)")

    file = st.file_uploader("Upload CSV File", type=["csv"])

    if file is not None:
        df = pd.read_csv(file)

        # clean
        for col in ["speed", "impact", "duration"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()

        # features
        df = add_features(df)

        # prediction
        df["prediction"] = model.predict(df[features])

        # summary
        st.success("Simulation Completed 🚀")

        st.write("### 📊 Results Table")
        st.dataframe(df)

        # counts
        weak = (df["prediction"] == "WEAK").sum()
        medium = (df["prediction"] == "MEDIUM").sum()
        strong = (df["prediction"] == "STRONG").sum()

        st.write("### 📊 Summary")
        st.json({
            "total": len(df),
            "weak": int(weak),
            "medium": int(medium),
            "strong": int(strong)
        })

        # visualization
        fig, ax = plt.subplots()
        ax.bar(["WEAK", "MEDIUM", "STRONG"], [weak, medium, strong])
        st.pyplot(fig)


# ======================================================
# REAL-TIME MODE (ESP32 SIMULATION)
# ======================================================
else:
    st.header("⚡ Real-Time Prediction")

    speed = st.number_input("Speed", value=40.0)
    impact = st.number_input("Impact", value=30.0)
    duration = st.number_input("Duration", value=0.5)

    if st.button("Predict Swing"):
        df = pd.DataFrame([{
            "speed": speed,
            "impact": impact,
            "duration": duration
        }])

        df = add_features(df)

        prediction = model.predict(df[features])[0]

        st.success(f"🏸 Prediction: {prediction}")