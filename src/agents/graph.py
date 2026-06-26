from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.types import Send
import re

from src.config import config
from src.agents.lora_inference import generate_lora, generate_base

class AgentState(TypedDict):
    question: str
    question_type: str           # coordinator 判断的问题类型
    forward_answer: str
    critical_answer: str
    creative_answer: str
    debate_critique: str         # 辩论 Round 1：批判 Agent 的质疑
    forward_revised: str         # 辩论 Round 2：前瞻 Agent 修正后的回答
    creative_revised: str        # 辩论 Round 2：创造 Agent 修正后的回答
    final_answer: str


def call_llm(prompt: str, use_lora: str = None) -> str:
    """调用模型生成回答

    Args:
        prompt: 提示词
        use_lora: None = 基座模型（无 LoRA）
                  "forward" = 基座 + forward LoRA（前瞻推理）
                  "critical" / "creative" = 后续训练完成后启用
    """
    try:
        if use_lora:
            return generate_lora(prompt, use_lora)
        else:
            return generate_base(prompt)
    except Exception as e:
        return f"[模型调用失败: {e}]"


def coordinator(state: AgentState) -> dict:
    """Coordinator：判断问题类型，决定调用哪些 Agent"""
    question = state["question"]
    prompt = f"""你是一个问题分类专家。请判断以下问题属于哪种类型，只输出类型编号，不要输出其他内容。

问题：{question}

类型编号：
1. simple_greeting — 简单问候（如"你好"、"你是谁"、"早上好"）
2. simple_factual — 简单事实问题（如"地球到月球多远"、"Python是什么"）
3. complex_reasoning — 复杂推理问题（需要多角度分析，如"如果太阳消失了会怎样"、"该不该实行四天工作制"）

只输出数字 1、2 或 3。"""
    result = call_llm(prompt).strip()

    # 提取数字
    match = re.search(r"[123]", result)
    question_type = match.group() if match else "3"  # 默认复杂问题

    type_map = {
        "1": "simple_greeting",
        "2": "simple_factual",
        "3": "complex_reasoning"
    }
    q_type = type_map.get(question_type, "complex_reasoning")

    return {"question_type": q_type}


def dispatcher(state: AgentState) -> list[Send]:
    """根据问题类型分发任务，复杂问题用 Send 并行执行多个 Agent"""
    q_type = state["question_type"]

    if q_type == "simple_greeting":
        return [Send("direct_answer", state)]

    elif q_type == "simple_factual":
        # 简单事实：只用批判 Agent
        return [Send("critical", state)]

    else:
        # 复杂推理：三个 Agent 同时并行执行
        return [
            Send("forward", state),
            Send("critical", state),
            Send("creative", state),
        ]


def direct_answer(state: AgentState) -> dict:
    """简单问候的直接回答"""
    answer = call_llm(f"请用一句简短友好的话回答：{state['question']}")
    return {"final_answer": answer}


def forward_agent(state: AgentState) -> dict:
    """前瞻推理，预测长期后果"""
    question = state["question"]
    prompt = f"""你是一个前瞻性推理专家。请预测以下问题的长期影响和连锁反应。
问题：{question}
请从短期、中期、长期三个维度分析，用中文给出你的回答，字数限制在500字以内。"""
    answer = call_llm(prompt, use_lora="forward")
    return {"forward_answer": answer}


def critical_agent(state: AgentState) -> dict:
    """批判推理，寻找逻辑漏洞"""
    question = state['question']
    prompt = f"""你是一个批判性推理专家。请找出以下问题中的逻辑漏洞和潜在错误。

问题：{question}

请质疑假设、找反例、识别逻辑谬误，用中文给出你的分析，字数限制在500字以内。"""
    answer = call_llm(prompt)
    return {"critical_answer": answer}


def creative_agent(state: AgentState) -> dict:
    """创造推理：跨领域类比"""
    question = state["question"]
    prompt = f"""你是一个创造性推理专家。请跳出常规思维，用跨领域类比来回答。

问题：{question}

请用其他领域的案例来类比，用中文给出创新视角的回答。虽然是按照其他领域的类比，但是最后的落脚点一定要回归到问题本身，字数限制在500字以内。"""
    answer = call_llm(prompt)
    return {"creative_answer": answer}


def aggregator(state: AgentState) -> dict:
    """综合 Agent 的回答，生成最终总结"""
    # 优先用修正后的回答，没有则用原始回答
    forward = state.get("forward_revised") or state.get("forward_answer", "")
    critical = state.get("critical_answer", "")
    creative = state.get("creative_revised") or state.get("creative_answer", "")

    prompt = f"""你是一个综合分析师。请阅读以下分析，然后写出一个综合总结。

原始问题：{state["question"]}

--- 前瞻分析 ---
{forward}

--- 批判分析 ---
{critical}

--- 创造性分析 ---
{creative}

请根据以上分析，写一个综合总结，要求：
1. 提取最有价值的观点
2. 找出三个分析的共识点和分歧点
3. 给出你自己的最终判断
4. 控制在 500 字以内"""
    final = call_llm(prompt)
    return {"final_answer": final}



