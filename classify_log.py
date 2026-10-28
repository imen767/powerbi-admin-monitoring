
import csv
from pathlib import Path

log_file = Path("logs/refresh_log.csv")
temp_file = Path("logs/refresh_log_fixed.csv")

with log_file.open("r", newline="", encoding="utf-8-sig") as source:
    reader = csv.DictReader(source)
    fieldnames = reader.fieldnames
    rows = list(reader)

for row in rows:
    model_name = row.get("model_name", "")
    error = row.get("error", "")

    if model_name.startswith("TEST - ") or "SIMULATION" in error:
        row["execution_type"] = "SIMULATION"
    else:
        row["execution_type"] = "REAL"

with temp_file.open("w", newline="", encoding="utf-8-sig") as destination:
    writer = csv.DictWriter(destination, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

temp_file.replace(log_file)

print("Classification du journal terminée.")
print("Les entrées TEST sont marquées SIMULATION.")
