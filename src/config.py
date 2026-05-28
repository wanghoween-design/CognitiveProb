"""
配置加载器

作用：读取 configs/config.yaml，让其他代码可以用 config["model"]["base_model"] 的方式访问配置

为什么单独一个文件？
- 所有配置读取逻辑集中在这里
- 其他文件不需要知道 yaml 文件在哪、怎么解析
"""

from pathlib import Path
import yaml


# 项目根目录
# 问：为什么需要这个？
# 答：因为这个文件在 src/ 下面，而 config.yaml 在 configs/ 下面
#     需要知道"往上走一层"才能找到 configs/config.yaml
ROOT_DIR = Path(__file__).parent.parent


def load_config(config_path: str = None) -> dict:
    """
    读取 YAML 配置文件，返回字典

    问：为什么返回 dict？
    答：Python 字典是最通用的数据结构，后面用 config["key"] 就能访问
    """
    if config_path is None:
        config_path = ROOT_DIR / "configs" / "config.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# 全局配置实例
# 问：为什么用全局变量？
# 答：配置只需要读一次，不需要每次都重新解析文件
#     其他文件 import config 就能直接用，不需要调用函数
config = load_config()
