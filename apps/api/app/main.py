from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(
    title="Agentic Support Copilot API", version="0.1.0", 
    description="API for Agentic Support Copilot"
)
app.include_router(api_router)