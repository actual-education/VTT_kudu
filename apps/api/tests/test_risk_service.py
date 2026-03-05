import pytest
from dataclasses import dataclass, field
from typing import Optional
from app.services.risk_service import RiskService, REASON_EQUATION_UNREAD, REASON_DIAGRAM_UNDESCRIBED, REASON_VISUAL_TEXT_UNMENTIONED, REASON_CHART_UNDESCRIBED


@dataclass
class FakeSegment:
    video_id: str = "test"
    start_time: float = 0.0
    end_time: float = 5.0
    transcript_text: Optional[str] = ""
    ocr_text: Optional[str] = None
    visual_description: Optional[str] = None
    has_text: bool = False
    has_diagram: bool = False
    has_equation: bool = False
    ai_suggestion: Optional[str] = None
    risk_level: Optional[str] = None
    risk_reason: Optional[str] = None


def make_segment(**kwargs) -> FakeSegment:
    return FakeSegment(**kwargs)


class TestRiskService:
    def setup_method(self):
        self.service = RiskService()

    def test_no_visual_content_is_low(self):
        seg = make_segment(transcript_text="just talking here")
        result = self.service.assess_segment(seg)
        assert result.level == "low"
        assert result.reason is None

    def test_equation_not_read_is_high(self):
        seg = make_segment(
            has_equation=True,
            ocr_text="E = mc^2",
            transcript_text="let me show you this formula",
        )
        result = self.service.assess_segment(seg)
        assert result.level == "high"
        assert result.reason == REASON_EQUATION_UNREAD

    def test_equation_read_aloud_is_not_high(self):
        seg = make_segment(
            has_equation=True,
            ocr_text="E = mc^2",
            transcript_text="energy equals mass times the speed of light squared E equals mc squared",
        )
        result = self.service.assess_segment(seg)
        # "mc" and "squared" overlap — should have coverage
        assert result.level != "high" or result.reason != REASON_EQUATION_UNREAD

    def test_diagram_undescribed_is_high(self):
        seg = make_segment(
            has_diagram=True,
            transcript_text="now look at this",
            visual_description="diagram showing vector addition",
        )
        result = self.service.assess_segment(seg)
        assert result.level == "high"
        assert result.reason == REASON_DIAGRAM_UNDESCRIBED

    def test_diagram_described_is_not_high(self):
        seg = make_segment(
            has_diagram=True,
            transcript_text="this diagram shows the vectors pointing in opposite directions",
            visual_description="diagram showing vector addition",
        )
        result = self.service.assess_segment(seg)
        assert result.level != "high" or result.reason != REASON_DIAGRAM_UNDESCRIBED

    def test_diagram_described_by_ai_suggestion_is_not_high(self):
        seg = make_segment(
            has_diagram=True,
            transcript_text="now look at this",
            ai_suggestion="The diagram shows vectors pointing in opposite directions.",
            visual_description="diagram showing vector addition",
        )
        result = self.service.assess_segment(seg)
        assert result.level != "high" or result.reason != REASON_DIAGRAM_UNDESCRIBED

    def test_chart_undescribed_is_high(self):
        seg = make_segment(
            has_text=True,
            ocr_text="Performance Results",
            visual_description="bar chart comparing algorithm performance",
            transcript_text="as you can see on the screen",
        )
        result = self.service.assess_segment(seg)
        assert result.level == "high"
        assert result.reason == REASON_CHART_UNDESCRIBED

    def test_visual_text_unmentioned_is_medium(self):
        seg = make_segment(
            has_text=True,
            ocr_text="Algorithm Complexity O(n^3)",
            transcript_text="let me show you something interesting",
        )
        result = self.service.assess_segment(seg)
        assert result.level == "medium"
        assert result.reason == REASON_VISUAL_TEXT_UNMENTIONED

    def test_visual_text_mentioned_is_low(self):
        seg = make_segment(
            has_text=True,
            ocr_text="Algorithm Complexity",
            transcript_text="the algorithm complexity is shown here on the board",
        )
        result = self.service.assess_segment(seg)
        assert result.level == "low"

    def test_equation_read_in_ai_suggestion_reduces_high_risk(self):
        seg = make_segment(
            has_equation=True,
            ocr_text="E = mc^2",
            transcript_text="let me show you this formula",
            ai_suggestion="On screen equation reads E equals mc squared.",
        )
        result = self.service.assess_segment(seg)
        assert result.level != "high" or result.reason != REASON_EQUATION_UNREAD

    def test_text_coverage_helper(self):
        assert self.service._text_coverage("hello world", "hello there world", 0.5)
        assert not self.service._text_coverage("hello world foo bar", "goodbye", 0.3)
        assert self.service._text_coverage("", "anything", 0.5)
