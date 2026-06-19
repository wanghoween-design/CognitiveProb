from typing import TypedDict
from langgraph.graph import StateGraph, END
import ollama
import re

from src.config import config

class AgentState(TypedDict):
    question: str
    question_type: str           # coordinator 判断的问题类型
    coordinator_answer: str      # 简单问题的直接回答
    forward_answer: str
    critical_answer: str
    creative_answer: str
    final_answer: str


def call_llm(prompt: str) -> str:
    """调用 Ollama 模型，返回清洗后的回答"""
    client = ollama.Client(host=config["ollama"]["base_url"])
    response = client.chat(
        model=config["model"]["base_model"],
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response["message"]["content"]
    
    return answer


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

    # 简单问候：直接回答
    if q_type == "simple_greeting":
        answer = call_llm(f"请用一句简短友好的话回答：{question}")
        return {"question_type": q_type, "coordinator_answer": answer}

    # 其他类型：交给后续 Agent 处理
    return {"question_type": q_type, "coordinator_answer": ""}


def route_by_type(state: AgentState) -> str:
    """根据问题类型决定路由"""
    q_type = state["question_type"]
    if q_type == "simple_greeting":
        return "direct_answer"
    elif q_type == "simple_factual":
        return "critical"          # 简单问题只用批判 Agent
    else:
        return "forward"           # 复杂问题三个 Agent 全用


def route_after_critical(state: AgentState) -> str:
    """critical 之后：简单事实去 aggregator，复杂推理去 creative"""
    if state["question_type"] == "simple_factual":
        return "aggregator"
    return "creative"


def direct_answer(state: AgentState) -> dict:
    """简单问题的直接回答（来自 coordinator）"""
    return {"final_answer": state["coordinator_answer"]}


def forward_agent(state: AgentState) -> dict:
    """前瞻推理，预测长期后果"""
    question = state["question"]
    prompt = f"""你是一个前瞻性推理专家。请预测以下问题的长期影响和连锁反应。
问题：{question}
请从短期、中期、长期三个维度分析，用中文给出你的回答，字数限制在500字以内。"""
    answer = call_llm(prompt)
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
    forward = state.get("forward_answer", "")
    critical = state.get("critical_answer", "")
    creative = state.get("creative_answer", "")

    # 根据有哪些 Agent 回答来构建 prompt
    sections = ""
    if forward:
        sections += f"\n--- 前瞻分析 ---\n{forward}\n"
    if critical:
        sections += f"\n--- 批判分析 ---\n{critical}\n"
    if creative:
        sections += f"\n--- 创造性分析 ---\n{creative}\n"

    prompt = f"""你是一个综合分析师。请阅读以下分析，然后写出一个综合总结。

原始问题：{state["question"]}
{sections}

请根据以上分析，写一个综合总结，要求：
1. 提取最有价值的观点
2. 如果有多个分析，找出共识点和分歧点
3. 给出你自己的最终判断
4. 控制在 500 字以内"""
    final = call_llm(prompt)
    return {"final_answer": final}


# 构建图
graph = StateGraph(AgentState)

# 添加节点
graph.add_node("coordinator", coordinator)
graph.add_node("direct_answer", direct_answer)
graph.add_node("forward", forward_agent)
graph.add_node("critical", critical_agent)
graph.add_node("creative", creative_agent)
graph.add_node("aggregator", aggregator)

# 设置入口为 coordinator
graph.set_entry_point("coordinator")

# coordinator 之后的条件路由
graph.add_conditional_edges(
    "coordinator",
    route_by_type,
    {
        "direct_answer": "direct_answer",   # 简单问候 → 直接回答
        "critical": "critical",             # 简单事实 → 批判 Agent
        "forward": "forward",               # 复杂推理 → 前瞻 Agent
    }
)

# 简单问候 → 直接回答 → 结束
graph.add_edge("direct_answer", END)

# 复杂推理：前瞻 → 批判
graph.add_edge("forward", "critical")

# 批判之后：根据问题类型路由
graph.add_conditional_edges(
    "critical",
    route_after_critical,
    {
        "creative": "creative",             # 复杂推理 → 创造 Agent
        "aggregator": "aggregator",         # 简单事实 → 直接汇总
    }
)

# 创造 → 汇总 → 结束
graph.add_edge("creative", "aggregator")
graph.add_edge("aggregator", END)

# 编译
app = graph.compile()
