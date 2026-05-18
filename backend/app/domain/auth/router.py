from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "auth", "status": "scaffolded"}
