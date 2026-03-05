from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class VideoImportRequest(BaseModel):
    url: str


class VideoResponse(BaseModel):
    id: str
    youtube_id: str
    title: str
    channel_title: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[str] = None
    compliance_score: Optional[float] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    videos: list[VideoResponse]
    total: int
