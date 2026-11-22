from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.errors import DomainError
from app.modules.calendars.intervals import intersect, merge
from app.modules.orders.contract import Key, Minute

Windows = Annotated[list[tuple[Minute, Minute]], Field(max_length=60)]


class Technician(BaseModel):
    name: Key
    role: Key
    windows: Windows


class Hold(BaseModel):
    id: Key
    type: Annotated[str, Field(pattern="^(stage|tech)$")]
    resource: Key
    start: Minute
    end: Minute


class Calendar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: date
    venue: Windows
    stages: Annotated[dict[Key, Windows], Field(max_length=30)]
    technicians: Annotated[dict[Key, Technician], Field(max_length=50)]
    holds: Annotated[list[Hold], Field(max_length=150)] = []


def load(raw):
    try:
        calendar = Calendar.model_validate(raw).model_dump(mode="json")
        groups = [calendar["venue"], *calendar["stages"].values(),
                  *(tech["windows"] for tech in calendar["technicians"].values())]
        if any(start >= end for windows in groups for start, end in windows):
            raise ValueError("反向窗口")
    except (ValidationError, ValueError) as exc:
        raise DomainError("BAD_CALENDAR", "日历字段或时段无效") from exc
    venue = merge(calendar["venue"])
    calendar["venue"] = venue
    calendar["effective_stages"] = {key: intersect(value, venue) for key, value in calendar["stages"].items()}
    calendar["effective_tech"] = {key: intersect(tech["windows"], venue)
                                  for key, tech in calendar["technicians"].items()}
    return calendar


def choices(calendar, role):
    return sorted(key for key, tech in calendar["technicians"].items() if tech["role"] == role)
