from fastapi import APIRouter

from app.preview import preview

router = APIRouter()


@router.get("/api/samples/{sample}/orders")
def orders(sample: str):
    return preview(sample)["orders"]
