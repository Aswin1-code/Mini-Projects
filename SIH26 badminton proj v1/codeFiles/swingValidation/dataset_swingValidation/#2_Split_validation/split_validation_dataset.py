import pandas as pd
from sklearn.model_selection import train_test_split
import os

MASTER_FILE = r"E:\Mini Project\gitfolder all proj\Mini-Projects\SIH26 badminton proj v1\codeFiles\swingValidation\dataset_swingValidation\#1_master dataset\master_validation_dataset.csv"

BASE = os.path.dirname(MASTER_FILE)

TRAIN_FILE = os.path.join(BASE, "validation_train.csv")
TEST_FILE = os.path.join(BASE, "validation_test.csv")

df = pd.read_csv(MASTER_FILE)

FEATURES = [
    "ax", "ay", "az",
    "gx", "gy", "gz",
    "speed", "impact", "duration"
]

X = df[FEATURES]
y = df["validity"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

train_df = X_train.copy()
train_df["validity"] = y_train.values

test_df = X_test.copy()
test_df["validity"] = y_test.values

train_df.to_csv(TRAIN_FILE, index=False)
test_df.to_csv(TEST_FILE, index=False)

print("\n==============================================")
print("VALIDATION DATASET SPLIT")
print("==============================================")

print("\nTRAINING DATA")
print("VALID   :", (train_df["validity"] == "VALID").sum())
print("INVALID :", (train_df["validity"] == "INVALID").sum())
print("TOTAL   :", len(train_df))

print("\nTEST DATA")
print("VALID   :", (test_df["validity"] == "VALID").sum())
print("INVALID :", (test_df["validity"] == "INVALID").sum())
print("TOTAL   :", len(test_df))

print("\nSaved:")
print(TRAIN_FILE)
print(TEST_FILE)

print("\n==============================================")