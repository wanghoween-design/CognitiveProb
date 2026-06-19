from fastapi import APIRouter
from src.models.crud import create_task, get_task, delete_task, change_task
import re
import ollama
from src.config import config

router = APIRouter()

@router.post("/tasks")
def create(questions:str):
    task = create_task(question=questions)
    return {"id": task.id}

@router.get("/tasks/{task_id}")
def read(task_id: int):
    task = get_task(task_id)
    if task is None:
        return {"error": "not found"}
    return {"id": task.id, "question":task.question, "status":task.status}

@router.delete("/tasks/{task_id}")
def delete(task_id: int):
    success = delete_task(task_id)
    if success:
        return {"message":"delete"}
    return {"error":"not found"}

@router.put("/tasks/{task_id}")
def update(task_id: int, question: str):
    task = change_task(task_id, question)
    if task is None:
        return {"error": "not found"}
    return {"id":task.id, "question": task.question, "status": task.status}

@router.post("/ask")
def ask(question: str):
    task = create_task(question=question)

    client = ollama.Client(host=config["ollama"]["base_url"])
    response = client.chat(
        model=config["model"]["base_model"],
        messages=[{"role": "user", "content": question}]
    )
    answer = response["message"]["content"]
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
    task.status = "done"
    from src.models.database import SessionLocal
    db = SessionLocal()
    db.merge(task)
    db.commit()
    db.close()

    return {"id": task.id, "question": task.question, "answer": answer}
         