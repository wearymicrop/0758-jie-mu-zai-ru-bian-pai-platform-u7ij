from time import perf_counter

from app.errors import DomainError
from app.pipeline import process
from app.store import fetch_recovery, save_recovery
from app.modules.recovery.event import parse_event
from app.modules.recovery.manifest import recovery_manifest
from app.modules.recovery.planner import plan_recovery


def build_recovery(source, raw_event):
    """纯计算：校验事件并在原批次结果上生成恢复单，不触碰存储。"""
    event = parse_event(raw_event)
    result = process(source)
    recovery = plan_recovery(result, event)
    return event, result, recovery


def create_recovery(source, raw_event):
    started = perf_counter()
    event, result, recovery = build_recovery(source, raw_event)
    digest = recovery_manifest(source, event)
    recovery_id = digest["digest"]
    try:
        _, _, record = fetch_recovery(recovery_id)
    except DomainError as exc:
        if exc.code != "RECOVERY_NOT_FOUND":
            raise
    else:
        return {**record, "reused": True}
    record = {"id": recovery_id, "manifest": digest, "closure": event,
              "elapsed_ms": round((perf_counter() - started) * 100, 2),
              "result": recovery, "baseline": {"reconcile": result["reconcile"]}}
    return save_recovery(source, event, record)


def rerun_recovery(recovery_id):
    source, event, original = fetch_recovery(recovery_id)
    if recovery_manifest(source, event) != original["manifest"]:
        raise DomainError("RUN_VERSION_CHANGED", "原批次与当前规则版本不一致", 409)
    _, _, recovery = build_recovery(source, event)
    if recovery != original["result"]:
        raise DomainError("RUN_DRIFT", "复算结果与原始恢复单不一致", 409)
    return {**original, "reused": True}
