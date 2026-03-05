import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.video import Video
from app.models.segment import Segment
from app.models.frame_analysis import FrameAnalysis
from app.models.caption_version import CaptionVersion

logger = logging.getLogger(__name__)

# Weights for compliance score components
WEIGHT_CAPTION_COMPLETENESS = 0.30
WEIGHT_VISUAL_COVERAGE = 0.30
WEIGHT_MANUAL_REVIEW = 0.20
WEIGHT_MODEL_UNCERTAINTY = 0.10
WEIGHT_OCR_RELIABILITY = 0.10


@dataclass
class ComplianceBreakdown:
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


class ComplianceService:
    def compute_score(self, video_id: str, db: Session) -> ComplianceBreakdown:
        """Compute weighted compliance score for a video."""
        segments = (
            db.query(Segment)
            .filter(Segment.video_id == video_id)
            .all()
        )
        frame_analyses = (
            db.query(FrameAnalysis)
            .filter(FrameAnalysis.video_id == video_id)
            .all()
        )
        caption_versions = (
            db.query(CaptionVersion)
            .filter(CaptionVersion.video_id == video_id)
            .all()
        )

        total = len(segments) if segments else 1

        # Count risk levels
        high_risk = sum(1 for s in segments if s.risk_level == "high")
        med_risk = sum(1 for s in segments if s.risk_level == "medium")
        low_risk = sum(1 for s in segments if s.risk_level == "low")

        # 1. Caption completeness (30%): do captions exist and cover the video?
        caption_completeness = self._score_caption_completeness(segments, caption_versions)

        # 2. Visual coverage (30%): are visual elements described?
        visual_coverage = self._score_visual_coverage(segments)

        # 3. Manual review (20%): have segments been reviewed?
        manual_review = self._score_manual_review(segments)

        # 4. Model uncertainty (10%): how confident are frame analyses?
        model_uncertainty = self._score_model_confidence(frame_analyses)

        # 5. OCR reliability (10%): is OCR text present where expected?
        ocr_reliability = self._score_ocr_reliability(segments, frame_analyses)

        overall = (
            caption_completeness * WEIGHT_CAPTION_COMPLETENESS
            + visual_coverage * WEIGHT_VISUAL_COVERAGE
            + manual_review * WEIGHT_MANUAL_REVIEW
            + model_uncertainty * WEIGHT_MODEL_UNCERTAINTY
            + ocr_reliability * WEIGHT_OCR_RELIABILITY
        )

        # Update video record
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.compliance_score = round(overall, 1)
            db.commit()

        return ComplianceBreakdown(
            overall_score=round(overall, 1),
            caption_completeness=round(caption_completeness, 1),
            visual_coverage=round(visual_coverage, 1),
            manual_review=round(manual_review, 1),
            model_uncertainty=round(model_uncertainty, 1),
            ocr_reliability=round(ocr_reliability, 1),
            total_segments=len(segments),
            high_risk_count=high_risk,
            medium_risk_count=med_risk,
            low_risk_count=low_risk,
        )

    def _score_caption_completeness(self, segments: list[Segment], versions: list[CaptionVersion]) -> float:
        if not versions:
            return 0.0
        # Has captions at all = 50 points, enhanced = +25, segments with transcript = remaining
        score = 50.0
        if any(v.label in ("enhanced", "reviewed", "published") for v in versions):
            score += 25.0
        if segments:
            with_text = sum(1 for s in segments if s.transcript_text)
            score += 25.0 * (with_text / len(segments))
        return min(score, 100.0)

    def _score_visual_coverage(self, segments: list[Segment]) -> float:
        if not segments:
            return 100.0
        visual_segments = [s for s in segments if s.has_text or s.has_diagram or s.has_equation]
        if not visual_segments:
            return 100.0  # No visual content to describe
        # Score based on how many visual segments are low risk (well described)
        described = sum(1 for s in visual_segments if s.risk_level == "low")
        return (described / len(visual_segments)) * 100.0

    def _score_manual_review(self, segments: list[Segment]) -> float:
        if not segments:
            return 100.0
        reviewed = sum(1 for s in segments if s.review_status in ("approved", "edited"))
        return (reviewed / len(segments)) * 100.0

    def _score_model_confidence(self, frame_analyses: list[FrameAnalysis]) -> float:
        if not frame_analyses:
            return 100.0
        confidences = [fa.confidence for fa in frame_analyses if fa.confidence is not None]
        if not confidences:
            return 50.0
        avg = sum(confidences) / len(confidences)
        return min(avg * 100.0, 100.0)

    def _score_ocr_reliability(self, segments: list[Segment], frame_analyses: list[FrameAnalysis]) -> float:
        text_frames = [fa for fa in frame_analyses if fa.has_text]
        if not text_frames:
            return 100.0
        with_ocr = sum(1 for fa in text_frames if fa.ocr_text)
        return (with_ocr / len(text_frames)) * 100.0


compliance_service = ComplianceService()
