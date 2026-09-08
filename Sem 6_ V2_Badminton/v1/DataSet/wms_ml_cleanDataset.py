import pandas as pd

# -------------------------------
# 1. LOAD DATASET
# -------------------------------
file_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\DataSet\w_m_s_cleanedData.csv"
df = pd.read_csv(file_path)

# -------------------------------
# 2. CLEAN NUMERIC VALUES
# -------------------------------
df["speed"] = pd.to_numeric(df["speed"], errors="coerce")
df["impact"] = pd.to_numeric(df["impact"], errors="coerce")
df["duration"] = pd.to_numeric(df["duration"], errors="coerce")

df = df.dropna()

# -------------------------------
# 3. CREATE LABEL (RULE-BASED)
# -------------------------------
def assign_label(speed, impact):
    if speed >= 52 or impact >= 43:
        return "STRONG"
    elif speed >= 43 or impact >= 35:
        return "MEDIUM"
    else:
        return "WEAK"

df["new_label"] = df.apply(lambda row: assign_label(row["speed"], row["impact"]), axis=1)
df = df.drop(columns=["swing_type", "timestamp"], errors="ignore")
# -------------------------------
# 4. FEATURE ENGINEERING (OPTIONAL BUT POWERFUL)
# -------------------------------
df["power"] = df["speed"] * df["impact"]
df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)

# -------------------------------
# 5. SAVE FINAL DATASET
# -------------------------------
output_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\DataSet\w_m_s_final_dataset.csv"
df.to_csv(output_path, index=False)

print("🔥 Dataset successfully saved at:")
print(output_path)

# -------------------------------
# 6. READY FOR ML (OPTIONAL OUTPUT)
# -------------------------------
X = df[["speed", "impact", "duration", "power", "efficiency"]]
y = df["new_label"]

print("\n🚗 Dataset ready for ML training!")
print("Features shape:", X.shape)
print("Labels shape:", y.shape)