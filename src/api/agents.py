import json
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.graph import app as agent_app
from src.models.crud import create_task, finish_task

router = APIRouter()


class QuestionIn(BaseModel):
    """统一的问题入参（JSON body），同时兼容旧的 query 参数方式"""
    question: str


def _pick(raw: Optional[QuestionIn], fallback: Optional[str]) -> str:
    q = (raw.question if raw else None) or fallback
    if not q or not q.strip():
        raise HTTPException(status_code=422, detail="question 不能为空")
    return q.strip()


def _build_response(result: dict, question: str, task_id) -> dict:
    """把 LangGraph 的最终 state 组装成 API 响应"""
    response = {
        "task_id": task_id,
        "question": question,
        "question_type": result.get("question_type", "unknown"),
    }
    # state 字段 → 响应字段的映射（只返回有内容的部分）
    field_map = {
        "forward": "forward_answer",
        "critical": "critical_answer",
        "creative": "creative_answer",
        "debate_critique": "debate_critique",
        "forward_revised": "forward_revised",
        "creative_revised": "creative_revised",
        "final": "final_answer",
    }
    for out_key, state_key in field_map.items():
        if result.get(state_key):
            response[out_key] = result[state_key]
    return response


def _create_task_safe(question: str):
    """数据库不可用时返回 None，推理照常进行（只是不留历史）"""
    try:
        return create_task(question=question).id
    except Exception:
        return None


@router.post("/reason")
def reason(raw: Optional[QuestionIn] = None, question: Optional[str] = None):
    """多 Agent 推理（一次性返回完整结果）"""
    q = _pick(raw, question)
    task_id = _create_task_safe(q)

    try:
        result = agent_app.invoke({"question": q})
    except Exception as e:
        if task_id is not None:
            finish_task(task_id, status="failed")
        raise HTTPException(status_code=500, detail=f"推理失败：{e}")

    response = _build_response(result, q, task_id)
    if task_id is not None:
        finish_task(task_id, status="done", result=response)
    return response


@router.post("/reason/stream")
def reason_stream(raw: Optional[QuestionIn] = None, question: Optional[str] = None):
    """多 Agent 推理（流式版）

    返回 NDJSON：每行一个 JSON 事件，前端据此实时点亮流程图。
    事件类型：
      {"event": "start", "task_id": ...}
      {"event": "node",  "node": "forward", "data": {...该节点的部分结果...}, "ts": ...}
      {"event": "end",   "data": {完整响应，结构与 /reason 相同}}
      {"event": "error", "message": "..."}
    """
    q = _pick(raw, question)
    task_id = _create_task_safe(q)

    def _line(payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=False) + "\n"

    def event_stream():
        yield _line({"event": "start", "task_id": task_id, "question": q})
        collected: dict = {}
        try:
            # stream_mode="updates"：每个节点完成时产出 {节点名: 该节点写入的 state 增量}
            for chunk in agent_app.stream({"question": q}, stream_mode="updates"):
                for node, update in chunk.items():
                    if not node or update is None or node == "__end__":
                        continue
                    collected.update(update)
                    clean = {k: v for k, v in update.items() if isinstance(v, str) and v}
                    yield _line({"event": "node", "node": node, "data": clean, "ts": time.time()})

            response = _build_response(collected, q, task_id)
            yield _line({"event": "end", "data": response})
            if task_id is not None:
                finish_task(task_id, status="done", result=response)
        except Exception as e:
            yield _line({"event": "error", "message": str(e)})
            if task_id is not None:
                finish_task(task_id, status="failed")

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
