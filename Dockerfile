# ========================================
# CognitiveProbe Docker 镜像
# 用法：docker build -t cognitiveprobe .
# ========================================

# 基础镜像：NVIDIA CUDA + Python
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip3 install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装额外依赖
RUN pip3 install --no-cache-dir \
    streamlit \
    modelscope \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY configs/ ./configs/
COPY data/ ./data/

# 创建必要目录
RUN mkdir -p models adapters adapters_4090

# 暴露端口
EXPOSE 8000 8501

# 启动脚本
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# 启动命令
CMD ["./docker-entrypoint.sh"]
