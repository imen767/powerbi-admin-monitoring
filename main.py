import os
import sys
import time
from datetime import datetime, timezone, timedelta
import csv
from pathlib import Path
from logger import log_refresh

import msal
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")

if not CLIENT_ID or not TENANT_ID:
    sys.exit("Erreur : vérifie les valeurs CLIENT_ID et TENANT_ID dans .env")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

SCOPES = [
    "https://analysis.windows.net/powerbi/api/Workspace.Read.All",
    "https://analysis.windows.net/powerbi/api/Dataset.ReadWrite.All"
]

app = msal.PublicClientApplication(
    client_id=CLIENT_ID,
    authority=AUTHORITY,
)

print("Demande de connexion à Microsoft...")

flow = app.initiate_device_flow(scopes=SCOPES)

if "user_code" not in flow:
    print("Impossible de démarrer la connexion.")
    print(flow.get("error_description", flow))
    sys.exit(1)

print(flow["message"])

result = app.acquire_token_by_device_flow(flow)

if "access_token" not in result:
    print("Échec de l'authentification.")
    print("Erreur :", result.get("error"))
    print("Détail :", result.get("error_description"))
    sys.exit(1)

print("\nConnexion réussie. Appel de l'API Power BI...")

response = requests.get(
    "https://api.powerbi.com/v1.0/myorg/datasets",
    headers={
        "Authorization": f"Bearer {result['access_token']}"
    },
    timeout=30,
)

if response.status_code != 200:
    print("L'API a retourné le statut :", response.status_code)
    print(response.text)
    sys.exit(1)

datasets = response.json().get("value", [])

print(f"\nSuccès ! {len(datasets)} modèle(s) sémantique(s) trouvé(s).")
for dataset in datasets:
    dataset_id = dataset.get("id")

    print("\n--- Détails du modèle sémantique ---")
    print("Nom :", dataset.get("name", "Inconnu"))
    print("ID :", dataset_id)
    print("Actualisable :", dataset.get("isRefreshable", "Non fourni"))

    # Consulter les 5 dernières actualisations
    history_url = (
        f"https://api.powerbi.com/v1.0/myorg/"
        f"datasets/{dataset_id}/refreshes"
    )

    history_response = requests.get(
        history_url,
        headers={
            "Authorization": f"Bearer {result['access_token']}"
        },
        params={"$top": 5},
        timeout=30,
    )

    if history_response.status_code != 200:
        print(
            "Impossible de lire l'historique :",
            history_response.status_code,
        )
        print(history_response.text)
        continue

    refreshes = history_response.json().get("value", [])

    print("\n--- Historique des actualisations ---")

    if not refreshes:
        print("Aucune actualisation retournée par l'API.")
        continue

    for refresh in refreshes:
        print("Statut :", refresh.get("status", "Inconnu"))
        print("Début :", refresh.get("startTime", "Inconnu"))
        print("Fin :", refresh.get("endTime", "En cours ou indisponible"))

        error = refresh.get("serviceExceptionJson")
        if error:
            print("Erreur :", error)

        print("-" * 35)


workspaces = response.json().get("value", [])

print(f"\nSuccès ! {len(workspaces)} espace(s) de travail trouvé(s).")

for workspace in workspaces:
    print(
        f"- {workspace.get('name', 'Sans nom')} "
        f"(ID : {workspace.get('id', 'inconnu')})"
    )

# --- Actualisation réelle avec confirmation explicite ---

TARGET_NAME = "Getting Started in Power BI"

target = next(
    (d for d in datasets if d.get("name") == TARGET_NAME),
    None,
)

if target is None:
    print(f"\nModèle introuvable : {TARGET_NAME}")
