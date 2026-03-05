from pydantic import BaseModel
from typing import Optional


class SegmentResponse(BaseModel):
    id: str
    video_id: str
    start_time: float
    end_time: float
    transcript_text: Optional[str] = None
    ocr_text: Optional[str] = None
    visual_description: Optional[str] = None
    ai_suggestion: Optional[str] = None
    has_text: bool
    has_diagram: bool
    has_equation: bool
    risk_level: Optional[str] = None
    risk_reason: Optional[str] = None
    review_status: str

    model_config = {"from_attributes": True}


class SegmentUpdateRequest(BaseModel):
    review_status: Optional[str] = None
    transcript_text: Optional[str] = None
    ai_suggestion: Optional[str] = None
