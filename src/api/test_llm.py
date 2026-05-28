from fastapi import APIRouter
from src.config import config
import ollama

router = APIRouter()

@router.get("/test_llm")
def test_llm():
    client = ollama.Client(
        host=config["ollama"]["base_url"]
    )
    response = client.chat(
        model = config["model"]["base_model"],
        messages=[{"role": "user", "content": "一句话简单介绍自己"}]
    )
    return {"response": response["message"]["content"]}