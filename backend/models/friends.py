from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal
from uuid import UUID


class FriendShipResponse(BaseModel):
    id: int
    user_id: UUID
    friend_id: UUID
    status: Literal["pending", "accepted", "blocked", "none"]
    created_at: datetime


class FriendRequest(BaseModel):
    cognito_sub: UUID = Field(description="Cognito sub of the user to send the request to")


class FriendsProfile(BaseModel):
    cognito_sub: UUID
    username: str
    friendship_status: Literal["pending", "accepted", "blocked", "none"]
    friendship_created_at: datetime


class PeopleYouMayKnow(BaseModel):
    cognito_sub: UUID
    username: str
