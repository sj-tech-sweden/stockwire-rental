from fastapi import APIRouter

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "finance", "status": "scaffolded"}
