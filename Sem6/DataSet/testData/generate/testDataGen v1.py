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
    duration = np.random.uniform(0.2, 1.2)

    data.append([speed, impact, duration])

# -------------------------------
# 2. MEDIUM SWINGS
# -------------------------------
for _ in range(150):
    speed = np.random.uniform(43, 51.9)
    impact = np.random.uniform(35, 42.9)
    duration = np.random.uniform(0.2, 1.2)

    data.append([speed, impact, duration])

# -------------------------------
# 3. STRONG SWINGS
# -------------------------------
for _ in range(150):
    speed = np.random.uniform(52, 60)
    impact = np.random.uniform(43, 55)
    duration = np.random.uniform(0.2, 1.2)

    data.append([speed, impact, duration])

# -------------------------------
# CREATE DATAFRAME
# -------------------------------
df = pd.DataFrame(data, columns=["speed", "impact", "duration"])

# -------------------------------
# RULE-BASED LABEL (GROUND TRUTH)
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
# FEATURE ENGINEERING (OPTIONAL BUT USEFUL)
# -------------------------------
df["power"] = df["speed"] * df["impact"]
df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)

# -------------------------------
# SAVE DATASET
# -------------------------------
output_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\DataSet\testData\data\testSwingData v1.csv"
df.to_csv(output_path, index=False)

print("🚀 Test dataset generated successfully!")
print("📁 Saved at:", output_path)

# sanity check
print("\nClass distribution:")
print(df["new_label"].value_counts())