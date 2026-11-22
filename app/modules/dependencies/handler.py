from fastapi import APIRouter

from app.preview import preview

router = APIRouter()


@router.get("/api/samples/{sample}/dependencies")
def dependencies(sample: str):
    return preview(sample)["dependencies"]
