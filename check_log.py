
import csv
from pathlib import Path

log_file = Path("logs/refresh_log.csv")

if not log_file.exists():
    print("Le journal n'existe pas encore.")
else:
    with log_file.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        print("Colonnes du journal :", reader.fieldnames)
        print()

        for row in reader:
            print(row)
