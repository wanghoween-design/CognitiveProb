#!/bin/bash
# ========================================
# CognitiveProbe 启动脚本
# ========================================

set -e

echo "=========================================="
echo "CognitiveProbe 启动中..."
echo "=========================================="

# ==================== 1. 下载模型 ====================
MODEL_DIR="models/qwen3-4b/Qwen/Qwen3-4B"

if [ ! -f "$MODEL_DIR/config.json" ]; then
    echo "[1/3] 模型不存在，通过 ModelScope 下载..."
    mkdir -p models/qwen3-4b
    python3 -c "
from modelscope import snapshot_download
snapshot_download('Qwen/Qwen3-4B', cache_dir='models/qwen3-4b')
print('模型下载完成')
"
else
    echo "[1/3] 模型已存在，跳过下载"
fi

# ==================== 2. 检查 adapter ====================
echo "[2/3] 检查 adapter..."
if [ -d "adapters_4090/forward_lora" ] && [ -f "adapters_4090/forward_lora/adapter_model.safetensors" ]; then
    echo "  ✅ adapters_4090 存在"
elif [ -d "adapters/forward_lora" ] && [ -f "adapters/forward_lora/adapter_model.safetensors" ]; then
    echo "  ✅ adapters 存在"
else
    echo "  ⚠️ 未找到 adapter，系统将使用基座模型"
fi

# ==================== 3. 启动服务 ====================
echo "[3/3] 启动服务..."

# 启动 FastAPI（后台）
echo "  启动 FastAPI (port 8000)..."
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# 等待 FastAPI 启动
sleep 5

# 启动 Streamlit（后台）
echo "  启动 Streamlit (port 8501)..."
streamlit run scripts/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    &
STREAMLIT_PID=$!

echo "=========================================="
echo "服务已启动！"
echo "  FastAPI:    http://localhost:8000"
echo "  Streamlit:  http://localhost:8501"
echo "  API 文档:   http://localhost:8000/docs"
echo "=========================================="

# 等待任意进程退出
wait $FASTAPI_PID $STREAMLIT_PID
