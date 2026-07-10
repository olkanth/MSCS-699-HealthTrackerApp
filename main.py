from fastapi import FastAPI

app = FastAPI(title="HealthTracker App", swagger_ui_parameters={"syntaxHighlight": True})

@app.get("/")
async def root():
    return {"message": "Hello World"}

