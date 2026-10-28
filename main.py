import os
import sys

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
    "https://analysis.windows.net/powerbi/api/Workspace.Read.All"
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
    "https://api.powerbi.com/v1.0/myorg/groups",
    headers={
        "Authorization": f"Bearer {result['access_token']}"
    },
    timeout=30,
)

if response.status_code != 200:
    print("L'API a retourné le statut :", response.status_code)
    print(response.text)
    sys.exit(1)

workspaces = response.json().get("value", [])

print(f"\nSuccès ! {len(workspaces)} espace(s) de travail trouvé(s).")

for workspace in workspaces:
    print(
        f"- {workspace.get('name', 'Sans nom')} "
        f"(ID : {workspace.get('id', 'inconnu')})"
    )