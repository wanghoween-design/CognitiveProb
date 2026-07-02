"""
CognitiveProbe 前端界面
用法：streamlit run scripts/app.py
"""

import streamlit as st
import requests
import time

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="CognitiveProbe",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== 自定义样式 ====================
st.markdown("""
<style>
    /* 主标题样式 */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* 卡片样式 */
    .agent-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .debate-card {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 4px solid #ffc107;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .final-card {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #28a745;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* 指标卡片 */
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #667eea;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #666;
    }

    /* 侧边栏样式 */
    .sidebar .stRadio > div {
        flex-direction: column;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## ⚙️ 设置")
    api_url = st.text_input("API 地址", value="http://127.0.0.1:8000")

    st.markdown("---")
    st.markdown("## 📋 示例问题")

    examples = {
        "👶 未成年人保护": "部分欧洲国家已经限制16岁以下儿童禁止使用社交媒体，你认为我国该不该跟进，或者全面禁止未成年人使用社交媒体？",
        "⚖️ 死刑存废": "死刑是否应该废除？请从法律、伦理、社会效果多角度分析",
        "🤖 AI 利弊": "人工智能是弊大于利还是利大于弊？深度剖析这个问题",
        "📅 四天工作制": "全面分析中国实行四天制工作日的影响",
    }

    for label, question in examples.items():
        if st.button(label, key=label, use_container_width=True):
            st.session_state.question = question


# ==================== 主界面 ====================
st.markdown('<div class="main-title">🧠 CognitiveProbe</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">基于 LoRA 认知注入的 Multi-Agent 协作推理系统</div>', unsafe_allow_html=True)

# 输入区域
col_input, col_btn = st.columns([4, 1])
with col_input:
    question = st.text_area(
        "请输入问题：",
        value=st.session_state.get("question", ""),
        height=120,
        placeholder="输入一个需要多角度分析的问题...",
        label_visibility="collapsed",
    )
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_button = st.button("🔍 开始分析", type="primary", use_container_width=True)


# ==================== 分析结果 ====================
if analyze_button:
    if not question.strip():
        st.warning("⚠️ 请输入问题")
        st.stop()

    # 计时
    start_time = time.time()

    with st.spinner("🔄 三个 Agent 协作推理中，请稍候..."):
        try:
            response = requests.post(
                f"{api_url}/reason",
                params={"question": question},
                timeout=1800,
            )
            result = response.json()
        except requests.exceptions.ConnectionError:
            st.error("❌ 无法连接 API 服务，请先启动：`uvicorn src.main:app --host 127.0.0.1 --port 8000`")
            st.stop()
        except Exception as e:
            st.error(f"❌ 请求失败：{e}")
            st.stop()

    elapsed = time.time() - start_time

    # 指标概览
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    q_type = result.get("question_type", "unknown")
    type_map = {"simple_greeting": "👋 简单问候", "simple_factual": "📚 简单事实", "complex_reasoning": "🧩 复杂推理"}

    with col1:
        st.metric("问题类型", type_map.get(q_type, q_type))
    with col2:
        st.metric("推理耗时", f"{elapsed:.1f} 秒")
    with col3:
        st.metric("Agent 数量", "3" if q_type == "complex_reasoning" else "1")
    with col4:
        has_debate = bool(result.get("debate_critique"))
        st.metric("辩论轮次", "1 轮" if has_debate else "无")

    # 三个 Agent 分析
    st.markdown("---")
    st.markdown("## 📊 三个 Agent 的分析")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🔮 前瞻分析")
        forward = result.get("forward", "无")
        st.markdown(f'<div class="agent-card">{forward}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("### 🔍 批判分析")
        critical = result.get("critical", "无")
        st.markdown(f'<div class="agent-card">{critical}</div>', unsafe_allow_html=True)

    with col3:
        st.markdown("### 💡 创造分析")
        creative = result.get("creative", "无")
        st.markdown(f'<div class="agent-card">{creative}</div>', unsafe_allow_html=True)

    # 辩论过程
    if result.get("debate_critique"):
        st.markdown("---")
        st.markdown("## ⚔️ 辩论过程")

        st.markdown("### 🔎 批判审查")
        st.markdown(f'<div class="debate-card">{result["debate_critique"]}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if result.get("forward_revised"):
                st.markdown("### 🔄 前瞻修正")
                st.markdown(f'<div class="agent-card">{result["forward_revised"]}</div>', unsafe_allow_html=True)
        with col2:
            if result.get("creative_revised"):
                st.markdown("### 🔄 创造修正")
                st.markdown(f'<div class="agent-card">{result["creative_revised"]}</div>', unsafe_allow_html=True)

    # 最终结论
    st.markdown("---")
    st.markdown("## 🎯 最终结论")
    final = result.get("final", "无最终结论")
    st.markdown(f'<div class="final-card">{final}</div>', unsafe_allow_html=True)

    # JSON 折叠
    with st.expander("📄 查看原始 JSON"):
        st.json(result)
