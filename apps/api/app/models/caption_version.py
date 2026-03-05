from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class CaptionVersion(Base, IDMixin, TimestampMixin):
    __tablename__ = "caption_versions"

    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    label = Column(String, nullable=False)  # raw_auto, enhanced, reviewed, published
    vtt_content = Column(Text, nullable=False)

    video = relationship("Video", back_populates="caption_versions")
