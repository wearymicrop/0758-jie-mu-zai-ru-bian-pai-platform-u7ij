from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.errors import DomainError
from app.modules.orders.contract import Key, Minute

EventKey = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class ClosureEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: EventKey
    stage: Key
    start: Minute
    end: Minute
    as_of: Optional[Minute] = None
    backup_stage: Optional[Key] = None


def parse_event(raw):
    try:
        event = ClosureEvent.model_validate(raw).model_dump()
    except Exception as exc:  # pydantic ValidationError 与类型错误统一归域错误
        raise DomainError("BAD_CLOSURE", "停场事件字段或时段无效") from exc
    if event["start"] >= event["end"]:
        raise DomainError("BAD_CLOSURE", "停场结束须晚于开始")
    if event["as_of"] is None:
        event["as_of"] = event["start"]
    if not 0 <= event["as_of"] <= event["start"]:
        raise DomainError("BAD_CLOSURE", "巡检时刻须在当日且不晚于停场开始")
    return event


def validate_event(event, calendar):
    stage = event["stage"]
    if stage not in calendar["stages"]:
        raise DomainError("BAD_CLOSURE", f"停场工位未知：{stage}")
    windows = calendar["effective_stages"][stage]
    if not any(event["start"] < end and start < event["end"] for start, end in windows):
        raise DomainError("BAD_CLOSURE", "停场时段与工位营业窗口无交集")
    backup = event.get("backup_stage")
    if backup is not None:
        if backup not in calendar["stages"]:
            raise DomainError("BAD_CLOSURE", f"备用工位未知：{backup}")
        if backup == stage:
            raise DomainError("BAD_CLOSURE", "备用工位不能与封场工位相同")
    as_of = event.get("as_of", event["start"])
    if not 0 <= as_of <= event["start"]:
        raise DomainError("BAD_CLOSURE", "巡检时刻须在当日且不晚于停场开始")
    return event
