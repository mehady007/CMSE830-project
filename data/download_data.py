"""Re-download the three public Our World in Data files into this folder.

Usage:  python data/download_data.py
"""
from pathlib import Path
from urllib.request import urlretrieve

HERE = Path(__file__).resolve().parent
SNAPSHOT_DATE = "2026-10-16"  # date the CSVs in data/ were downloaded; update after a refresh
FILES = {
    "owid-co2-data.csv": "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv",
    "owid-energy-data.csv": "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv",
    "owid-continents.csv": ("https://ourworldindata.org/grapher/continents-according-to-our-world-in-data.csv"
                            "?v=1&csvType=full&useColumnShortNames=true"),
}

if __name__ == "__main__":
    for name, url in FILES.items():
        print(f"Downloading {name} ...")
        urlretrieve(url, HERE / name)
    print("Done. Note: OWID updates these files; numbers may differ slightly from the October 2026 snapshot.")
    print("Remember to update SNAPSHOT_DATE in this file.")
