
from logger import log_refresh

# Simulation locale : aucune requête n'est envoyée à Power BI.
log_refresh(
    model_name="TEST - Getting Started in Power BI",
    status="Failed",
    duration_seconds=5.0,
    error="SIMULATION : échec volontaire pour tester le journal",
)

print("Simulation d'échec terminée.")
print("Aucune actualisation Power BI n'a été lancée.")
