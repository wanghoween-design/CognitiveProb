from fastapi import FastAPI
from src.api.health import router as health_router
from src.api.config_route import router as config_router
from src.api.test_llm import router as test_llm_router

app = FastAPI(title="CognitiveProb")

app.include_router(health_router)
app.include_router(config_router)
app.include_router(test_llm_router)