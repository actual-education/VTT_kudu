from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class Job(Base, IDMixin, TimestampMixin):
    __tablename__ = "jobs"

    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="queued")  # queued, running, completed, failed
    current_step = Column(String)
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text)
    result_summary = Column(Text)

    video = relationship("Video", back_populates="jobs")
    user = relationship("User", back_populates="jobs")
