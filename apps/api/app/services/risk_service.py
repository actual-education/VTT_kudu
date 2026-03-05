import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.segment import Segment
from app.models.video import Video

logger = logging.getLogger(__name__)

REASON_VISUAL_TEXT_UNMENTIONED = "VISUAL_TEXT_UNMENTIONED"
REASON_DIAGRAM_UNDESCRIBED = "DIAGRAM_UNDESCRIBED"
REASON_EQUATION_UNREAD = "EQUATION_UNREAD"
REASON_CHART_UNDESCRIBED = "CHART_UNDESCRIBED"
REASON_MODEL_UNCERTAIN = "MODEL_UNCERTAIN"


@dataclass
class RiskResult:
    level: str  # low, medium, high
    reason: str | None


class RiskService:
    def assess_segment(self, segment: Segment) -> RiskResult:
        """Compare transcript vs OCR/vision content and assign risk."""
        narration = self._combined_narration(segment)
        ocr_text = (segment.ocr_text or "").lower()
        description = (segment.visual_description or "").lower()

        # High risk: equation present but not read aloud
        if segment.has_equation:
            if not self._text_coverage(ocr_text, narration, threshold=0.4):
                return RiskResult("high", REASON_EQUATION_UNREAD)

        # High risk: diagram present but not described
        if segment.has_diagram:
            diagram_keywords = {"diagram", "chart", "graph", "figure", "arrow", "shows", "pointing"}
            if not any(kw in narration for kw in diagram_keywords):
                return RiskResult("high", REASON_DIAGRAM_UNDESCRIBED)

        # High risk: chart detected in visual description
        if any(kw in description for kw in ("chart", "bar chart", "pie chart", "graph", "plot")):
            chart_keywords = {"chart", "graph", "percent", "data", "comparison", "compare"}
            if not any(kw in narration for kw in chart_keywords):
                return RiskResult("high", REASON_CHART_UNDESCRIBED)

        # Medium risk: visual text not mentioned in transcript
        if segment.has_text and ocr_text:
            if not self._text_coverage(ocr_text, narration, threshold=0.3):
                return RiskResult("medium", REASON_VISUAL_TEXT_UNMENTIONED)

        # Medium risk: low model confidence on a frame with visual content
        if segment.has_text or segment.has_diagram or segment.has_equation:
            # We don't have direct confidence on segments, but flag if visual content
            # is present and nothing is mentioned
            if not ocr_text and not description:
                return RiskResult("medium", REASON_MODEL_UNCERTAIN)

        return RiskResult("low", None)

    def _text_coverage(self, source_text: str, target_text: str, threshold: float) -> bool:
        """Check if source_text words are sufficiently covered in target_text."""
        if not source_text:
            return True
        source_words = set(self._tokenize(source_text))
        target_words = set(self._tokenize(target_text))
        if not source_words:
            return True
        overlap = source_words & target_words
        return len(overlap) / len(source_words) >= threshold

    def _combined_narration(self, segment: Segment) -> str:
        transcript = (segment.transcript_text or "").strip()
        suggestion = str(getattr(segment, "ai_suggestion", "") or "").strip()
        return f"{transcript} {suggestion}".strip().lower()

    def _tokenize(self, text: str) -> list[str]:
        """Simple word tokenization, filtering short/common words."""
        import re
        words = re.findall(r"[a-z0-9]+", text.lower())
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "of", "and", "or", "for"}
        return [w for w in words if len(w) > 1 and w not in stop_words]

    def assess_video_segments(self, video_id: str, db: Session) -> list[Segment]:
        """Assess risk for all segments of a video."""
        segments = (
            db.query(Segment)
            .filter(Segment.video_id == video_id)
            .order_by(Segment.start_time)
            .all()
        )
        for seg in segments:
            result = self.assess_segment(seg)
            seg.risk_level = result.level
            seg.risk_reason = result.reason
        db.commit()
        return segments


risk_service = RiskService()
