from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class Message_Create(BaseModel):
    reciever_id: UUID
    content: str


class Message_Response(BaseModel):
    id: int
    sender_id: UUID
    reciever_id: UUID
    content: str
    created_at: datetime
    is_read: bool

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}
