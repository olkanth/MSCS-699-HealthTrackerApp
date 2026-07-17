from contextlib import asynccontextmanager

from fastapi import FastAPI
from .database import ensure_database_exists
from .routers import auth, patients, vital_signs, activity, alert_thresholds, alerts, risk_scores


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database if not exist, this will help avoided manual database creation.
    # However, it's not recommended in actual production environmnet because it may cause creating DB on a misconfiured connection.  
    ensure_database_exists()
    yield


# Creating the fastapi app instance.
app = FastAPI(
    title="HealthTrackerApp",
    description="HealthTracker is a web apis for tracking your health metrics.",
    swagger_ui_parameters={"syntaxHighlight": True},
    lifespan=lifespan,
)

app.include_router(auth.router)
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

