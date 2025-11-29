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
    # path to original uploaded photo (relative URL like /static/uploads/..)
    photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    owner = relationship("User", backref="tasks")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # one-to-one relationships to hold NDVI / segmentation / analysis results
    # photos attached to the task; cascade so deleting a Task removes its Photos
    photos = relationship("Photo", back_populates="task", cascade="all, delete-orphan")

class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    task = relationship("Task", back_populates="photos")

    path: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # one-to-one result relationships
    ndvi = relationship("PhotoNDVI", uselist=False, back_populates="photo", cascade="all, delete-orphan")
    segmentation = relationship("PhotoSegmentation", uselist=False, back_populates="photo", cascade="all, delete-orphan")
    analysis = relationship("PhotoAnalysis", uselist=False, back_populates="photo", cascade="all, delete-orphan")


class PhotoNDVI(Base):
    __tablename__ = "photo_ndvi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    photo_id: Mapped[int] = mapped_column(Integer, ForeignKey("photos.id"), unique=True, nullable=False)
    photo = relationship("Photo", back_populates="ndvi")

    ndvi_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ndvi_params: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ndvi_error: Mapped[str | None] = mapped_column(String(512), nullable=True)


class PhotoSegmentation(Base):
    __tablename__ = "photo_segmentation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    photo_id: Mapped[int] = mapped_column(Integer, ForeignKey("photos.id"), unique=True, nullable=False)
    photo = relationship("Photo", back_populates="segmentation")

    segmentation_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    segmentation_params: Mapped[str | None] = mapped_column(String(512), nullable=True)
    segmentation_error: Mapped[str | None] = mapped_column(String(512), nullable=True)


class PhotoAnalysis(Base):
    __tablename__ = "photo_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    photo_id: Mapped[int] = mapped_column(Integer, ForeignKey("photos.id"), unique=True, nullable=False)
    photo = relationship("Photo", back_populates="analysis")

    analysis_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    analysis_params: Mapped[str | None] = mapped_column(String(512), nullable=True)
    analysis_error: Mapped[str | None] = mapped_column(String(512), nullable=True)

