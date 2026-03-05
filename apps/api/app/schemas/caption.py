from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CaptionVersionResponse(BaseModel):
    id: str
    video_id: str
    version_number: int
    label: str
    vtt_content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CaptionIngestRequest(BaseModel):
    content: str


class CaptionValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