# ====== 辩论-共识协议 ======

def debate_reviewer(state: AgentState) -> dict:
    """辩论 Round 1：批判 Agent 审视前瞻和创造的分析，提出质疑"""
    forward = state.get("forward_answer", "")
    creative = state.get("creative_answer", "")

    prompt = f"""你是一个批判性审查专家。请审视以下两个分析，找出它们的逻辑漏洞、事实错误和不合理的假设。

原始问题：{state["question"]}

--- 前瞻分析 ---
{forward}

--- 创造性分析 ---
{creative}

请指出这两个分析中：
1. 哪些结论缺乏证据支持
2. 哪些推理存在逻辑漏洞
3. 哪些假设可能不成立
4. 用中文回答，控制在 300 字以内。"""
    critique = call_llm(prompt)
    return {"debate_critique": critique}


def forward_reviser(state: AgentState) -> dict:
    """辩论 Round 2：前瞻 Agent 根据批判质疑修正自己的观点"""
    original = state.get("forward_answer", "")
    critique = state.get("debate_critique", "")

    prompt = f"""你是一个前瞻性推理专家。你之前的分析受到了批判性审查，请根据质疑修正你的观点。

原始问题：{state["question"]}

--- 你之前的分析 ---
{original}

--- 批判质疑 ---
{critique}

请修正你的分析，保留正确的部分，修正错误的部分，用中文回答，控制在 500 字以内。"""
    revised = call_llm(prompt, use_lora="forward")
    return {"forward_revised": revised}


def creative_reviser(state: AgentState) -> dict:
    """辩论 Round 2：创造 Agent 根据批判质疑修正自己的观点"""
    original = state.get("creative_answer", "")
    critique = state.get("debate_critique", "")

    prompt = f"""你是一个创造性推理专家。你之前的分析受到了批判性审查，请根据质疑修正你的观点。

原始问题：{state["question"]}

--- 你之前的分析 ---
{original}

--- 批判质疑 ---
{critique}

请修正你的分析，保留创新视角，但修正其中不合理的部分，用中文回答，控制在 500 字以内。"""
    revised = call_llm(prompt)
    return {"creative_revised": revised}


def sync_point(state: AgentState) -> dict:
    """汇聚节点：等待所有并行 Agent 完成，统一路由"""
    return {}


def route_after_sync(state: AgentState) -> str:
    """汇聚后路由：简单事实直接汇总，复杂推理进入辩论"""
    if state["question_type"] == "simple_factual":
        return "aggregator"
    return "debate_reviewer"


# 构建图
graph = StateGraph(AgentState)

# 添加节点
graph.add_node("coordinator", coordinator)
graph.add_node("direct_answer", direct_answer)
graph.add_node("forward", forward_agent)
graph.add_node("critical", critical_agent)
graph.add_node("creative", creative_agent)
graph.add_node("sync_point", sync_point)
graph.add_node("sync_point_2", sync_point)
graph.add_node("aggregator", aggregator)
graph.add_node("debate_reviewer", debate_reviewer)
graph.add_node("forward_reviser", forward_reviser)
graph.add_node("creative_reviser", creative_reviser)

# 设置入口为 coordinator
graph.set_entry_point("coordinator")

# coordinator → dispatcher（用 Send 并行分发）
graph.add_conditional_edges("coordinator", dispatcher)

# 三个 Agent 完成后 → 汇聚节点（等待所有并行任务完成）
graph.add_edge("forward", "sync_point")
graph.add_edge("critical", "sync_point")
graph.add_edge("creative", "sync_point")

# 汇聚后统一路由
graph.add_conditional_edges("sync_point", route_after_sync)

# 辩论 Round 1：批判审查
# debate_reviewer 完成后，前瞻和创造同时修正（并行）
graph.add_conditional_edges(
    "debate_reviewer",
    lambda s: [Send("forward_reviser", s), Send("creative_reviser", s)]
)

# 辩论 Round 2：修正完成后 → 汇聚 → 汇总
graph.add_edge("forward_reviser", "sync_point_2")
graph.add_edge("creative_reviser", "sync_point_2")
graph.add_edge("sync_point_2", "aggregator")

# 直接回答 → 结束
graph.add_edge("direct_answer", END)
graph.add_edge("aggregator", END)

# 编译
app = graph.compile()
