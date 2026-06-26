"""
调试脚本：最小化复现，定位 uvicorn 里加载模型卡住的根因
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Step 1: import 模型加载模块...")
from src.agents.lora_inference import preload

print("Step 2: 加载模型...")
preload()

print("Step 3: 加载完成，启动 FastAPI...")

from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
