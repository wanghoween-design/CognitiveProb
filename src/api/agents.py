from fastapi import APIRouter
from src.agents.graph import app as agent_app
from src.agents.graph import AgentState

router = APIRouter()

@router.post("/reason")
def reason(question: str):
    # 运行 LangGraph 工作流
    result = agent_app.invoke({"question": question})
    response = {
        "question": question,
        "question_type": result.get("question_type", "unknown"),
        "final": result["final_answer"]
    }
    # 返回有内容的 Agent 原始分析
    if result.get("forward_answer"):
        response["forward"] = result["forward_answer"]
    if result.get("critical_answer"):
        response["critical"] = result["critical_answer"]
    if result.get("creative_answer"):
        response["creative"] = result["creative_answer"]
    # 返回辩论过程的中间结果（帮助理解系统行为）
    if result.get("debate_critique"):
        response["debate_critique"] = result["debate_critique"]
    if result.get("forward_revised"):
        response["forward_revised"] = result["forward_revised"]
    if result.get("creative_revised"):
        response["creative_revised"] = result["creative_revised"]
    return response
