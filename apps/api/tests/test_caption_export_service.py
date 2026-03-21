import os

os.environ["DATABASE_URL"] = "sqlite:///./test_caption_export.db"

from app.database import engine, SessionLocal
from app.models.base import Base
from app.models import Video, CaptionVersion, Segment
from app.services.caption_service import caption_service
from app.utils.vtt_parser import parse_vtt


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_caption_export.db"):
        os.remove("test_caption_export.db")


def test_export_original_vtt_prefers_raw_auto_over_enhanced_version():
    db = SessionLocal()
    try:
        video = Video(youtube_id="abc123xyz00", title="Demo Video")
        db.add(video)
        db.commit()
        db.refresh(video)

        db.add_all([
            CaptionVersion(
                video_id=video.id,
                version_number=1,
                label="raw_auto",
                vtt_content="WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nraw line\n",
            ),
            CaptionVersion(
                video_id=video.id,
                version_number=2,
                label="enhanced",
                vtt_content="WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nEnhanced line.\n",
            ),
            CaptionVersion(
                video_id=video.id,
                version_number=3,
                label="reviewed",
                vtt_content="WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nEnhanced line.\n[Visual: chart appears]\n",
            ),
        ])
        db.commit()

        exported = caption_service.get_original_vtt(video.id, db)

        assert exported is not None
        assert "raw line" in exported
        assert "Enhanced line." not in exported
        assert "[Visual: chart appears]" not in exported
    finally:
        db.close()


def test_export_visual_descriptions_vtt_contains_only_ai_suggestions():
    db = SessionLocal()
    try:
        video = Video(youtube_id="def456uvw99", title="Description Demo")
        db.add(video)
        db.commit()
        db.refresh(video)

        db.add_all([
            Segment(
                video_id=video.id,
                start_time=1.0,
                end_time=3.0,
                transcript_text="Original caption",
                ai_suggestion="[Visual: a chart rises sharply.]",
                risk_level="high",
            ),
            Segment(
                video_id=video.id,
                start_time=4.0,
                end_time=6.0,
                transcript_text="Another caption",
                ai_suggestion=None,
                risk_level="low",
            ),
            Segment(
                video_id=video.id,
                start_time=7.0,
                end_time=9.0,
                transcript_text="Third caption",
                ai_suggestion="[Visual: molecules collide.]",
                risk_level="medium",
            ),
        ])
        db.commit()

        exported = caption_service.get_visual_descriptions_vtt(video.id, db)

        assert exported is not None
        assert "Original caption" not in exported
        assert "Another caption" not in exported
        assert "[Visual: a chart rises sharply.]" in exported
        assert "[Visual: molecules collide.]" in exported
    finally:
        db.close()


def test_export_original_vtt_dedupes_progressive_caption_windows():
    db = SessionLocal()
    try:
        video = Video(youtube_id="ghi789rst88", title="Progressive Captions")
        db.add(video)
        db.commit()
        db.refresh(video)

        db.add(
            CaptionVersion(
                video_id=video.id,
                version_number=1,
                label="enhanced",
                vtt_content="""WEBVTT

00:00:05.429 --> 00:00:05.439
So far we've only talked about.

00:00:05.439 --> 00:00:06.929
So far we've only talked about
electrical fields between charged.

00:00:06.929 --> 00:00:06.939
Electrical fields between charged.

00:00:06.939 --> 00:00:09.299
Electrical fields between charged
objects like particles and plates so can.
""",
            )
        )
        db.commit()

        exported = caption_service.get_original_vtt(video.id, db)

        assert exported is not None
        cues = parse_vtt(exported)
        assert len(cues) == 3
        assert cues[0].text == "So far we've only talked about."
        assert cues[1].text == "electrical fields between charged."
        assert cues[2].text == "objects like particles and plates so can."
    finally:
        db.close()