else:
    dataset_id = target["id"]

    print("\n" + "=" * 50)
    print("DEMANDE D'ACTUALISATION")
    print("Modèle :", target["name"])
    print("ID :", dataset_id)
    print("Type : actualisation standard")
    print("=" * 50)

    confirmation = input(
        "\nPour lancer une actualisation RÉELLE, "
        "tape exactement CONFIRMER : "
    ).strip()

    if confirmation != "CONFIRMER":
        print("Opération annulée. Aucune requête POST envoyée.")
    else:
        refresh_url = (
            "https://api.powerbi.com/v1.0/myorg/"
            f"datasets/{dataset_id}/refreshes"
        )
        request_started_at = datetime.now(timezone.utc)

        try:
            refresh_response = requests.post(
                refresh_url,
                headers={
                    "Authorization": f"Bearer {result['access_token']}",
                    "Content-Type": "application/json",
                },
                json={"notifyOption": "NoNotification"},
                timeout=30,
            )

            if refresh_response.status_code in (200, 202):
                print("\nPower BI a accepté la demande.")
                print("Code HTTP :", refresh_response.status_code)

                history_url = (
                    "https://api.powerbi.com/v1.0/myorg/"
                    f"datasets/{dataset_id}/refreshes"
                )

                print("\nSurveillance de l'actualisation...")

                final_status_found = False
                monitoring_error = None
                deadline = time.monotonic() + 120

                while time.monotonic() < deadline:
                    time.sleep(5)

                    try:
                        history_response = requests.get(
                            history_url,
                            headers={
                                "Authorization":
                                    f"Bearer {result['access_token']}"
                            },
                            params={"$top": 20},
                            timeout=30,
                        )
                    except requests.RequestException as error:
                        monitoring_error = str(error)
                        print("Erreur pendant la surveillance :", error)
                        break

                    if history_response.status_code != 200:
                        monitoring_error = (
                            f"HTTP {history_response.status_code}: "
                            f"{history_response.text}"
                        )
                        print(
                            "Impossible de consulter l'historique :",
                            monitoring_error,
                        )
                        break

                    refreshes = history_response.json().get("value", [])
                    candidates = []

                    # Garder les actualisations ViaApi démarrées
                    # après le début de notre demande.
                    for refresh in refreshes:
                        start_time = refresh.get("startTime")

                        if not start_time:
                            continue

                        try:
                            parsed_time = datetime.fromisoformat(
                                start_time.replace("Z", "+00:00")
                            )
                        except ValueError:
                            continue

                        if (
                            parsed_time >= request_started_at
                            and refresh.get("refreshType") == "ViaApi"
                        ):
                            candidates.append((parsed_time, refresh))

                    if not candidates:
                        print(
                            "Demande en attente d'apparition "
                            "dans l'historique..."
                        )
                        continue

                    # Examiner l'actualisation correspondante la plus récente.
                    candidates.sort(key=lambda item: item[0], reverse=True)
                    new_refresh = candidates[0][1]

                    status = new_refresh.get("status", "Unknown")
                    print("Statut actuel :", status)

                    if status == "Completed":
                        duration_seconds = None
                        start_time = new_refresh.get("startTime")
                        end_time = new_refresh.get("endTime")

                        if start_time and end_time:
                            try:
                                start = datetime.fromisoformat(
                                    start_time.replace("Z", "+00:00")
                                )
                                end = datetime.fromisoformat(
                                    end_time.replace("Z", "+00:00")
                                )
                                duration_seconds = round(
                                    (end - start).total_seconds(), 2
                                )
                            except ValueError:
                                pass

                        print("\nActualisation terminée avec succès.")

                        log_refresh(
                            model_name=target["name"],
                            status="Completed",
                            duration_seconds=duration_seconds,
                        )

                        final_status_found = True
                        break

                    if status == "Failed":
                        error = new_refresh.get(
                            "serviceExceptionJson",
                            "Erreur non détaillée par l'API",
                        )

                        print("\nÉCHEC de l'actualisation.")
                        print("Détail de l'erreur :", error)

                        log_refresh(
                            model_name=target["name"],
                            status="Failed",
                            error=str(error),
                        )

                        final_status_found = True
                        break

                    # Unknown ou statut intermédiaire : continuer à vérifier.

                # Ce bloc s'exécute après la fin de la boucle,
                # et non à chaque vérification.
                if not final_status_found:
                    if monitoring_error:
                        log_refresh(
                            model_name=target["name"],
                            status="MonitoringError",
                            error=monitoring_error,
                        )
                        print(
                            "La surveillance a rencontré une erreur. "
                            "Vérifie l'historique Power BI."
                        )
                    else:
                        log_refresh(
                            model_name=target["name"],
                            status="Timeout",
                            error=(
                                "Statut final non confirmé après "
                                "120 secondes. Vérifier l'historique Power BI."
                            ),
                        )
                        print(
                            "\nStatut final non confirmé après 120 secondes. "
                            "Consulte l'historique Power BI avant toute "
                            "nouvelle demande."
                        )

        except requests.RequestException as error:
            print("Erreur réseau :", error)
            print(
                "Vérifie l'historique Power BI avant de réessayer, "
                "pour éviter de déclencher une seconde actualisation."
            )