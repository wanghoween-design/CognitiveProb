from fastapi import FastAPI
from src.api.health import router as health_router
from src.api.config_route import router as config_router
from src.api.test_llm import router as test_llm_router
from src.api.tasks import router as tasks_router
from src.models.database import engine
from src.models.task import Base
from src.api.agents import router as agents_router
from src.agents.lora_inference import preload

# ⚠️ 必须在 FastAPI 创建之前、主线程中加载模型
#    如果在 lifecycle/线程池里加载会导致 CUDA 死锁
print("=" * 60)
print("预加载本地模型（主线程）...")
print("=" * 60)
preload()

app = FastAPI(title="CognitiveProbe")

# 数据库初始化（PostgreSQL 未启动时跳过，不影响 /reason 等接口）
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    print("⚠️ 数据库连接失败，任务存储相关接口不可用，/reason 等推理接口正常")

app.include_router(health_router)
app.include_router(config_router)
app.include_router(test_llm_router)
app.include_router(tasks_router)


app.include_router(agents_router)
