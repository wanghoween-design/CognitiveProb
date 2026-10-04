"""
CognitiveProbe 前端界面（v2）
=============================
深色控制台风格 + 全链路流程可视化。

- 流式读取 /reason/stream：LangGraph 每个节点完成即推送一个事件
- 流程图实时点亮：执行中的节点呼吸发光，完成的节点打勾并显示耗时，
  没有走的路径保持暗淡，一眼看出"推理进行到了哪一步"
- 三视角分析、辩论过程、观点修正、最终结论分区呈现

用法：streamlit run scripts/app.py
"""
import html
import json
import os
import time

import requests
import streamlit as st

# ==================== 常量 ====================
# 默认 API 地址：可用环境变量 COGNITIVEPROBE_API_URL 覆盖（多项目并存 / 自定义端口时有用）
DEFAULT_API = os.getenv("COGNITIVEPROBE_API_URL", "http://127.0.0.1:8000")

TYPE_META = {
    "simple_greeting": ("👋", "简单问候", "#34d399"),
    "simple_factual": ("📚", "简单事实", "#fbbf24"),
    "complex_reasoning": ("🧩", "复杂推理", "#818cf8"),
}

EXAMPLES = [
    ("📅 四天工作制", "全面分析中国实行四天制工作日的影响"),
    ("👶 未成年人保护", "部分欧洲国家已经限制16岁以下儿童使用社交媒体，你认为我国该不该跟进，或者全面禁止未成年人使用社交媒体？"),
    ("🤖 AI 利弊", "人工智能是弊大于利还是利大于弊？深度剖析这个问题"),
    ("🚗 新能源汽车", "新能源汽车取代燃油车还需要多少年？会带来哪些连锁反应？"),
]

# 链路定义：每个单元是一个或多个并行节点（key, 图标, 名称, 颜色）
def _u(label, *nodes):
    return {"label": label, "nodes": list(nodes)}

CHAIN_COMPLEX = [
    _u(None, ("question", "💬", "提问", "#818cf8")),
    _u(None, ("coordinator", "🧭", "协调路由", "#22d3ee")),
    _u("三视角并行",
       ("agent_forward", "🔮", "前瞻", "#38bdf8"),
       ("agent_critical", "🔍", "批判", "#fbbf24"),
       ("agent_creative", "💡", "创造", "#a78bfa")),
    _u(None, ("sync", "🔗", "汇聚", "#64748b")),
    _u(None, ("debate", "⚔️", "辩论审查", "#fb7185")),
    _u("并行修正",
       ("revise_forward", "🔮", "前瞻修正", "#38bdf8"),
       ("revise_creative", "💡", "创造修正", "#a78bfa")),
    _u(None, ("aggregate", "🧩", "综合汇总", "#818cf8")),
    _u(None, ("final", "✨", "最终结论", "#34d399")),
]

CHAIN_FACTUAL = [
    _u(None, ("question", "💬", "提问", "#818cf8")),
    _u(None, ("coordinator", "🧭", "协调路由", "#22d3ee")),
    _u(None, ("agent_critical", "🔍", "批判分析", "#fbbf24")),
    _u(None, ("sync", "🔗", "汇聚", "#64748b")),
    _u(None, ("aggregate", "🧩", "综合汇总", "#818cf8")),
    _u(None, ("final", "✨", "最终结论", "#34d399")),
]

CHAIN_GREETING = [
    _u(None, ("question", "💬", "提问", "#818cf8")),
    _u(None, ("coordinator", "🧭", "协调路由", "#22d3ee")),
    _u(None, ("direct", "💬", "直接回答", "#34d399")),
    _u(None, ("final", "✨", "最终结论", "#34d399")),
]

CHAINS = {
    "simple_greeting": CHAIN_GREETING,
    "simple_factual": CHAIN_FACTUAL,
    "complex_reasoning": CHAIN_COMPLEX,
}

# LangGraph 节点名 → 流程图步骤 key
NODE_TO_STEP = {
    "coordinator": "coordinator",
    "direct_answer": "direct",
    "forward": "agent_forward",
    "critical": "agent_critical",
    "creative": "agent_creative",
    "sync_point": "sync",
    "debate_reviewer": "debate",
    "forward_reviser": "revise_forward",
    "creative_reviser": "revise_creative",
    "sync_point_2": "sync2",
    "aggregator": "aggregate",
}

