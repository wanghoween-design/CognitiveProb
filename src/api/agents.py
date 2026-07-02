from fastapi import APIRouter
from src.agents.graph import app as agent_app
from src.agents.graph import AgentState
from src.models.crud import create_task
from src.models.database import SessionLocal

router = APIRouter()

@router.post("/reason")
def reason(question: str):
    # 1. 创建任务，存入数据库
    task = create_task(question)

    try:
        # 2. 运行 LangGraph 工作流
        result = agent_app.invoke({"question": question})

        # 3. 构建响应
        response = {
            "task_id": task.id,
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

        # 返回辩论过程的中间结果
        if result.get("debate_critique"):
            response["debate_critique"] = result["debate_critique"]
        if result.get("forward_revised"):
            response["forward_revised"] = result["forward_revised"]
        if result.get("creative_revised"):
            response["creative_revised"] = result["creative_revised"]

        # 4. 更新任务状态为完成
        task.status = "done"
        db = SessionLocal()
        db.merge(task)
        db.commit()
        db.close()

        return response

    except Exception as e:
        # 推理失败时更新任务状态
        task.status = "failed"
        db = SessionLocal()
        db.merge(task)
        db.commit()
        db.close()
        raise e
