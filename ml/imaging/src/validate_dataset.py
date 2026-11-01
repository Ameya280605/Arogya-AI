import tarfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "ml" / "imaging" / "data"

ARCHIVE_PATH = DATA_DIR / "images_001.tar.gz"
CSV_PATH = DATA_DIR / "Data_Entry_2017_v2020.csv"


def main():
    print("Loading dataset metadata...")
    df = pd.read_csv(CSV_PATH)

    print(f"CSV records: {len(df):,}")
    print(f"Unique patients: {df['Patient ID'].nunique():,}")

    print("\nInspecting image archive...")
    with tarfile.open(ARCHIVE_PATH, "r:gz") as archive:
        image_names = {
            Path(member.name).name
            for member in archive.getmembers()
            if member.isfile() and member.name.lower().endswith(".png")
        }

    csv_names = set(df["Image Index"].astype(str))
    matched_names = image_names & csv_names

    print(f"PNG images in archive: {len(image_names):,}")
    print(f"Image filenames matched to CSV: {len(matched_names):,}")
    print(f"Archive images missing from CSV: {len(image_names - csv_names):,}")
    print(f"CSV images not in archive: {len(csv_names - image_names):,}")

    subset = df[df["Image Index"].isin(matched_names)]

    print("\nLabel distribution in this archive:")
    print(subset["Finding Labels"].value_counts().head(20).to_string())

    print("\nImage view positions:")
    print(subset["View Position"].value_counts(dropna=False).to_string())

    print("\nDataset validation inspection complete.")
    print("No images were extracted or modified.")


if __name__ == "__main__":
    main()