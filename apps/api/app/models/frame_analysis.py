from sqlalchemy import Column, String, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class FrameAnalysis(Base, IDMixin, TimestampMixin):
    __tablename__ = "frame_analyses"

    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    timestamp = Column(Float, nullable=False)

    has_text = Column(Boolean, default=False)
    has_diagram = Column(Boolean, default=False)
    has_equation = Column(Boolean, default=False)
    likely_essential = Column(Boolean, default=False)

    ocr_text = Column(Text)
    description = Column(Text)
    confidence = Column(Float)

    video = relationship("Video", back_populates="frame_analyses")
