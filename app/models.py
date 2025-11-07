from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime, func, UniqueConstraint
from .database import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from sqlalchemy import Text

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    owner = relationship("User", backref="tasks")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # path to original uploaded photo (relative URL like /static/uploads/..)
    photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # path to last generated NDVI image (relative URL)
    ndvi_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # JSON string with last NDVI params (e.g. {"red":0,"nir":2})
    ndvi_params: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # last NDVI processing error message (if any)
    ndvi_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # segmentation fields
    segmentation_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    segmentation_params: Mapped[str | None] = mapped_column(String(512), nullable=True)
    segmentation_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ndvi_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ndvi_settings: Mapped[str | None] = mapped_column(String(1024), nullable=True)

