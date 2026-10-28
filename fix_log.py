
import csv
from pathlib import Path

log_file = Path("logs/refresh_log.csv")
temp_file = Path("logs/refresh_log_fixed.csv")

with log_file.open("r", newline="", encoding="utf-8-sig") as source:
    reader = csv.reader(source)
    rows = list(reader)

if not rows:
    print("Le journal est vide.")
else:
    expected_header = [
        "date_utc",
        "model_name",
        "status",
        "duration_seconds",
        "error",
        "execution_type",
    ]

    old_header = rows[0]

    if "execution_type" not in old_header:
        rows[0] = expected_header

        for row in rows[1:]:
            if len(row) < 6:
                row.append("REAL")
    else:
        print("La colonne execution_type existe déjà.")

    with temp_file.open(
        "w", newline="", encoding="utf-8-sig"
    ) as destination:
        writer = csv.writer(destination)
        writer.writerows(rows)

    temp_file.replace(log_file)
    print("En-tête du journal corrigé.")
