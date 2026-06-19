"""测试配置加载"""
import sys
sys.path.insert(0, ".")

from src.config import config

# 测试访问不同层级的配置
print("1. 基础模型:", config["model"]["base_model"])
print("2. Forward rank:", config["model"]["lora"]["forward"]["r"])
print("3. Ollama URL:", config["ollama"]["base_url"])
print("4. Critical 权重:", config["coordinator"]["vote_weights"]["critical"])
print("\n配置加载成功!")
print(config)