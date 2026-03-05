import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_compliance.db"

from app.database import engine, SessionLocal
from app.models.base import Base
from app.models import Video, Segment, FrameAnalysis, CaptionVersion
from app.services.compliance_service import compliance_service


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_compliance.db"):
        os.remove("test_compliance.db")


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def create_video(db, **kwargs):
    defaults = {"youtube_id": "test123", "title": "Test Video"}
    defaults.update(kwargs)
    v = Video(**defaults)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


class TestComplianceService:
    def test_no_segments_gives_high_score(self, db):
        video = create_video(db)
        breakdown = compliance_service.compute_score(video.id, db)
        # No segments = caption completeness low, but visual/manual/ocr = 100
        assert breakdown.total_segments == 0

    def test_all_low_risk_gives_high_visual_coverage(self, db):
        video = create_video(db)
        # Add a caption version
        cv = CaptionVersion(video_id=video.id, version_number=1, label="enhanced", vtt_content="WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello")
        db.add(cv)
        # Add segments with low risk and visual content
        for i in range(3):
            seg = Segment(
                video_id=video.id,
                start_time=i * 5.0,
                end_time=(i + 1) * 5.0,
                transcript_text="some text",
                has_text=True,
                risk_level="low",
                review_status="pending",
            )
            db.add(seg)
        db.commit()

        breakdown = compliance_service.compute_score(video.id, db)
        assert breakdown.visual_coverage == 100.0
        assert breakdown.low_risk_count == 3
        assert breakdown.high_risk_count == 0

    def test_high_risk_segments_lower_visual_coverage(self, db):
        video = create_video(db)
        cv = CaptionVersion(video_id=video.id, version_number=1, label="raw_auto", vtt_content="WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello")
        db.add(cv)
        # 2 high risk, 1 low risk — all have visual content
        for i, risk in enumerate(["high", "high", "low"]):
            seg = Segment(
                video_id=video.id,
                start_time=i * 5.0,
                end_time=(i + 1) * 5.0,
                transcript_text="text",
                has_text=True,
                risk_level=risk,
                review_status="pending",
            )
            db.add(seg)
        db.commit()

        breakdown = compliance_service.compute_score(video.id, db)
        assert breakdown.visual_coverage == pytest.approx(33.3, abs=0.1)
        assert breakdown.high_risk_count == 2

    def test_reviewed_segments_improve_manual_review(self, db):
        video = create_video(db)
        for i, status in enumerate(["approved", "approved", "pending"]):
            seg = Segment(
                video_id=video.id,
                start_time=i * 5.0,
                end_time=(i + 1) * 5.0,
                transcript_text="text",
                risk_level="low",
                review_status=status,
            )
            db.add(seg)
        db.commit()

        breakdown = compliance_service.compute_score(video.id, db)
        assert breakdown.manual_review == pytest.approx(66.7, abs=0.1)

    def test_model_confidence_score(self, db):
        video = create_video(db)
        for conf in [0.9, 0.8, 0.7]:
            fa = FrameAnalysis(
                video_id=video.id, timestamp=0.0, confidence=conf
            )
            db.add(fa)
        db.commit()

        breakdown = compliance_service.compute_score(video.id, db)
        assert breakdown.model_uncertainty == pytest.approx(80.0, abs=0.1)

    def test_overall_is_weighted_sum(self, db):
        video = create_video(db)
        cv = CaptionVersion(video_id=video.id, version_number=1, label="enhanced", vtt_content="WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello")
        db.add(cv)
        seg = Segment(
            video_id=video.id,
            start_time=0.0,
            end_time=5.0,
            transcript_text="text",
            has_text=True,
            risk_level="low",
            review_status="approved",
        )
        db.add(seg)
        fa = FrameAnalysis(video_id=video.id, timestamp=2.5, confidence=0.9, has_text=True, ocr_text="hello")
        db.add(fa)
        db.commit()

        breakdown = compliance_service.compute_score(video.id, db)
        expected = (
            breakdown.caption_completeness * 0.30
            + breakdown.visual_coverage * 0.30
            + breakdown.manual_review * 0.20
            + breakdown.model_uncertainty * 0.10
            + breakdown.ocr_reliability * 0.10
        )
        assert breakdown.overall_score == pytest.approx(round(expected, 1), abs=0.2)