STATUS_TEXT = {
    "coordinator": "协调器正在判断问题类型…",
    "agent_forward": "前瞻 Agent 正在推演长期影响…",
    "agent_critical": "批判 Agent 正在寻找逻辑漏洞…",
    "agent_creative": "创造 Agent 正在寻找跨领域类比…",
    "sync": "等待并行节点汇聚…",
    "debate": "批判 Agent 正在审查其他分析…",
    "revise_forward": "前瞻 Agent 正在根据质疑修正观点…",
    "revise_creative": "创造 Agent 正在根据质疑修正观点…",
    "aggregate": "汇总 Agent 正在综合所有观点…",
    "direct": "正在生成回答…",
}

EVENT_CARD = {
    "agent_forward": ("🔮", "前瞻 Agent", "#38bdf8", "forward"),
    "agent_critical": ("🔍", "批判 Agent", "#fbbf24", "critical"),
    "agent_creative": ("💡", "创造 Agent", "#a78bfa", "creative"),
    "debate": ("⚔️", "辩论 · 批判审查", "#fb7185", "debate_critique"),
    "revise_forward": ("🔄", "前瞻修正", "#38bdf8", "forward_revised"),
    "revise_creative": ("🔄", "创造修正", "#a78bfa", "creative_revised"),
    "aggregate": ("🧩", "综合汇总", "#818cf8", "final"),
    "direct": ("💬", "直接回答", "#34d399", "final"),
}

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="CognitiveProbe · 多智能体协作推理台",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

ss = st.session_state
for k, v in {
    "result": None, "steps": {}, "chain": None, "q_type": None,
    "meta": {}, "feed": [], "health_cache": None, "error": None,
}.items():
    ss.setdefault(k, v)

