import pandas as pd
import numpy as np

np.random.seed(42)

data = []

# -------------------------------
# 1. WEAK SWINGS
# -------------------------------
for _ in range(150):
    speed = np.random.uniform(20, 42)
    impact = np.random.uniform(10, 34)
    duration = np.random.uniform(0.4, 1.4)

    data.append([speed, impact, duration])

# -------------------------------
# 2. MEDIUM SWINGS
# -------------------------------
for _ in range(150):
    speed = np.random.uniform(43, 51.9)
    impact = np.random.uniform(35, 42.9)
    duration = np.random.uniform(0.35, 1.2)

    data.append([speed, impact, duration])

# -------------------------------
# 3. STRONG SWINGS
# -------------------------------
for _ in range(150):
    speed = np.random.uniform(52, 60)
    impact = np.random.uniform(43, 55)
    duration = np.random.uniform(0.3, 1.0)

    data.append([speed, impact, duration])

# -------------------------------
# CREATE DATAFRAME
# -------------------------------
df = pd.DataFrame(data, columns=["speed", "impact", "duration"])

# -------------------------------
# LABELING RULE
# -------------------------------
def assign_label(speed, impact):
    if speed >= 52 or impact >= 43:
        return "STRONG"
    elif speed >= 43 or impact >= 35:
        return "MEDIUM"
    else:
        return "WEAK"

df["new_label"] = df.apply(lambda row: assign_label(row["speed"], row["impact"]), axis=1)

# -------------------------------
# FEATURE ENGINEERING (FIXED)
# -------------------------------

# Power (raw physical interaction)
df["power"] = df["speed"] * df["impact"]

# Efficiency (normalized 0–100 scale)
df["efficiency_raw"] = df["impact"] / df["duration"]

# Normalize efficiency to 0–100 range
df["efficiency"] = (
    (df["efficiency_raw"] - df["efficiency_raw"].min()) /
    (df["efficiency_raw"].max() - df["efficiency_raw"].min())
) * 100

# Intensity (balanced score)

# -------------------------------
# DROP RAW COLUMN
# -------------------------------
df.drop(columns=["efficiency_raw"], inplace=True)

# -------------------------------
# SAVE DATASET
# -------------------------------
output_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\DataSet\testData\data\testSwingData_v3.csv"
df.to_csv(output_path, index=False)

print("🚀 Clean test dataset generated successfully!")
print("📁 Saved at:", output_path)

# -------------------------------
# CLASS DISTRIBUTION CHECK
# -------------------------------
print("\nClass distribution:")
print(df["new_label"].value_counts())

# -------------------------------
# QUICK STATS CHECK
# -------------------------------
print("\nEfficiency range check:")
print("Min:", df["efficiency"].min())
print("Max:", df["efficiency"].max())