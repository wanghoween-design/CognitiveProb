from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.types import Send
import json
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
    """Coordinator：判断问题类型，决定调用哪些 Agent（JSON 输出 + 容错版）"""
    question = state["question"]

    # 1. 快速规则兜底：极简问候直接拦截，节省一次 LLM 调用
    bare_greetings = {"你好", "嗨", "早上好", "晚上好", "你是谁", "谢谢", "再见"}
    if question.strip() in bare_greetings:
        return {"question_type": "simple_greeting"}

    # 2. 用强约束 prompt 让 LLM 只输出 JSON
    prompt = f"""请判断以下问题属于哪种类型。你必须**只输出一个 JSON 对象**，不要添加任何解释或多余文字。

JSON 格式：{{"type": 数字}}

数字定义：
1 = simple_greeting    （仅问候，无实质问题）
2 = simple_factual     （有唯一明确答案的客观事实，无需分析）
3 = complex_reasoning  （需要分析、讨论、评价、建议，含“该不该”“利弊”“比较”等）

问题：{question}

JSON："""

    result = call_llm(prompt).strip()

    # 3. 解析 JSON（带多层容错）
    q_type_num = 3   # 默认复杂问题，确保安全
    try:
        # 尝试找到第一个 { 和最后一个 }，截取 JSON 段
        start = result.find('{')
        end = result.rfind('}')
        if start != -1 and end != -1:
            json_str = result[start:end+1]
            data = json.loads(json_str)
            q_type_num = int(data.get("type", 3))
    except Exception:
        # JSON 解析失败时，回退到取最后一个出现的独立数字 1/2/3
        numbers = re.findall(r'\b([123])\b', result)
        if numbers:
            q_type_num = int(numbers[-1])

    # 限制范围
    if q_type_num not in (1, 2, 3):
        q_type_num = 3

    type_map = {1: "simple_greeting", 2: "simple_factual", 3: "complex_reasoning"}
    return {"question_type": type_map[q_type_num]}


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
    answer = call_llm(prompt, use_lora="critical")
    return {"critical_answer": answer}


def creative_agent(state: AgentState) -> dict:
    """创造推理：跨领域类比"""
    question = state["question"]
    prompt = f"""你是一个创造性推理专家。请跳出常规思维，用跨领域类比来回答。

问题：{question}

请用其他领域的案例来类比，用中文给出创新视角的回答。虽然是按照其他领域的类比，但是最后的落脚点一定要回归到问题本身，字数限制在500字以内。"""
    answer = call_llm(prompt, use_lora="creative")
    return {"creative_answer": answer}


def aggregator(state: AgentState) -> dict:
    """综合 Agent 的回答，生成最终总结"""
    # 优先用修正后的回答，没有则用原始回答
    forward = state.get("forward_revised") or state.get("forward_answer", "")
    critical = state.get("critical_answer", "")
    creative = state.get("creative_revised") or state.get("creative_answer", "")

    prompt = f"""请综合以下三个分析，写一个简洁的最终结论。

原始问题：{state["question"]}

前瞻分析（提取关键点）：{forward[:400]}

批判分析（提取关键点）：{critical[:400]}

创造分析（提取关键点）：{creative[:400]}

要求：
1. 只输出一段话，不超过 200 字
2. 不要用"###"标题或编号
3. 直接给出结论，不要说"综合分析"、"总结如下"等引导语
4. 提取三个分析的共识，给出最终判断

最终结论："""
    final = call_llm(prompt)
    return {"final_answer": final}



# ====== 辩论-共识协议 ======

def debate_reviewer(state: AgentState) -> dict:
    """辩论 Round 1：批判 Agent 审视前瞻和创造的分析，提出质疑"""
    forward = state.get("forward_answer", "")
    creative = state.get("creative_answer", "")

    prompt = f"""你是一个批判性审查专家。请审视以下两个分析，找出逻辑漏洞。

原始问题：{state["question"]}

前瞻分析（摘要）：{forward[:400]}

创造分析（摘要）：{creative[:400]}

请指出：
1. 哪些结论缺乏证据支持
2. 哪些推理存在逻辑漏洞
3. 哪些假设可能不成立
用中文回答，200-300字。"""
    critique = call_llm(prompt, use_lora="critical")
    return {"debate_critique": critique}


def forward_reviser(state: AgentState) -> dict:
    """辩论 Round 2：前瞻 Agent 根据批判质疑修正自己的观点"""
    original = state.get("forward_answer", "")
    critique = state.get("debate_critique", "")

    prompt = f"""你是一个前瞻性推理专家。请根据批判质疑修正你的分析。

原始问题：{state["question"]}

你之前的分析（摘要）：{original[:300]}

批判质疑（关键点）：{critique[:300]}

请修正分析，保留正确的部分，修正错误的部分，用中文回答，200-400字。"""
    revised = call_llm(prompt, use_lora="forward")
    return {"forward_revised": revised}


def creative_reviser(state: AgentState) -> dict:
    """辩论 Round 2：创造 Agent 根据批判质疑修正自己的观点"""
    original = state.get("creative_answer", "")
    critique = state.get("debate_critique", "")

    prompt = f"""你是一个创造性推理专家。请根据批判质疑修正你的分析。

原始问题：{state["question"]}

你之前的分析（摘要）：{original[:300]}

批判质疑（关键点）：{critique[:300]}

请修正分析，保留创新视角，修正不合理部分，用中文回答，200-400字。"""
    revised = call_llm(prompt, use_lora="creative")
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
