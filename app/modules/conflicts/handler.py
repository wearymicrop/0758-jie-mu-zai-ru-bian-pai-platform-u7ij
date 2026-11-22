from fastapi import APIRouter

from app.preview import preview

router = APIRouter()


@router.get("/api/samples/{sample}/conflicts")
def conflicts(sample: str):
    return preview(sample)["conflicts"]
