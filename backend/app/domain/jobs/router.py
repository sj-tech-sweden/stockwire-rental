from fastapi import APIRouter

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "jobs", "status": "scaffolded"}
