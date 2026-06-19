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
    # 只返回有内容的 Agent 结果
    if result.get("forward_answer"):
        response["forward"] = result["forward_answer"]
    if result.get("critical_answer"):
        response["critical"] = result["critical_answer"]
    if result.get("creative_answer"):
        response["creative"] = result["creative_answer"]
    return response
