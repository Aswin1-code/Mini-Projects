import pandas as pd

# =========================================
# 1. LOAD CALIBRATION CSV
# =========================================

file_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\dataset\badminton_data (3).csv"

df = pd.read_csv(file_path)

print("\n===== RAW CALIBRATION DATA =====")
print(df.head())

# =========================================
# 2. CLEAN IMPORTANT COLUMNS
# =========================================

required_cols = ["speed", "impact", "duration"]

for col in required_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=required_cols)

print("\nTotal valid swings:", len(df))

if len(df) < 10:
    print("❌ Not enough swing data for calibration")
    exit()

# =========================================
# 3. FEATURE ENGINEERING
# =========================================

# Main strength metric
df["power"] = df["speed"] * df["impact"]

# Optional useful metric
df["efficiency"] = df["impact"] / (df["duration"] + 1e-6)

print("\n===== FEATURES ADDED =====")
print(df[["speed", "impact", "duration", "power", "efficiency"]].head())

# =========================================
# 4. SORT POWER VALUES
# =========================================

power_sorted = df["power"].sort_values().reset_index(drop=True)

print("\n===== SORTED POWER VALUES =====")
print(power_sorted)

# =========================================
# 5. AUTO THRESHOLD GENERATION
# =========================================

# Lower 25% → Weak threshold
weak_threshold = power_sorted.quantile(0.25)

# Upper 75% → Strong threshold
strong_threshold = power_sorted.quantile(0.75)

# Medium lies between both

print("\n===================================")
print("🏸 PERSONALIZED PLAYER THRESHOLDS")
print("===================================")

print(f"WEAK   : Power < {weak_threshold:.2f}")
print(f"MEDIUM : {weak_threshold:.2f} to {strong_threshold:.2f}")
print(f"STRONG : Power > {strong_threshold:.2f}")

# =========================================
# 6. PLAYER BASELINE SUMMARY
# =========================================

avg_speed = df["speed"].mean()
avg_impact = df["impact"].mean()
avg_duration = df["duration"].mean()
avg_power = df["power"].mean()

print("\n===================================")
print("📊 PLAYER BASELINE")
print("===================================")

print(f"Average Speed     : {avg_speed:.2f}")
print(f"Average Impact    : {avg_impact:.2f}")
print(f"Average Duration  : {avg_duration:.2f}")
print(f"Average Power     : {avg_power:.2f}")

# =========================================
# 7. SAVE THRESHOLDS FOR STREAMLIT
# =========================================

thresholds = pd.DataFrame([{
    "weak_threshold": weak_threshold,
    "strong_threshold": strong_threshold,
    "avg_speed": avg_speed,
    "avg_impact": avg_impact,
    "avg_duration": avg_duration,
    "avg_power": avg_power
}])

save_path = r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\v2\player_thresholds2.csv"
thresholds.to_csv(save_path, index=False)

print("\n💾 Thresholds saved at:")
print(save_path)

print("\n✅ Calibration Completed Successfully")