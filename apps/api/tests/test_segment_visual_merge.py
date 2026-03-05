from app.models.segment import Segment
from app.pipeline.steps import _can_merge_segments, _text_similarity, _merge_text_lines


def _segment(**kwargs) -> Segment:
    defaults = {
        "video_id": "v1",
        "start_time": 0.0,
        "end_time": 1.0,
        "transcript_text": "",
        "ocr_text": None,
        "visual_description": None,
        "has_text": False,
        "has_diagram": False,
        "has_equation": False,
    }
    defaults.update(kwargs)
    return Segment(**defaults)


def test_text_similarity_identical_content_is_high():
    a = "Revenue chart for 2024 by quarter"
    b = "2024 quarter revenue chart"
    assert _text_similarity(a, b) >= 0.8


def test_can_merge_when_visual_context_stable():
    left = _segment(
        start_time=0.0,
        end_time=4.0,
        transcript_text="Intro",
        ocr_text="Quarterly revenue chart 2024",
        visual_description="Bar chart comparing four quarters",
        has_text=True,
        has_diagram=True,
    )
    right = _segment(
        start_time=4.2,
        end_time=8.0,
        transcript_text="More explanation",
        ocr_text="Revenue chart 2024 quarterly",
        visual_description="Bar chart comparing the four quarters",
        has_text=True,
        has_diagram=True,
    )

    assert _can_merge_segments(left, right)


def test_does_not_merge_when_visual_flags_change():
    left = _segment(
        start_time=0.0,
        end_time=4.0,
        ocr_text="Equation E=mc2",
        visual_description="Equation on slide",
        has_text=True,
        has_equation=True,
    )
    right = _segment(
        start_time=4.1,
        end_time=8.0,
        ocr_text="Architecture diagram",
        visual_description="Flow diagram with arrows",
        has_text=True,
        has_diagram=True,
        has_equation=False,
    )

    assert not _can_merge_segments(left, right)


def test_does_not_merge_when_visual_description_is_substantially_different():
    left = _segment(
        start_time=0.0,
        end_time=4.0,
        ocr_text="x = y + z",
        visual_description="Math equation on white background",
        has_text=True,
        has_equation=True,
    )
    right = _segment(
        start_time=4.2,
        end_time=8.0,
        ocr_text="Civil War timeline 1861-1865",
        visual_description="Historical timeline with dates",
        has_text=True,
        has_equation=True,
    )

    assert not _can_merge_segments(left, right)


def test_merge_text_lines_drops_shorter_near_duplicate_lines():
    merged = _merge_text_lines(
        "The left or right in our problem we're",
        "The left or right in our problem we're just dealing with the up and down",
    )
    assert merged == "The left or right in our problem we're just dealing with the up and down"
