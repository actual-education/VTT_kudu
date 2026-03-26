from sqlalchemy import Column, String, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class Segment(Base, IDMixin, TimestampMixin):
    __tablename__ = "segments"

    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)

    transcript_text = Column(Text)
    ocr_text = Column(Text)
    visual_description = Column(Text)
    ai_suggestion = Column(Text)

    has_text = Column(Boolean, default=False)
    has_diagram = Column(Boolean, default=False)
    has_equation = Column(Boolean, default=False)

    risk_level = Column(String)  # low, medium, high
    education_level = Column(String, default="low")  # low, high
    risk_reason = Column(String)  # reason code
    review_status = Column(String, default="pending")  # pending, approved, rejected, edited

    video = relationship("Video", back_populates="segments")
