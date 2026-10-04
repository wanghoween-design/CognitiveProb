from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.lora_inference import generate_base
from src.models.crud import (
    create_task,
    get_task,
    delete_task,
    change_task,
    finish_task,
    list_tasks,
)

router = APIRouter()


class QuestionIn(BaseModel):
    """统一的问题入参（JSON body），同时兼容旧的 query 参数方式"""
    question: str


def _pick(raw: Optional[QuestionIn], fallback: Optional[str]) -> str:
    q = (raw.question if raw else None) or fallback
    if not q or not q.strip():
        raise HTTPException(status_code=422, detail="question 不能为空")
    return q.strip()


@router.post("/tasks")
def create(raw: Optional[QuestionIn] = None, question: Optional[str] = None):
    """创建任务。推荐 JSON body：{"question": "..."}"""
    try:
        task = create_task(question=_pick(raw, question))
    except Exception:
        raise HTTPException(status_code=503, detail="数据库不可用，请先启动 PostgreSQL（docker compose up -d）")
    return {"id": task.id, "question": task.question, "status": task.status}


@router.get("/tasks")
def read_list(limit: int = 20):
    """最近的任务列表（前端历史记录用）。数据库不可用时返回空列表"""
    try:
        return {"tasks": list_tasks(limit=limit)}
    except Exception:
        return {"tasks": []}


@router.get("/tasks/{task_id}")
def read(task_id: int):
    try:
        task = get_task(task_id)
    except Exception:
        raise HTTPException(status_code=503, detail="数据库不可用")
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return {
        "id": task.id,
        "question": task.question,
        "status": task.status,
        "result": task.result,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.delete("/tasks/{task_id}")
def delete(task_id: int):
    try:
        success = delete_task(task_id)
    except Exception:
        raise HTTPException(status_code=503, detail="数据库不可用")
    if not success:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return {"message": "deleted"}


@router.put("/tasks/{task_id}")
def update(task_id: int, raw: Optional[QuestionIn] = None, question: Optional[str] = None):
    try:
        task = change_task(task_id, _pick(raw, question))
    except Exception:
        raise HTTPException(status_code=503, detail="数据库不可用")
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return {"id": task.id, "question": task.question, "status": task.status}


@router.post("/ask")
def ask(raw: Optional[QuestionIn] = None, question: Optional[str] = None):
    """单轮端到端问答：本地基座模型直接回答，结果存库"""
    q = _pick(raw, question)
    task_id = None
    try:
        task_id = create_task(question=q).id
    except Exception:
        pass  # 数据库不可用时照常回答，只是不存历史

    answer = generate_base(q)
    if task_id is not None:
        finish_task(task_id, status="done", result={"answer": answer})

    return {"id": task_id, "question": q, "answer": answer}
