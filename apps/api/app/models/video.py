from sqlalchemy import Column, String, Integer, Float, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class Video(Base, IDMixin, TimestampMixin):
    __tablename__ = "videos"

    youtube_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    channel_title = Column(String)
    duration_seconds = Column(Integer)
    thumbnail_url = Column(String)
    description = Column(Text)
    published_at = Column(String)

    compliance_score = Column(Float)
    status = Column(String, default="imported")  # imported, scanning, scanned, reviewed, published

    jobs = relationship("Job", back_populates="video")
    segments = relationship("Segment", back_populates="video", order_by="Segment.start_time")
    frame_analyses = relationship("FrameAnalysis", back_populates="video", order_by="FrameAnalysis.timestamp")
    caption_versions = relationship("CaptionVersion", back_populates="video", order_by="CaptionVersion.version_number")
