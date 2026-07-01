"""
三个 LoRA Agent 训练结果横向对比
用法: python scripts/plot_compare.py
依赖: pip install matplotlib numpy
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from matplotlib.ticker import MaxNLocator, FuncFormatter


# ==================== 中文字体配置 ====================
# 尝试加载系统中文字体，如果找不到就用默认字体
def get_chinese_font():
    """获取支持中文的字体"""
    chinese_fonts = [
        "Microsoft YaHei",      # 微软雅黑
        "SimHei",               # 黑体
        "SimSun",               # 宋体
        "KaiTi",                # 楷体
        "Arial Unicode MS",     # Arial Unicode
        "Noto Sans CJK SC",     # Noto Sans
        "WenQuanYi Micro Hei",  # 文泉驿
    ]
    for font_name in chinese_fonts:
        try:
            font_path = fm.findfont(fm.FontProperties(family=font_name))
            if font_path and "DejaVu" not in font_path:
                return font_name
        except:
            continue
    return None

chinese_font = get_chinese_font()
if chinese_font:
    plt.rcParams["font.sans-serif"] = [chinese_font, "DejaVu Sans"]
    print(f"✅ 使用中文字体: {chinese_font}")
else:
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    print("⚠️ 未找到中文字体，使用默认字体（中文可能显示为方框）")

plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题


# ==================== 基础配置 ====================
BASE_DIR = Path(__file__).parent.parent / "adapters"

LOG_PATHS = {
    "Forward (r=8)": BASE_DIR / "forward_lora" / "training_log.json",
    "Critical (r=12)": BASE_DIR / "critical_lora" / "training_log.json",
    "Creative (r=16)": BASE_DIR / "creative_lora" / "training_log.json",
}

# 输出路径
OUT_DIR = BASE_DIR
OUT_PNG = OUT_DIR / "training_comparison.png"
OUT_PDF = OUT_DIR / "training_comparison.pdf"


# ==================== 读取日志 ====================
all_logs = {}
for name, path in LOG_PATHS.items():
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            all_logs[name] = json.load(f)
        print(f"✅ 已加载 {name}: {len(all_logs[name])} 条记录")
    else:
        print(f"⚠️ 跳过 {name}: 文件不存在 {path}")

if not all_logs:
    print("❌ 没有找到任何训练日志，请先运行训练脚本")
    sys.exit(1)


# ==================== 画图风格 ====================
plt.rcParams.update({
    "figure.dpi": 160,
    "savefig.dpi": 300,

    "font.family": "DejaVu Sans",
    "font.size": 10,

    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "axes.linewidth": 0.8,

    "xtick.labelsize": 9,
    "ytick.labelsize": 9,

    "legend.fontsize": 10,
    "legend.frameon": False,

    "lines.linewidth": 2.0,
    "lines.markersize": 4,

    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

# 三个 Agent 的颜色
COLORS = {
    "Forward (r=8)": "#D55E00",    # 橙色
    "Critical (r=12)": "#0072B2",  # 蓝色
    "Creative (r=16)": "#009E73",  # 绿色
}

# 四个指标
METRICS = [
    ("Training Loss", "loss", "Loss", False),
    ("Mean Token Accuracy", "mean_token_accuracy", "Accuracy", True),
    ("Gradient Norm", "grad_norm", "Grad. Norm", None),
    ("Policy Entropy", "entropy", "Entropy", None),
]


# ==================== 工具函数 ====================
def moving_average(values: np.ndarray, window: int = 3) -> np.ndarray:
    """轻量平滑"""
    if len(values) < window:
        return values
    kernel = np.ones(window) / window
    padded = np.pad(values, (window // 2, window - 1 - window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def smart_formatter(x, pos):
    """让纵轴数字更干净"""
    if abs(x) >= 100:
        return f"{x:.0f}"
    if abs(x) >= 10:
        return f"{x:.1f}"
    if abs(x) >= 1:
        return f"{x:.2f}"
    return f"{x:.3f}"


# ==================== 创建画布 ====================
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.flatten()

for idx, (title, key, ylabel, higher_is_better) in enumerate(METRICS):
    ax = axes[idx]

    for name, logs in all_logs.items():
        epochs = np.array([log["epoch"] for log in logs], dtype=float)
        values = np.array([log[key] for log in logs], dtype=float)
        smooth_values = moving_average(values, window=3)

        color = COLORS[name]

        # 原始曲线：浅线
        ax.plot(
            epochs,
            values,
            color=color,
            alpha=0.25,
            linewidth=1.0,
        )

        # 平滑曲线：主线
        ax.plot(
            epochs,
            smooth_values,
            color=color,
            linewidth=2.2,
            label=name,
        )

        # 最后一个值标注（偏移避免重叠）
        final_value = values[-1]
        ax.scatter(
            epochs[-1],
            final_value,
            color=color,
            s=30,
            zorder=5,
        )

        # 根据不同 Agent 调整标注位置，避免重叠
        offsets = {
            "Forward (r=8)": (5, 8),
            "Critical (r=12)": (5, -3),
            "Creative (r=16)": (5, 3),
        }
        offset = offsets.get(name, (5, 0))

        ax.annotate(
            f"{final_value:.3g}",
            xy=(epochs[-1], final_value),
            xytext=offset,
            textcoords="offset points",
            va="center",
            fontsize=7,
            color=color,
            fontweight="bold",
        )

    # 标题和标签
    ax.set_title(title, fontweight="bold", pad=10)
    ax.set_xlabel("Epoch")
    ax.set_ylabel(ylabel)

    # 网格和边框
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(FuncFormatter(smart_formatter))

    # Accuracy 固定到 0-1 范围
    if key == "mean_token_accuracy":
        ax.set_ylim(0.4, 0.8)

    # 图例
    ax.legend(loc="upper right" if higher_is_better else "upper right")

    # 标注最终值的含义（放在角落，避免遮挡曲线）
    if higher_is_better is True:
        ax.annotate("↑ Higher is better", xy=(0.98, 0.05), xycoords="axes fraction",
                    fontsize=7, color="green", ha="right", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
    elif higher_is_better is False:
        ax.annotate("↓ Lower is better", xy=(0.98, 0.05), xycoords="axes fraction",
                    fontsize=7, color="red", ha="right", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))


# ==================== 总标题 ====================
fig.suptitle(
    "LoRA Training Comparison: Forward vs Critical vs Creative",
    fontsize=16,
    fontweight="bold",
    y=1.02,
)

fig.text(
    0.5,
    -0.02,
    "Thin lines show raw values; bold lines show a 3-epoch moving average. "
    "Each model uses different LoRA rank and target modules.",
    ha="center",
    fontsize=9,
    color="dimgray",
)

plt.tight_layout()

# ==================== 保存 ====================
plt.savefig(OUT_PNG, bbox_inches="tight", dpi=300)
plt.savefig(OUT_PDF, bbox_inches="tight", dpi=300)

print(f"\nPNG 图表已保存: {OUT_PNG}")
print(f"PDF 图表已保存: {OUT_PDF}")

plt.show()
