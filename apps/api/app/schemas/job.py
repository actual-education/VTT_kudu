from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ScanRequest(BaseModel):
    video_id: str


class BatchScanRequest(BaseModel):
    video_ids: list[str]


class JobResponse(BaseModel):
    id: str
    video_id: str
    status: str
    current_step: Optional[str] = None
    progress: int
    error_message: Optional[str] = None
    result_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
