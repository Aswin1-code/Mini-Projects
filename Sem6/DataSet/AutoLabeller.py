import pandas as pd

# =========================
# 1. LOAD DATA
# =========================
file_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\DataSet\w_m_strong_dataRaw.csv"
df = pd.read_csv(file_path)

# =========================
# 2. CLEAN / TYPE FIX
# =========================
for col in ["speed", "impact", "duration"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# remove bad rows (if any corrupted values exist)
df = df.dropna().reset_index(drop=True)

# =========================
# 3. UPDATED LABEL RULES
# =========================
def assign_label(speed, impact):
    if speed >= 52 or impact >= 43:
        return "STRONG"
    elif (speed >= 43 and speed < 52) or (impact >= 35 and impact < 43):
        return "MEDIUM"
    else:
        return "WEAK"

# =========================
# 4. APPLY LABELS (FASTER THAN apply)
# =========================
df["new_label"] = "WEAK"

df.loc[
    (df["speed"] >= 52) | (df["impact"] >= 43),
    "new_label"
] = "STRONG"

df.loc[
    ((df["speed"] >= 43) & (df["speed"] < 52)) |
    ((df["impact"] >= 35) & (df["impact"] < 43)),
    "new_label"
] = "MEDIUM"

# =========================
# 5. CONFUSION MATRIX
# =========================
print("\n=== LABEL COMPARISON (OLD vs NEW) ===")
print(pd.crosstab(df["swing_type"], df["new_label"]))

# =========================
# 6. MISMATCH ANALYSIS
# =========================
mismatch = df[df["swing_type"] != df["new_label"]]

print("\nMismatch count:", len(mismatch))
print("\nSample mismatches:")
print(mismatch.head(10))

# =========================
# 7. SAVE CLEAN DATASET
# =========================
output_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\DataSet\w_m_s_cleanedData.csv"
df.to_csv(output_path, index=False)

print("\n🚀 Clean dataset saved successfully!")

from sklearn.metrics import classification_report, confusion_matrix

print("\n=== CLASSIFICATION REPORT ===")
print(classification_report(df["swing_type"], df["new_label"]))

print("\n=== CONFUSION MATRIX ===")
print(confusion_matrix(df["swing_type"], df["new_label"]))