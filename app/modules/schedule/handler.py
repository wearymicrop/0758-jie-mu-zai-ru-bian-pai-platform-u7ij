from fastapi import APIRouter

from app.errors import DomainError
from app.preview import preview

router = APIRouter()


@router.get('/api/samples/{sample}/schedule')
def schedule(sample: str, job: str | None = None):
    result = preview(sample)['schedule']
    if job is None:
        return result
    for row in result['jobs']:
        if row['id'] == job:
            return row
    raise DomainError('ORDER_NOT_FOUND', '找不到该工序', 404)
