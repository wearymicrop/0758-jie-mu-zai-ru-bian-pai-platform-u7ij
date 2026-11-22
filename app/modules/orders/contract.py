from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Key = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Minute = Annotated[int, Field(strict=True, ge=0, le=2880)]


class WorkOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Key
    show: Key
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    stage: Key
    role: Key
    duration: Annotated[int, Field(strict=True, gt=0, le=720)]
    reset: Annotated[int, Field(strict=True, ge=0, le=120)] = 0
    release: Minute = 0
    deadline: Minute
    priority: Annotated[int, Field(strict=True, ge=0, le=99)] = 5
    needs: Annotated[list[Key], Field(max_length=30)] = []
