import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    """健康检查：附带模型 / Mock / 数据库状态，前端据此显示服务状态"""
    from src.agents.lora_inference import is_model_loaded, loaded_adapters, mock_enabled
    from src.models.database import engine

    db_ok = False
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "mock_llm": mock_enabled(),
        "model_loaded": is_model_loaded(),
        "loaded_adapters": loaded_adapters(),
        "db": db_ok,
    }
