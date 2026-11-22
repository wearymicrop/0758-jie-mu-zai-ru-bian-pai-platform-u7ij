from fastapi import APIRouter, Response

from app.errors import DomainError
from app.manifest import canonical
from app.sources import choose_source
from app.store import fetch_recovery
from app.modules.recovery.archive import build_recovery, create_recovery, rerun_recovery
from app.modules.recovery.checklist import build_recovery_checklist

router = APIRouter()


def _select(payload):
    if "closure" not in payload or not isinstance(payload["closure"], dict):
        raise DomainError("CHOOSE_SOURCE", "请提供停场事件 closure")
    event = payload["closure"]
    source_payload = {key: payload[key] for key in ("sample", "orders", "calendar") if key in payload}
    source, _ = choose_source(source_payload)
    return source, event


@router.post("/api/recoveries/preview")
def preview_recovery(payload: dict):
    source, event = _select(payload)
    parsed, result, recovery = build_recovery(source, event)
    return {"closure": parsed, "result": recovery,
            "dispatch": build_recovery_checklist(recovery, result["calendars"])}


@router.post("/api/recoveries")
def submit_recovery(payload: dict):
    source, event = _select(payload)
    return create_recovery(source, event)


@router.get("/api/recoveries/{recovery_id}")
def saved_recovery(recovery_id: str):
    return fetch_recovery(recovery_id)[2]


@router.post("/api/recoveries/{recovery_id}/rerun")
def verify_recovery(recovery_id: str):
    return rerun_recovery(recovery_id)


@router.get("/api/recoveries/{recovery_id}/export")
def export_recovery(recovery_id: str):
    _, _, record = fetch_recovery(recovery_id)
    return Response(canonical(record), media_type="application/json", headers={
        "Content-Disposition": f'attachment; filename="recovery-{recovery_id}.json"',
        "Cache-Control": "no-store",
    })
