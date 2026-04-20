import uuid
from datetime import date as date_type
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LogLunchRequest(BaseModel):
    restaurant_id: uuid.UUID
    attendees: list[uuid.UUID]
    lunch_date: Optional[date_type] = Field(None, alias="date")

    model_config = {"populate_by_name": True}


class LunchHistoryResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    date: date_type
    attendees: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class LunchHistoryListResponse(BaseModel):
    entries: list[LunchHistoryResponse]
