from fastapi import APIRouter
from src.config import config

router = APIRouter()

@router.get("/config")
def get_config():
    return config
