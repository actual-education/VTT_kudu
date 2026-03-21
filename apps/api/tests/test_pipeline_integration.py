import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_pipeline_integ.db"

from app.database import engine, SessionLocal
from app.models.base import Base
from app.models import Video, Job, Segment, FrameAnalysis, CaptionVersion
from app.services.youtube_service import youtube_service
from app.pipeline.steps import (
    step_fetch_metadata,
    step_download_captions,
    step_enhance_captions,
    step_extract_frames,
    step_analyze_frames_ocr,
    step_analyze_frames_vision,
    step_align_segments,
    step_score_risk,
    step_generate_descriptions,
    step_compute_compliance,
    step_finalize,
)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_pipeline_integ.db"):
        os.remove("test_pipeline_integ.db")


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def video(db):
    meta = youtube_service.get_video_metadata("https://youtube.com/watch?v=dQw4w9WgXcQ")
    v = Video(**meta)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


class TestFullPipeline:
    def test_full_pipeline_produces_segments_and_score(self, db, video):
        step_fetch_metadata(video, db)
        assert video.duration_seconds > 0

        step_download_captions(video, db)
        versions = db.query(CaptionVersion).filter(CaptionVersion.video_id == video.id).all()
        assert len(versions) == 1
        assert versions[0].label == "raw_auto"

        enhanced = step_enhance_captions(video, db)
        assert enhanced is not None
        assert enhanced.label == "enhanced"

        frames = step_extract_frames(video, db)
        assert len(frames) > 0

        analyses = step_analyze_frames_ocr(video, frames, db)
        assert len(analyses) == len(frames)
        fa_count = db.query(FrameAnalysis).filter(FrameAnalysis.video_id == video.id).count()
        assert fa_count == len(frames)

        step_analyze_frames_vision(video, frames, analyses, db)
        with_desc = db.query(FrameAnalysis).filter(
            FrameAnalysis.video_id == video.id,
            FrameAnalysis.description.isnot(None),
        ).count()
        assert with_desc > 0

        segments = step_align_segments(video, db)
        assert len(segments) > 0
        seg_count = db.query(Segment).filter(Segment.video_id == video.id).count()
        assert seg_count == len(segments)

        step_score_risk(video, segments, db)
        # Reload segments to get risk levels from DB
        segments = db.query(Segment).filter(Segment.video_id == video.id).all()
        risk_levels = {s.risk_level for s in segments}
        assert risk_levels.issubset({"low", "medium", "high"})

        step_generate_descriptions(video, segments, db)
        with_suggestions = [s for s in segments if s.ai_suggestion]
        assert len(with_suggestions) > 0

        # Should have created a new caption version with AI cues
        all_versions = db.query(CaptionVersion).filter(CaptionVersion.video_id == video.id).all()
        assert len(all_versions) >= 3  # raw_auto, enhanced, reviewed

        score = step_compute_compliance(video, segments, db)
        assert 0 <= score <= 100
        assert video.compliance_score is not None

        step_finalize(video, db)
        assert video.status == "scanned"

    def test_pipeline_creates_caption_versions_in_order(self, db, video):
        step_fetch_metadata(video, db)
        step_download_captions(video, db)
        step_enhance_captions(video, db)

        versions = (
            db.query(CaptionVersion)
            .filter(CaptionVersion.video_id == video.id)
            .order_by(CaptionVersion.version_number)
            .all()
        )
        assert versions[0].label == "raw_auto"
        assert versions[0].version_number == 1
        assert versions[1].label == "enhanced"
        assert versions[1].version_number == 2

    def test_segments_have_transcript_text(self, db, video):
        step_fetch_metadata(video, db)
        step_download_captions(video, db)
        step_enhance_captions(video, db)
        frames = step_extract_frames(video, db)
        analyses = step_analyze_frames_ocr(video, frames, db)
        step_analyze_frames_vision(video, frames, analyses, db)
        segments = step_align_segments(video, db)

        for seg in segments:
            assert seg.transcript_text is not None
            assert len(seg.transcript_text) > 0

    def test_high_risk_segments_get_ai_suggestions(self, db, video):
        step_fetch_metadata(video, db)
        step_download_captions(video, db)
        step_enhance_captions(video, db)
        frames = step_extract_frames(video, db)
        analyses = step_analyze_frames_ocr(video, frames, db)
        step_analyze_frames_vision(video, frames, analyses, db)
        segments = step_align_segments(video, db)
        step_score_risk(video, segments, db)
        step_generate_descriptions(video, segments, db)

        segments = db.query(Segment).filter(Segment.video_id == video.id).all()
        high_risk = [s for s in segments if s.risk_level == "high"]
        for seg in high_risk:
            if seg.ocr_text or seg.visual_description:
                assert seg.ai_suggestion is not None

    def test_vision_step_reports_incremental_progress(self, db, video, monkeypatch):
        frames = [
            {"timestamp": 0.0, "path": "/tmp/frame1.jpg"},
            {"timestamp": 10.0, "path": "/tmp/frame2.jpg"},
        ]
        analyses = [
            FrameAnalysis(video_id=video.id, timestamp=0.0),
            FrameAnalysis(video_id=video.id, timestamp=10.0),
        ]
        for analysis in analyses:
            db.add(analysis)
        db.commit()

        def fake_analyze_frame(frame_path: str, timestamp: float) -> dict:
            return {
                "has_text": True,
                "has_diagram": False,
                "has_equation": False,
                "likely_essential": True,
                "ocr_text": f"text at {timestamp}",
                "description": f"description at {timestamp}",
                "confidence": 0.9,
            }

        monkeypatch.setattr(
            "app.pipeline.steps.vision_service.analyze_frame",
            fake_analyze_frame,
        )

        progress_calls: list[tuple[int, int]] = []

        step_analyze_frames_vision(
            video,
            frames,
            analyses,
            db,
            progress_callback=lambda completed, total: progress_calls.append((completed, total)),
        )

        assert progress_calls == [(1, 2), (2, 2)]

    def test_generate_descriptions_uses_template_mode_for_large_batches(self, db, video):
        from app.services.description_service import description_service

        created_segments = []
        for index in range(35):
            seg = Segment(
                video_id=video.id,
                start_time=float(index),
                end_time=float(index + 1),
                transcript_text="lecture transcript",
                ocr_text=f"formula {index}",
                visual_description="diagram on screen",
                has_text=True,
                risk_level="high",
            )
            db.add(seg)
            created_segments.append(seg)
        db.commit()

        progress_calls: list[tuple[int, int]] = []
        updated = description_service.generate_for_video(
            video.id,
            db,
            progress_callback=lambda completed, total: progress_calls.append((completed, total)),
        )

        assert updated == 35
        assert progress_calls[0] == (1, 35)
        assert progress_calls[-1] == (35, 35)
        refreshed = db.query(Segment).filter(Segment.video_id == video.id).all()
        assert all(seg.ai_suggestion for seg in refreshed)


