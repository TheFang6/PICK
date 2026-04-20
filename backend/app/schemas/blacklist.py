import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BlacklistAddRequest(BaseModel):
    restaurant_id: uuid.UUID
    mode: str = "permanent"


class BlacklistResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    restaurant_id: uuid.UUID
    mode: str
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BlacklistListResponse(BaseModel):
    entries: list[BlacklistResponse]
