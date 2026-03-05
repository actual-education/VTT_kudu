from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class User(Base, IDMixin, TimestampMixin):
    __tablename__ = "users"

    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)

    youtube_accounts = relationship("YouTubeAccount", back_populates="user")
    jobs = relationship("Job", back_populates="user")
