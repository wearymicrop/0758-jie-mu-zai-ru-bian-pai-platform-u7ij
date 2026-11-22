from fastapi import APIRouter

from app.preview import preview

router = APIRouter()


@router.get("/api/samples/{sample}/calendars")
def calendars(sample: str):
    return preview(sample)["calendars"]
