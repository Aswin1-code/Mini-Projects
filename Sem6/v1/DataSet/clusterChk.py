import pandas as pd
import matplotlib.pyplot as plt

# 1. Load CSV
df = pd.read_csv(r"E:\Mini Project\gitfolder all proj\Mini-Projects\Sem6\DataSet\weak.csv")

# 2. Clean data (just in case)
df = df.dropna()

# 3. Map labels to colors
color_map = {
    "WEAK": "red",
    "MEDIUM": "orange",
    "STRONG": "green"
}

colors = df["swing_type"].map(color_map)

# 4. Scatter plot: Speed vs Impact
plt.figure(figsize=(10, 6))
plt.scatter(df["speed"], df["impact"], c=colors, alpha=0.7)

# 5. Labels and title
plt.title("Badminton Swing Analysis: Speed vs Impact")
plt.xlabel("Speed")
plt.ylabel("Impact")

# 6. Add legend manually
import matplotlib.patches as mpatches
legend_labels = [
    mpatches.Patch(color="red", label="WEAK"),
    mpatches.Patch(color="orange", label="MEDIUM"),
    mpatches.Patch(color="green", label="STRONG"),
]
plt.legend(handles=legend_labels)

plt.grid(True)
plt.show()