from fastapi import FastAPI

app = FastAPI(title="HealthTrackerApp", description = "HealthTracker is a web apis for tracking your health metrics.",   swagger_ui_parameters={"syntaxHighlight": True})

@app.get("/")
async def root():
    return {"message": "Welcome to HealthTrackerApp!!"}