# ==================== 样式 ====================
st.markdown("""
<style>
/* ---------- 全局 ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1100px 520px at 50% -120px, rgba(99,102,241,.20), transparent 65%),
        radial-gradient(900px 420px at 100% 0%, rgba(34,211,238,.07), transparent 60%),
        #0b1120 !important;
    color: #e2e8f0;
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
#MainMenu, footer, [data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
.block-container { padding: 1.8rem 2.4rem 5rem !important; max-width: 1320px; }
a { color: #7dd3fc; }

/* ---------- 侧边栏 ---------- */
[data-testid="stSidebar"] {
    background: rgba(9,13,26,.92) !important;
    border-right: 1px solid rgba(148,163,184,.12);
}
[data-testid="stSidebar"] * { color: #cbd5e1; }
[data-testid="stSidebar"] hr { border-color: rgba(148,163,184,.14); margin: .9rem 0; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(148,163,184,.07);
    border: 1px solid rgba(148,163,184,.16);
    color: #cbd5e1; border-radius: 10px; text-align: left;
    transition: all .2s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    border-color: rgba(129,140,248,.7); color: #fff;
    background: rgba(129,140,248,.12);
}

/* ---------- 输入组件 ---------- */
.stTextArea textarea {
    background: rgba(148,163,184,.07) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(148,163,184,.22) !important;
    border-radius: 14px !important;
    font-size: 15px !important;
    line-height: 1.6 !important;
}
.stTextArea textarea:focus {
    border-color: rgba(129,140,248,.85) !important;
    box-shadow: 0 0 0 3px rgba(129,140,248,.18) !important;
}
.stButton > button[kind="primary"], [data-testid="stForm"] button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #22d3ee 120%) !important;
    border: none !important; color: #fff !important;
    font-weight: 700; letter-spacing: .05em;
    box-shadow: 0 4px 18px rgba(99,102,241,.4);
    transition: all .25s;
}
.stButton > button[kind="primary"]:hover, [data-testid="stForm"] button[kind="primary"]:hover {
    filter: brightness(1.12);
    box-shadow: 0 6px 24px rgba(99,102,241,.55);
}
[data-testid="stExpander"] {
    border: 1px solid rgba(148,163,184,.15) !important;
    border-radius: 12px !important;
    background: rgba(148,163,184,.04) !important;
}

/* ---------- 流程图 ---------- */
@keyframes pf-pulse {
    0%   { box-shadow: 0 0 0 0 var(--glow); }
    70%  { box-shadow: 0 0 0 13px transparent; }
    100% { box-shadow: 0 0 0 0 transparent; }
}
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: .25; } }

.pf-wrap {
    background: rgba(148,163,184,.045);
    border: 1px solid rgba(148,163,184,.13);
    border-radius: 18px;
    padding: 26px 22px 16px;
    overflow-x: auto;
}
.pf-row { display: flex; align-items: flex-start; min-width: 900px; }
.pf-node { display: flex; flex-direction: column; align-items: center; width: 88px; flex-shrink: 0; }
.pf-circle {
    width: 54px; height: 54px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 23px; position: relative;
    background: rgba(148,163,184,.09);
    border: 1.5px solid rgba(148,163,184,.28);
    transition: all .45s ease;
}
.pf-label { margin-top: 9px; font-size: 12px; color: #64748b; text-align: center; line-height: 1.35; }
.pf-dur { font-size: 10px; color: #7dd3fc; margin-top: 3px; font-variant-numeric: tabular-nums; }
.pf-badge {
    position: absolute; right: -5px; top: -5px; width: 19px; height: 19px;
    border-radius: 50%; background: #34d399; color: #052e16;
    font-size: 11px; font-weight: 800; display: none;
    align-items: center; justify-content: center;
}
.pf-tag {
    margin-top: 5px; font-size: 10px; padding: 2px 8px; border-radius: 99px;
    background: rgba(129,140,248,.15); color: #a5b4fc;
    border: 1px solid rgba(129,140,248,.4); white-space: nowrap;
}
.pf-node.running .pf-circle {
    border-color: var(--c); background: rgba(148,163,184,.05);
    animation: pf-pulse 1.5s ease-out infinite;
}
.pf-node.running .pf-label { color: #e2e8f0; }
.pf-node.done .pf-circle {
    border-color: var(--c);
    background: linear-gradient(145deg, rgba(148,163,184,.05), var(--soft));
    box-shadow: 0 0 16px var(--glow);
}
.pf-node.done .pf-circle .pf-badge { display: flex; }
.pf-node.done .pf-label { color: #f1f5f9; }
.pf-node.error .pf-circle { border-color: #f87171; box-shadow: 0 0 14px rgba(248,113,113,.5); }
.pf-node.error .pf-label { color: #fca5a5; }

.pf-arrow {
    flex: 1; min-width: 20px; height: 2px; margin: 26px 3px 0;
    background: rgba(148,163,184,.18); position: relative; border-radius: 2px;
}
.pf-arrow::after {
    content: ''; position: absolute; right: -1px; top: -3.5px;
    border-left: 7px solid rgba(148,163,184,.35);
    border-top: 4.5px solid transparent; border-bottom: 4.5px solid transparent;
}
.pf-arrow.lit {
    background: linear-gradient(90deg, #6366f1, #22d3ee);
    box-shadow: 0 0 9px rgba(99,102,241,.75);
}
.pf-arrow.lit::after { border-left-color: #22d3ee; }

.pf-group {
    flex-shrink: 0; border: 1px dashed rgba(148,163,184,.25);
    border-radius: 14px; padding: 12px 12px 8px; margin: 0 4px;
    display: flex; flex-direction: column; gap: 7px;
    transition: all .45s ease; background: rgba(148,163,184,.03);
}
.pf-group.running { border-color: rgba(129,140,248,.65); border-style: solid; }
.pf-group.done { border-color: rgba(52,211,153,.5); border-style: solid; }
.pf-chip {
    display: flex; align-items: center; gap: 8px;
    padding: 5px 11px 5px 6px; border-radius: 10px;
    border: 1px solid rgba(148,163,184,.2);
    background: rgba(148,163,184,.07); transition: all .4s ease;
}
.pf-chip .ico {
    width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; background: rgba(148,163,184,.13);
    border: 1px solid transparent;
}
.pf-chip .t { font-size: 12px; color: #94a3b8; white-space: nowrap; }
.pf-chip .d { font-size: 10px; color: #7dd3fc; margin-left: auto; padding-left: 8px; }
.pf-chip.running { border-color: var(--c); animation: pf-pulse 1.5s ease-out infinite; }
.pf-chip.running .t { color: #e2e8f0; }
.pf-chip.running .ico { border-color: var(--c); }
.pf-chip.done { border-color: var(--c); background: var(--soft); }
.pf-chip.done .t { color: #f1f5f9; }
.pf-chip.done .ico { background: var(--soft); box-shadow: 0 0 9px var(--glow); }
.pf-group-label {
    font-size: 10.5px; color: #64748b; text-align: center; letter-spacing: .12em;
}

/* 进度条与状态行 */
.pf-status { display: flex; align-items: center; gap: 10px; margin-top: 14px; min-height: 22px; }
.pf-status .dot {
    width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0;
    background: #64748b; animation: blink 1.2s infinite;
}
.pf-status.ok .dot { background: #34d399; animation: none; }
.pf-status.err .dot { background: #f87171; animation: none; }
.pf-status .txt { font-size: 13px; color: #94a3b8; }
.pf-status.ok .txt { color: #6ee7b7; }
.pf-status.err .txt { color: #fca5a5; }
.pf-bar { height: 4px; border-radius: 99px; background: rgba(148,163,184,.12); margin-top: 12px; overflow: hidden; }
.pf-bar > div {
    height: 100%; border-radius: 99px;
    background: linear-gradient(90deg, #6366f1, #22d3ee, #34d399);
    transition: width .5s ease;
}

/* ---------- 页面组件 ---------- */
.hero { display: flex; align-items: center; gap: 18px; margin-bottom: 6px; }
.hero .logo {
    width: 58px; height: 58px; border-radius: 16px; font-size: 30px;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, rgba(99,102,241,.25), rgba(34,211,238,.18));
    border: 1px solid rgba(129,140,248,.45);
    box-shadow: 0 0 28px rgba(99,102,241,.3);
}
.hero h1 {
    font-size: 30px; font-weight: 800; margin: 0; letter-spacing: .02em;
    background: linear-gradient(100deg, #e0e7ff 0%, #a5b4fc 40%, #67e8f9 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero .sub { font-size: 13px; color: #64748b; margin-top: 3px; }
.pills { display: flex; gap: 8px; margin: 14px 0 18px; flex-wrap: wrap; }
.pill {
    font-size: 12px; padding: 4px 12px; border-radius: 99px;
    border: 1px solid rgba(148,163,184,.22); color: #94a3b8;
    background: rgba(148,163,184,.06);
}
.pill b { font-weight: 600; }
.pill.on { border-color: rgba(52,211,153,.5); color: #6ee7b7; }
.pill.warn { border-color: rgba(251,191,36,.5); color: #fcd34d; }
.pill.off { border-color: rgba(248,113,113,.5); color: #fca5a5; }

.panel {
    background: rgba(148,163,184,.045);
    border: 1px solid rgba(148,163,184,.13);
    border-radius: 18px; padding: 20px 22px; margin-bottom: 18px;
}
.sec-title {
    display: flex; align-items: center; gap: 10px;
    font-size: 17px; font-weight: 700; color: #e2e8f0;
    margin: 26px 0 14px;
}
.sec-title::before {
    content: ''; width: 4px; height: 18px; border-radius: 4px;
    background: linear-gradient(180deg, #818cf8, #22d3ee);
}

.stat-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 4px; }
.stat {
    flex: 1; min-width: 150px; border-radius: 14px; padding: 14px 18px;
    background: rgba(148,163,184,.05); border: 1px solid rgba(148,163,184,.14);
}
.stat .v { font-size: 19px; font-weight: 700; color: #e2e8f0; }
.stat .k { font-size: 11.5px; color: #64748b; margin-top: 3px; letter-spacing: .05em; }

.out-card {
    border-radius: 14px; padding: 16px 18px; margin-bottom: 12px;
    background: rgba(148,163,184,.045);
    border: 1px solid rgba(148,163,184,.13);
    border-left: 3px solid var(--c);
    font-size: 13.5px; line-height: 1.85; color: #cbd5e1;
}
.out-card .head {
    display: flex; align-items: center; gap: 8px; margin-bottom: 9px;
    font-size: 13px; font-weight: 700; color: var(--c);
}
.out-card .head .d { margin-left: auto; font-size: 11px; color: #64748b; font-weight: 400; }
.out-card .body { color: #cbd5e1; word-break: break-word; }

.final-card {
    border-radius: 16px; padding: 22px 24px;
    background: linear-gradient(135deg, rgba(52,211,153,.09), rgba(34,211,238,.05));
    border: 1px solid rgba(52,211,153,.4);
    font-size: 15.5px; line-height: 1.95; color: #d1fae5;
    box-shadow: 0 0 34px rgba(52,211,153,.09);
}
.final-card .head {
    display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
    font-size: 13px; font-weight: 700; color: #6ee7b7; letter-spacing: .1em;
}
.err-panel {
    border-radius: 14px; padding: 18px 20px;
    background: rgba(248,113,113,.08); border: 1px solid rgba(248,113,113,.4);
    color: #fecaca; font-size: 13.5px; line-height: 1.8;
}
.hint {
    border: 1px dashed rgba(148,163,184,.25); border-radius: 18px;
    padding: 42px 20px; text-align: center; color: #64748b;
}
.hint .big { font-size: 40px; margin-bottom: 12px; }
.hint .t { font-size: 15px; color: #94a3b8; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)


# ==================== 工具函数 ====================
def esc(text) -> str:
    """转义 HTML 并保留换行"""
    return html.escape(str(text)).replace("\n", "<br>")


def fmt_dur(d: float) -> str:
    if d is None or d < 0.4:
        return ""
    return f"{d:.1f}s"


def get_health(api: str):
    """带 30s 缓存的服务状态探测"""
    cache = ss.get("health_cache")
    if cache and cache["api"] == api and time.time() - cache["t"] < 30:
        return cache["data"]
    try:
        r = requests.get(f"{api}/health", timeout=8)
        data = r.json() if r.ok else None
    except Exception:
        data = None
    ss["health_cache"] = {"t": time.time(), "api": api, "data": data}
    return data


def out_card(icon: str, title: str, color: str, body: str, dur: float = None) -> str:
    d = f'<span class="d">{fmt_dur(dur)}</span>' if dur else ""
    return (
        f'<div class="out-card" style="--c:{color}">'
        f'<div class="head">{icon} {esc(title)}{d}</div>'
        f'<div class="body">{esc(body)}</div></div>'
    )


# ==================== 流程图渲染 ====================
def init_chain(question_type: str | None):
    """按问题类型初始化链路步骤状态，第一步（提问）直接完成，协调器进入执行"""
    chain = CHAINS.get(question_type, CHAIN_COMPLEX)
    steps = {}
    for unit in chain:
        for key, _, _, _ in unit["nodes"]:
            steps[key] = {"state": "pending", "dur": None}
    steps["question"]["state"] = "done"
    steps["coordinator"] = {"state": "running", "dur": None, "since": time.time()}
    return chain, steps


def rebuild_chain(steps, q_type: str):
    """协调器给出问题类型后，切换到对应的链路（保留协调器耗时）"""
    chain, new_steps = init_chain(q_type)
    new_steps["question"] = {"state": "done", "dur": None}
    new_steps["coordinator"] = {
        "state": "done",
        "dur": steps.get("coordinator", {}).get("dur"),
    }
    activate_next(chain, new_steps, "coordinator")
    return chain, new_steps


def _unit_done(unit, steps) -> bool:
    return all(steps[n[0]]["state"] == "done" for n in unit["nodes"])


def activate_next(chain, steps, done_key: str):
    """某节点完成后：若所属单元全部完成，则点亮下一个单元"""
    idx = next(i for i, u in enumerate(chain) if any(n[0] == done_key for n in u["nodes"]))
    if not _unit_done(chain[idx], steps):
        return
    if idx + 1 < len(chain):
        for key, _, _, _ in chain[idx + 1]["nodes"]:
            if steps[key]["state"] == "pending":
                steps[key] = {"state": "running", "dur": None, "since": time.time()}


def mark_done(chain, steps, key: str, duration: float):
    steps[key] = {"state": "done", "dur": duration if duration and duration > 0 else None}
    activate_next(chain, steps, key)


def render_pipeline(chain, steps, q_type=None, status="", state="run", progress=None) -> str:
    """生成整张链路图的 HTML"""
    parts = ['<div class="pf-wrap"><div class="pf-row">']
    n_units = len(chain)

    for i, unit in enumerate(chain):
        if i > 0:
            lit = " lit" if _unit_done(chain[i - 1], steps) else ""
            parts.append(f'<div class="pf-arrow{lit}"></div>')

        unit_done = _unit_done(unit, steps)
        if len(unit["nodes"]) > 1:
            chips = []
            for key, icon, label, color in unit["nodes"]:
                s = steps[key]
                cls = s["state"]
                dur = f'<span class="d">{fmt_dur(s.get("dur"))}</span>' if cls == "done" else ""
                soft = _soft(color)
                glow = _glow(color)
                chips.append(
                    f'<div class="pf-chip {cls}" style="--c:{color};--glow:{glow};--soft:{soft}">'
                    f'<span class="ico">{icon}</span><span class="t">{esc(label)}</span>{dur}</div>'
                )
            gcls = "done" if unit_done else (
                "running" if any(steps[n[0]]["state"] == "running" for n in unit["nodes"]) else ""
            )
            parts.append(
                f'<div class="pf-group {gcls}">{"".join(chips)}'
                f'<div class="pf-group-label">{esc(unit["label"] or "")}</div></div>'
            )
        else:
            key, icon, label, color = unit["nodes"][0]
            s = steps[key]
            soft, glow = _soft(color), _glow(color)
            badge = '<span class="pf-badge">✓</span>'
            dur = f'<div class="pf-dur">{fmt_dur(s.get("dur"))}</div>' if s["state"] == "done" else ""
            tag = ""
            if key == "coordinator" and s["state"] == "done" and q_type:
                te, tt, tc = TYPE_META.get(q_type, ("❓", q_type, "#94a3b8"))
                tag = f'<div class="pf-tag" style="color:{tc};border-color:{tc}55;background:{tc}18">{te} {esc(tt)}</div>'
            parts.append(
                f'<div class="pf-node {s["state"]}" style="--c:{color};--glow:{glow};--soft:{soft}">'
                f'<div class="pf-circle">{icon}{badge}</div>'
                f'<div class="pf-label">{esc(label)}</div>{tag}{dur}</div>'
            )

    parts.append("</div>")

    # 状态行 + 进度条
    cls = {"run": "", "ok": " ok", "err": " err"}.get(state, "")
    done_units = sum(1 for u in chain if _unit_done(u, steps))
    pct = progress if progress is not None else int(done_units / n_units * 100)
    parts.append(
        f'<div class="pf-status{cls}"><span class="dot"></span><span class="txt">{esc(status)}</span></div>'
        f'<div class="pf-bar"><div style="width:{pct}%"></div></div></div>'
    )
    return "".join(parts)


def _soft(color: str) -> str:
    return color + "22"


def _glow(color: str) -> str:
    return color + "59"


def status_text_for(chain, steps) -> str:
    for unit in chain:
        for key, _, label, _ in unit["nodes"]:
            if steps[key]["state"] == "running":
                return STATUS_TEXT.get(key, f"{label} 执行中…")
    return ""


# ==================== 页面区块 ====================
def render_hero(api: str):
    h = get_health(api)
    pills = []
    if h is None:
        pills.append('<span class="pill off">● API 离线</span>')
    else:
        pills.append('<span class="pill on">● API 在线</span>')
        if h.get("mock_llm"):
            pills.append('<span class="pill warn">🧪 Mock 模式</span>')
        elif h.get("model_loaded"):
            pills.append('<span class="pill on">🧠 模型已加载</span>')
        else:
            pills.append('<span class="pill">🧠 模型未加载</span>')
        if h.get("loaded_adapters"):
            n = len(h["loaded_adapters"])
            pills.append(f'<span class="pill">🎯 LoRA × {n}</span>')
        pills.append(
            '<span class="pill on">💾 数据库正常</span>' if h.get("db")
            else '<span class="pill off">💾 数据库离线</span>'
        )

    st.markdown(
        f'<div class="hero"><div class="logo">🧠</div><div>'
        f'<h1>CognitiveProbe 推理控制台</h1>'
        f'<div class="sub">基于 LoRA 认知注入的 Multi-Agent 协作推理系统 · 前瞻 / 批判 / 创造 三视角辩论共识</div>'
        f'</div></div><div class="pills">{"".join(pills)}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ 服务配置")
        api = st.text_input("API 地址", value=ss.get("api", DEFAULT_API), key="api_input")
        if api != ss.get("api"):
            ss["api"] = api
            ss["health_cache"] = None

        st.markdown("---")
        st.markdown("### 💡 示例问题")
        for label, q in EXAMPLES:
            if st.button(label, key=f"ex_{label}", use_container_width=True):
                ss["question_input"] = q
                st.rerun()

        st.markdown("---")
        st.markdown("### 🕘 历史记录")
        try:
            r = requests.get(f"{ss['api']}/tasks", params={"limit": 8}, timeout=4)
            tasks = r.json().get("tasks", []) if r.ok else []
        except Exception:
            tasks = []

        if not tasks:
            st.caption("暂无记录（需要数据库在线）")
        for t in tasks:
            icon = {"done": "✅", "failed": "❌", "pending": "⏳"}.get(t["status"], "•")
            q_short = t["question"][:22] + ("…" if len(t["question"]) > 22 else "")
            if st.button(f"{icon} #{t['id']} {q_short}", key=f"hist_{t['id']}", use_container_width=True):
                load_history(t["id"])
    return ss.get("api", DEFAULT_API)


def load_history(task_id: int):
    """点击历史记录：取回完整结果并展示"""
    try:
        r = requests.get(f"{ss['api']}/tasks/{task_id}", timeout=6)
        data = r.json() if r.ok else None
    except Exception:
        data = None
    if not data:
        st.toast(f"任务 {task_id} 读取失败", icon="⚠️")
        return
    result = data.get("result")
    if not result:
        st.toast("该任务没有保存推理结果", icon="ℹ️")
        return
    q_type = result.get("question_type", "complex_reasoning")
    chain, steps = init_chain(q_type)
    # 历史回放：整条链路直接点亮
    for unit in chain:
        for key, *_ in unit["nodes"]:
            steps[key] = {"state": "done", "dur": None}
    ss["chain"], ss["steps"], ss["q_type"] = chain, steps, q_type
    ss["result"] = result
    ss["meta"] = {"task_id": data["id"], "elapsed": None, "replay": True}
    ss["feed"] = []
    ss["error"] = None
    st.rerun()


def render_results(result: dict, meta: dict):
    """完整结果区（指标 + 三视角 + 辩论 + 结论）"""
    q_type = result.get("question_type", "unknown")
    icon, tname, tcolor = TYPE_META.get(q_type, ("❓", q_type, "#94a3b8"))
    elapsed = meta.get("elapsed")
    n_debate = 1 if result.get("debate_critique") else 0

    stats = f"""
    <div class="stat-row">
      <div class="stat"><div class="v">{icon} {esc(tname)}</div><div class="k">问题类型</div></div>
      <div class="stat"><div class="v">{f"{elapsed:.1f} s" if elapsed else "—"}</div><div class="k">推理耗时</div></div>
      <div class="stat"><div class="v">{"3 并行 + 辩论" if q_type == "complex_reasoning" else ("1 Agent" if q_type == "simple_factual" else "直答")}</div><div class="k">协作方式</div></div>
      <div class="stat"><div class="v">{n_debate} 轮</div><div class="k">辩论修正</div></div>
    </div>"""
    st.markdown(stats, unsafe_allow_html=True)

    st.markdown('<div class="sec-title">三视角分析</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    cards = [
        ("🔮", "前瞻 Agent · 因果推演", "#38bdf8", result.get("forward")),
        ("🔍", "批判 Agent · 逻辑审查", "#fbbf24", result.get("critical")),
        ("💡", "创造 Agent · 跨域类比", "#a78bfa", result.get("creative")),
    ]
    for col, (icon_, title, color, text) in zip((c1, c2, c3), cards):
        with col:
            body = text if text else "（该路径未启用此 Agent）"
            st.markdown(
                f'<div class="out-card" style="--c:{color}">'
                f'<div class="head">{icon_} {esc(title)}</div><div class="body">{esc(body)}</div></div>',
                unsafe_allow_html=True,
            )

    if result.get("debate_critique"):
        st.markdown('<div class="sec-title">辩论 · 批判审查</div>', unsafe_allow_html=True)
        st.markdown(out_card("⚔️", "批判 Agent 的质疑", "#fb7185", result["debate_critique"]),
                    unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if result.get("forward_revised"):
                st.markdown(out_card("🔄", "前瞻 · 修正后", "#38bdf8", result["forward_revised"]),
                            unsafe_allow_html=True)
        with c2:
            if result.get("creative_revised"):
                st.markdown(out_card("🔄", "创造 · 修正后", "#a78bfa", result["creative_revised"]),
                            unsafe_allow_html=True)

    st.markdown('<div class="sec-title">最终结论</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="final-card"><div class="head">✨ CONSENSUS · 共识结论</div>'
        f'{esc(result.get("final") or result.get("answer") or "（无输出）")}</div>',
        unsafe_allow_html=True,
    )

    with st.expander("📄 查看原始 JSON"):
        st.json(result)


def render_empty():
    st.markdown(
        '<div class="hint"><div class="big">🛰️</div>'
        '<div class="t">输入一个问题，观察三个 Agent 如何协作</div>'
        '<div>协调路由 → 三视角并行分析 → 辩论审查 → 观点修正 → 综合共识</div></div>',
        unsafe_allow_html=True,
    )


def render_error(msg: str):
    st.markdown(
        f'<div class="err-panel"><b>❌ 推理请求失败</b><br>{esc(msg)}<br>'
        f'<span style="color:#94a3b8">请确认 API 服务已启动：'
        f'<code>uvicorn src.main:app --host 127.0.0.1 --port 8000</code></span></div>',
        unsafe_allow_html=True,
    )


# ==================== 流式推理 ====================
def run_stream(question: str):
    api = ss.get("api", DEFAULT_API)

    # 初始链路：类型未知，先展示完整复杂链路
    chain, steps = init_chain(None)
    ss["chain"], ss["steps"], ss["q_type"] = chain, steps, None
    ss["result"], ss["error"], ss["feed"], ss["meta"] = None, None, [], {}

    pipeline_ph = st.empty()
    feed_ph = st.empty()
    pipeline_ph.markdown(
        render_pipeline(chain, steps, status="正在连接推理服务…"), unsafe_allow_html=True
    )

    start = time.time()
    try:
        resp = requests.post(
            f"{api}/reason/stream", json={"question": question},
            stream=True, timeout=(5, 1800),
        )
        resp.raise_for_status()
    except Exception as e:
        ss["error"] = str(e)
        pipeline_ph.markdown(
            render_pipeline(chain, steps, status=f"连接失败：{e}", state="err", progress=0),
            unsafe_allow_html=True,
        )
        render_error(str(e))
        return

    error_msg = None
    try:
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            evt = json.loads(raw)
            kind = evt.get("event")

            if kind == "start":
                ss["meta"]["task_id"] = evt.get("task_id")

            elif kind == "node":
                node = evt.get("node", "")
                ts = evt.get("ts", time.time())
                key = NODE_TO_STEP.get(node)
                if key and key in steps:
                    prev = steps[key]
                    dur = ts - prev["since"] if prev.get("since") else None
                    mark_done(chain, steps, key, dur)
                    pipeline_ph.markdown(
                        render_pipeline(chain, steps, ss["q_type"], status_text_for(chain, steps)),
                        unsafe_allow_html=True,
                    )
                # 节点产出文本 → 实时追加卡片
                data = evt.get("data") or {}
                if node == "coordinator":
                    new_type = data.get("question_type")
                    if new_type and new_type != ss["q_type"]:
                        ss["q_type"] = new_type
                        # 类型确定 → 切换到该类型对应的链路
                        chain, steps = rebuild_chain(steps, new_type)
                        ss["chain"], ss["steps"] = chain, steps
                    pipeline_ph.markdown(
                        render_pipeline(chain, steps, ss["q_type"], status_text_for(chain, steps)),
                        unsafe_allow_html=True,
                    )
                if key in EVENT_CARD:
                    icon, title, color, field = EVENT_CARD[key]
                    text = data.get(field)
                    if text:
                        ss["feed"].append((icon, title, color, text, steps[key].get("dur")))
                        feed_ph.markdown(
                            '<div class="sec-title">实时输出</div>' + "".join(
                                out_card(i_, t_, c_, b_, d_) for i_, t_, c_, b_, d_ in ss["feed"]
                            ),
                            unsafe_allow_html=True,
                        )
                time.sleep(0.25)   # 轻微停顿，让点亮动画可感知（真实推理下无感）

            elif kind == "end":
                ss["result"] = evt.get("data") or {}
                break

            elif kind == "error":
                error_msg = evt.get("message", "未知错误")
                break
    finally:
        resp.close()

    elapsed = time.time() - start

    if error_msg:
        ss["error"] = error_msg
        for key in steps:
            if steps[key]["state"] == "running":
                steps[key]["state"] = "error"
        pipeline_ph.markdown(
            render_pipeline(chain, steps, ss["q_type"], status=f"推理出错：{error_msg}", state="err"),
            unsafe_allow_html=True,
        )
        render_error(error_msg)
        return

    if ss["result"] is None:
        return

    # 全部点亮
    for key in steps:
        if steps[key]["state"] in ("running", "pending"):
            steps[key] = {"state": "done", "dur": None}
    ss["chain"], ss["steps"], ss["meta"] = chain, steps, {"elapsed": elapsed, **ss["meta"]}
    pipeline_ph.markdown(
        render_pipeline(chain, steps, ss["q_type"], status=f"推理完成，耗时 {elapsed:.1f} 秒", state="ok", progress=100),
        unsafe_allow_html=True,
    )
    feed_ph.empty()
    render_results(ss["result"], ss["meta"])


def render_cached():
    """rerun 时按 session 状态重绘（保留上次结果 / 流程图）"""
    chain, steps = ss["chain"], ss["steps"]
    if chain and steps:
        st.markdown(
            render_pipeline(chain, steps, ss["q_type"],
                            status="推理完成" if ss.get("result") else "推理中断",
                            state="ok" if ss.get("result") else "err",
                            progress=100 if ss.get("result") else None),
            unsafe_allow_html=True,
        )
    if ss.get("error") and not ss.get("result"):
        render_error(ss["error"])
    if ss.get("result"):
        render_results(ss["result"], ss.get("meta", {}))


# ==================== 主流程 ====================
api = render_sidebar()
render_hero(api)

# 输入区用 st.form：提交时原子性地取当前文本，避免"点了按钮但文本还没同步"的问题
with st.form("question_form"):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        question = st.text_area(
            "请输入问题", key="question_input", height=110, label_visibility="collapsed",
            placeholder="输入一个需要多角度分析的问题，例如：全面分析中国实行四天制工作日的影响…",
        )
    with col_btn:
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
        analyze = st.form_submit_button("🔍 开始分析", type="primary", use_container_width=True)

if analyze:
    if not question.strip():
        st.markdown(
            '<div class="err-panel">⚠️ 请先输入问题</div>', unsafe_allow_html=True
        )
    else:
        run_stream(question.strip())
elif ss.get("result") or ss.get("chain"):
    render_cached()
else:
    render_empty()
