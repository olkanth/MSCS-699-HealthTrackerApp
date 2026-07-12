from fastapi import FastAPI
from .routers import patients, vital_signs, activity, alert_thresholds, alerts, risk_scores

# Creating the fastapi app instance.
app = FastAPI(title="HealthTrackerApp", description = "HealthTracker is a web apis for tracking your health metrics.",   swagger_ui_parameters={"syntaxHighlight": True})

app.include_router(patients.router)
app.include_router(vital_signs.router)
app.include_router(activity.router)
app.include_router(alert_thresholds.router)
app.include_router(alerts.router)
app.include_router(risk_scores.router)

# root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to HealthTrackerApp!!"}

