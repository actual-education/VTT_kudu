from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class YouTubeAccount(Base, IDMixin, TimestampMixin):
    __tablename__ = "youtube_accounts"

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    channel_id = Column(String, nullable=False)
    channel_title = Column(String)
    access_token = Column(String)
    refresh_token = Column(String)

    user = relationship("User", back_populates="youtube_accounts")