class TestPreUploadValidation:
    def test_blocks_with_unreviewed_high_risk(self, db, video):
        from app.routers.export import pre_upload_validation

        # Run pipeline
        step_fetch_metadata(video, db)
        step_download_captions(video, db)
        step_enhance_captions(video, db)
        frames = step_extract_frames(video, db)
        analyses = step_analyze_frames_ocr(video, frames, db)
        step_analyze_frames_vision(video, frames, analyses, db)
        segments = step_align_segments(video, db)
        step_score_risk(video, segments, db)

        # Check that validation blocks
        from unittest.mock import MagicMock
        mock_db = db  # use real DB session

        result = pre_upload_validation(video.id, mock_db)
        high_risk_pending = db.query(Segment).filter(
            Segment.video_id == video.id,
            Segment.risk_level == "high",
            Segment.review_status == "pending",
        ).count()

        if high_risk_pending > 0:
            assert result["ready"] is False
            assert any(i["severity"] == "critical" for i in result["issues"])

    def test_ready_after_all_reviewed(self, db, video):
        step_fetch_metadata(video, db)
        step_download_captions(video, db)
        step_enhance_captions(video, db)
        frames = step_extract_frames(video, db)
        analyses = step_analyze_frames_ocr(video, frames, db)
        step_analyze_frames_vision(video, frames, analyses, db)
        segments = step_align_segments(video, db)
        step_score_risk(video, segments, db)

        # Mark all segments as reviewed
        for seg in db.query(Segment).filter(Segment.video_id == video.id).all():
            seg.review_status = "approved"
        db.commit()

        from app.routers.export import pre_upload_validation
        result = pre_upload_validation(video.id, db)
        assert result["ready"] is True
