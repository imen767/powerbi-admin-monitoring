
import csv
from pathlib import Path
from datetime import datetime, timezone


def log_refresh(model_name, status, duration_seconds=None, error="",execution_type="REAL",):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "refresh_log.csv"
    file_exists = log_file.exists()

    with log_file.open(
        "a",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "date_utc",
                "model_name",
                "status",
                "duration_seconds",
                "error",
                "execution_type",
            ])

        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            model_name,
            status,
            duration_seconds if duration_seconds is not None else "",
            error,
            execution_type,
        ])

    print(f"Résultat enregistré dans : {log_file}")
