from fastapi import FastAPI
from src.api.health import router as health_router
from src.api.config_route import router as config_router
from src.api.test_llm import router as test_llm_router
from src.api.tasks import router as tasks_router
from src.models.database import engine
from src.models.task import Base
from src.api.agents import router as agents_router

app = FastAPI(title="CognitiveProb")
Base.metadata.create_all(bind=engine)

app.include_router(health_router)
app.include_router(config_router)
app.include_router(test_llm_router)
app.include_router(tasks_router)


app.include_router(agents_router)
