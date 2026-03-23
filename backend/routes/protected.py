from fastapi import APIRouter, Depends
from backend.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/me")
def get_me(user=Depends(get_current_user)):
    return {
        "message": "You are authenticated ",
        "user": user
    }