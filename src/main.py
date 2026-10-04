import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
# 测试/演示环境可设置 SKIP_MODEL_PRELOAD=1，先启动 API 和文档，不占用 GPU。
if os.getenv("SKIP_MODEL_PRELOAD", "0") == "1":
    print("跳过本地模型预加载：SKIP_MODEL_PRELOAD=1")
else:
    print("=" * 60)
    print("预加载本地模型（主线程）...")
    print("=" * 60)
    preload()

app = FastAPI(title="CognitiveProbe")

# 允许前端（Streamlit / 本地开发页面）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库初始化（PostgreSQL 未启动时跳过，不影响 /reason 等接口）
if os.getenv("SKIP_DB_INIT", "0") == "1":
    print("跳过数据库初始化：SKIP_DB_INIT=1")
else:
    try:
        Base.metadata.create_all(bind=engine)
        # 老库迁移：给已存在的 tasks 表补 result 列（PG 支持 IF NOT EXISTS）
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS result JSON"
            ))
    except Exception as e:
        print(f"⚠️ 数据库连接失败，任务存储相关接口不可用，/reason 等推理接口正常（{e}）")

app.include_router(health_router)
app.include_router(config_router)
app.include_router(test_llm_router)
app.include_router(tasks_router)


app.include_router(agents_router)
