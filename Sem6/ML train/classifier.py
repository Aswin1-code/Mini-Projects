import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# -------------------------------
# 1. LOAD DATA
# -------------------------------
df = pd.read_csv(r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\DataSet\w_m_s_cleanedData.csv")

# -------------------------------
# 2. CLEAN DATA (IMPORTANT FIX)
# -------------------------------
df["speed"] = pd.to_numeric(df["speed"], errors="coerce")
df["impact"] = pd.to_numeric(df["impact"], errors="coerce")
df["duration"] = pd.to_numeric(df["duration"], errors="coerce")

df = df.dropna()

# -------------------------------
# 3. RULE-BASED LABEL (your old system)
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
# 4. VISUALIZATION (STEP 1 DONE ✔)
# -------------------------------
plt.scatter(df["speed"], df["impact"], c=df["new_label"].astype("category").cat.codes)
plt.xlabel("Speed")
plt.ylabel("Impact")
plt.title("Swing Clustering Visualization")
plt.show()

# -------------------------------
# 5. ML MODEL (STEP 2)
# -------------------------------
X = df[["speed", "impact", "duration"]]
y = df["new_label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestClassifier(n_estimators=150, random_state=42)
model.fit(X_train, y_train)

# -------------------------------
# 6. PREDICTION
# -------------------------------
y_pred = model.predict(X_test)

# -------------------------------
# 7. ACCURACY (THIS IS WHAT YOU WANTED 🔥)
# -------------------------------
acc = accuracy_score(y_test, y_pred)
print("\n🔥 ML ACCURACY:", acc)

# -------------------------------
# 8. FULL REPORT
# -------------------------------
print("\n=== CLASSIFICATION REPORT ===")
print(classification_report(y_test, y_pred))

print("\n=== CONFUSION MATRIX ===")
print(confusion_matrix(y_test, y_pred))

from sklearn.model_selection import cross_val_score
scores = cross_val_score(model, X, y, cv=5)
print(scores.mean())

sample = pd.DataFrame([[45.2, 38.1, 0.52]],
                      columns=["speed", "impact", "duration"])
print(model.predict(sample))