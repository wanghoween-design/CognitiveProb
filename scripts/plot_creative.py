"""
Creative LoRA 训练指标可视化：论文风格 2D 多指标图
用法: python scripts/plot_creative.py
依赖: pip install matplotlib numpy
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator, FuncFormatter


# ==================== 基础配置 ====================
LOG_PATH = Path(__file__).parent.parent / "adapters" / "creative_lora" / "training_log.json"

OUT_DIR = LOG_PATH.parent
OUT_PNG = OUT_DIR / "training_metrics_paper_style.png"
OUT_PDF = OUT_DIR / "training_metrics_paper_style.pdf"


# ==================== 读取日志 ====================
with open(LOG_PATH, "r", encoding="utf-8") as f:
    logs = json.load(f)

epochs = np.array([log["epoch"] for log in logs], dtype=float)

def get_metric_value(log, keys):
    """从日志中获取指标值，兼容不同的 key 名称"""
    for key in keys:
        if key in log:
            return log[key]
    return 0

metrics = {
    "Training Loss": {
        "key": "loss",
        "values": np.array([get_metric_value(log, ["loss", "train_loss"]) for log in logs], dtype=float),
        "ylabel": "Loss",
        "higher_is_better": False,
    },
    "Gradient Norm": {
        "key": "grad_norm",
        "values": np.array([get_metric_value(log, ["grad_norm"]) for log in logs], dtype=float),
        "ylabel": "Grad. Norm",
        "higher_is_better": None,
    },
    "Policy Entropy": {
        "key": "entropy",
        "values": np.array([get_metric_value(log, ["entropy"]) for log in logs], dtype=float),
        "ylabel": "Entropy",
        "higher_is_better": None,
    },
    "Mean Token Accuracy": {
        "key": "mean_token_accuracy",
        "values": np.array([get_metric_value(log, ["mean_token_accuracy"]) for log in logs], dtype=float),
        "ylabel": "Accuracy",
        "higher_is_better": True,
    },
}


# ==================== 画图风格 ====================
plt.rcParams.update({
    "figure.dpi": 160,
    "savefig.dpi": 300,

    "font.family": "DejaVu Sans",
    "font.size": 10,

    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "axes.linewidth": 0.8,

    "xtick.labelsize": 9,
    "ytick.labelsize": 9,

    "legend.fontsize": 9,
    "legend.frameon": False,

    "lines.linewidth": 2.0,
    "lines.markersize": 4,

    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

# 色盲友好配色，论文图里比较稳
COLORS = {
    "Training Loss": "#D55E00",
    "Gradient Norm": "#0072B2",
    "Policy Entropy": "#009E73",
    "Mean Token Accuracy": "#CC79A7",
}


# ==================== 工具函数 ====================
def normalize(values: np.ndarray) -> np.ndarray:
    """归一化到 [0, 1]，常数序列放到 0.5，避免画成贴底线。"""
    vmin, vmax = np.min(values), np.max(values)
    if np.isclose(vmax - vmin, 0):
        return np.full_like(values, 0.5, dtype=float)
    return (values - vmin) / (vmax - vmin)


def moving_average(values: np.ndarray, window: int = 3) -> np.ndarray:
    """轻量平滑，epoch少时自动退化为原曲线。"""
    if len(values) < window:
        return values
    kernel = np.ones(window) / window
    padded = np.pad(values, (window // 2, window - 1 - window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def smart_formatter(x, pos):
    """让纵轴数字更干净。"""
    if abs(x) >= 100:
        return f"{x:.0f}"
    if abs(x) >= 10:
        return f"{x:.1f}"
    if abs(x) >= 1:
        return f"{x:.2f}"
    return f"{x:.3f}"


# ==================== 创建画布 ====================
fig = plt.figure(figsize=(12.5, 8.0))

# 上面一张总览，下面 2x2 展示真实数值
gs = fig.add_gridspec(
    nrows=3,
    ncols=2,
    height_ratios=[1.15, 1.0, 1.0],
    hspace=0.55,
    wspace=0.28,
)

ax_overview = fig.add_subplot(gs[0, :])
axes = [
    fig.add_subplot(gs[1, 0]),
    fig.add_subplot(gs[1, 1]),
    fig.add_subplot(gs[2, 0]),
    fig.add_subplot(gs[2, 1]),
]


# ==================== 上方：归一化总览 ====================
for name, info in metrics.items():
    values = info["values"]
    values_norm = normalize(values)
    smooth_norm = moving_average(values_norm, window=3)

    color = COLORS[name]

    ax_overview.plot(
        epochs,
        smooth_norm,
        color=color,
        label=name,
        linewidth=2.2,
    )

    ax_overview.scatter(
        epochs[-1],
        smooth_norm[-1],
        color=color,
        s=28,
        zorder=5,
    )

    # 右侧直接标注，比图例更适合论文阅读
    ax_overview.text(
        epochs[-1] + 0.03 * (epochs[-1] - epochs[0] + 1),
        smooth_norm[-1],
        name,
        color=color,
        va="center",
        fontsize=9,
    )

ax_overview.set_title("Training Dynamics Overview", fontweight="bold", pad=8)
ax_overview.set_xlabel("Epoch")
ax_overview.set_ylabel("Normalized Value")
ax_overview.set_ylim(-0.05, 1.08)
ax_overview.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
ax_overview.spines["top"].set_visible(False)
ax_overview.spines["right"].set_visible(False)
ax_overview.xaxis.set_major_locator(MaxNLocator(integer=True))


# ==================== 下方：真实数值子图 ====================
for ax, (name, info) in zip(axes, metrics.items()):
    values = info["values"]
    smooth_values = moving_average(values, window=3)
    color = COLORS[name]

    # 原始曲线：浅线
    ax.plot(
        epochs,
        values,
        color=color,
        alpha=0.28,
        linewidth=1.2,
    )

    # 平滑曲线：主线
    ax.plot(
        epochs,
        smooth_values,
        color=color,
        linewidth=2.2,
    )

    # 每个点
    ax.scatter(
        epochs,
        values,
        color=color,
        s=18,
        alpha=0.75,
        zorder=4,
    )

    # 最后一个值标注
    final_value = values[-1]
    ax.scatter(
        epochs[-1],
        final_value,
        color=color,
        s=34,
        zorder=5,
    )

    ax.annotate(
        f"{final_value:.4g}",
        xy=(epochs[-1], final_value),
        xytext=(6, 0),
        textcoords="offset points",
        va="center",
        fontsize=8,
        color=color,
        fontweight="bold",
    )

    # 标题里放 min/max，方便看范围
    vmin, vmax = np.min(values), np.max(values)
    ax.set_title(
        f"{name}  [{vmin:.4g}, {vmax:.4g}]",
        loc="left",
        fontweight="bold",
        pad=6,
    )

    ax.set_xlabel("Epoch")
    ax.set_ylabel(info["ylabel"])

    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(FuncFormatter(smart_formatter))

    # token acc 如果是 0~1，可以固定到稍微好看的范围
    if name == "Mean Token Accuracy":
        ymin = max(0.0, np.min(values) - 0.05)
        ymax = min(1.0, np.max(values) + 0.05)
        if ymax - ymin < 0.1:
            center = (ymax + ymin) / 2
            ymin, ymax = max(0.0, center - 0.05), min(1.0, center + 0.05)
        ax.set_ylim(ymin, ymax)


# ==================== 总标题与说明 ====================
fig.suptitle(
    "Creative LoRA Training Metrics",
    fontsize=15,
    fontweight="bold",
    y=0.98,
)

fig.text(
    0.5,
    0.015,
    "Thin lines show raw values; bold lines show a 3-epoch moving average. "
    "The top panel normalizes each metric for trend comparison.",
    ha="center",
    fontsize=9,
    color="dimgray",
)


# 给右侧直接标注留空间
plt.subplots_adjust(right=0.86, bottom=0.08, top=0.92)

# ==================== 保存 ====================
plt.savefig(OUT_PNG, bbox_inches="tight")
plt.savefig(OUT_PDF, bbox_inches="tight")

print(f"PNG 图表已保存: {OUT_PNG}")
print(f"PDF 图表已保存: {OUT_PDF}")

plt.show()
