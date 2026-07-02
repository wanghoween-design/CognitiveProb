#!/bin/bash
# ========================================
# AutoDL 部署脚本
# 用法：在 AutoDL 上执行 bash scripts/autodl_deploy.sh
# ========================================

set -e

echo "=========================================="
echo "CognitiveProbe AutoDL 部署脚本"
echo "=========================================="

# ==================== 1. 环境检查 ====================
echo ""
echo "[1/6] 检查环境..."

# 检查 GPU
if ! nvidia-smi > /dev/null 2>&1; then
    echo "❌ 未检测到 GPU，请确认实例已启动"
    exit 1
fi

echo "GPU 信息："
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# 检查 Python 版本
python_version=$(python --version 2>&1)
echo "Python 版本：$python_version"

# ==================== 2. 创建虚拟环境 ====================
echo ""
echo "[2/6] 创建虚拟环境..."

if [ ! -d ".venv" ]; then
    python -m venv .venv
    echo "虚拟环境创建完成"
else
    echo "虚拟环境已存在，跳过"
fi

source .venv/bin/activate
echo "已激活虚拟环境"

# ==================== 3. 安装依赖 ====================
echo ""
echo "[3/6] 安装依赖..."

# 升级 pip
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 PyTorch（AutoDL 镜像通常已预装，这里确保版本正确）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || true

# 安装项目依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装额外依赖
pip install modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "依赖安装完成"

# ==================== 4. 下载模型 ====================
echo ""
echo "[4/6] 下载模型..."

MODEL_DIR="./models/qwen3-4b/Qwen/Qwen3-4B"

if [ -d "$MODEL_DIR" ] && [ -f "$MODEL_DIR/config.json" ]; then
    echo "模型已存在，跳过下载"
else
    echo "通过 ModelScope 下载 Qwen3-4B..."
    mkdir -p ./models/qwen3-4b

    python -c "
from modelscope import snapshot_download
snapshot_download('Qwen/Qwen3-4B', cache_dir='./models/qwen3-4b')
print('模型下载完成')
"
fi

# 验证模型
if [ -f "$MODEL_DIR/config.json" ]; then
    echo "✅ 模型验证通过"
else
    echo "❌ 模型下载失败，请检查网络"
    exit 1
fi

# ==================== 5. 验证训练数据 ====================
echo ""
echo "[5/6] 验证训练数据..."

for f in data/forward_train.json data/critical_train.json data/creative_train.json; do
    if [ -f "$f" ]; then
        count=$(python -c "import json; print(len(open('$f').readlines()))")
        echo "✅ $f: $count 条"
    else
        echo "❌ $f 不存在"
        exit 1
    fi
done

# ==================== 6. 开始训练 ====================
echo ""
echo "[6/6] 开始训练..."

echo "=========================================="
echo "训练配置："
echo "  GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
echo "  显存: $(nvidia-smi --query-gpu=memory.total --format=csv,noheader)"
echo "  训练脚本: scripts/train_all.py"
echo "  预计耗时: 2-4 小时"
echo "=========================================="
echo ""

# 使用 screen 防止断连
if command -v screen &> /dev/null; then
    echo "使用 screen 运行训练（断连后可恢复）"
    echo "重新连接：screen -r train"
    echo ""
    screen -S train -dm bash -c "
        source .venv/bin/activate
        python scripts/train_all.py 2>&1 | tee training_output.log
        echo '训练完成！'
    "
    echo "✅ 训练已在后台启动"
    echo "查看训练状态：tail -f training_output.log"
    echo "重新连接：screen -r train"
else
    echo "screen 未安装，直接运行训练"
    echo "注意：断开连接会中断训练"
    echo ""
    source .venv/bin/activate
    python scripts/train_all.py 2>&1 | tee training_output.log
fi

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
