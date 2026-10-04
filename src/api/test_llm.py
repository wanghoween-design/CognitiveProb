from fastapi import APIRouter

from src.agents.lora_inference import generate_base

router = APIRouter()


@router.get("/test_llm")
def test_llm():
    """测试本地模型是否可以正常推理（Mock 模式下返回 mock 回答）"""
    try:
        answer = generate_base("用一句话简单介绍自己")
        return {"response": answer}
    except Exception as e:
        return {"error": str(e)}
