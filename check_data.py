import pandas as pd

df = pd.read_csv("data/processed_startups.csv")

print(df["Fate"].value_counts())
print("\nData Types:\n")
print(df.dtypes)