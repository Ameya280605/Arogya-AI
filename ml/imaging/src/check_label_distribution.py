import pandas as pd
from pathlib import Path

data_dir = Path("ml/imaging/data")

csv_path = data_dir / "Data_Entry_2017_v2020.csv"
image_dir = data_dir / "images"

df = pd.read_csv(csv_path)

available_images = {
    image.name for image in image_dir.glob("*.png")
}

df = df[df["Image Index"].isin(available_images)].copy()

labels = [
    "Atelectasis",
    "Cardiomegaly",
    "Effusion",
    "Infiltration",
    "Mass",
    "Nodule",
    "Pneumonia",
    "Pneumothorax",
    "Consolidation",
    "Edema",
    "Emphysema",
    "Fibrosis",
    "Pleural_Thickening",
    "Hernia",
]

print("Available images:", len(df))
print("Unique patients:", df["Patient ID"].nunique())

print("\nPer-label positive counts:")

findings = df["Finding Labels"].fillna("").str.split("|")

for label in labels:
    positive_count = findings.apply(lambda items: label in items).sum()
    print(f"{label}: {positive_count}")
