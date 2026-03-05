from pydantic import BaseModel


class ComplianceBreakdownResponse(BaseModel):
    overall_score: float
    caption_completeness: float
    visual_coverage: float
    manual_review: float
    model_uncertainty: float
    ocr_reliability: float
    total_segments: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class ComplianceReportResponse(BaseModel):
    video_id: str
    title: str
    overall_score: float
    caption_completeness: float
    visual_coverage: float
    manual_review: float
    model_uncertainty: float
    ocr_reliability: float
    total_segments: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    flags_count: int
    disclaimer: str
