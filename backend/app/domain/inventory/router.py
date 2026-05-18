from fastapi import APIRouter

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "inventory", "status": "scaffolded"}
