from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB, TEXT, TIMESTAMP, UUID
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text
from .base import db
import datetime


class User(db.Model):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    email = Column(String(255), unique=True, nullable=False)
    email_verified_at = Column(TIMESTAMP(timezone=False), default=None)
    username = Column(String(255), default=None, unique=False)
    password_hash = Column(String(80))
    avatar_url = Column(String(255), default="")
    bio = Column(TEXT, default="")
    location = Column(JSONB, default=lambda: {})
    rating = Column(JSONB, default=lambda: {})
    is_onboarded = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=False), default=datetime.datetime.now())
    updated_at = Column(TIMESTAMP(timezone=False), default=datetime.datetime.now())

    gaming_platform_id = Column(UUID(as_uuid=True), default=None)
    play_style_id = Column(UUID(as_uuid=True), default=None)
    avatar_id = Column(UUID(as_uuid=True), default=None)
    objective_id = Column(UUID(as_uuid=True), default=None)

    source_id = Column(String(18), default=None)
    source_type = Column(Integer, default=1)
    stats_url = Column(String(255), default="")
    social_url = Column(JSONB, default=lambda: {})
    stats_id = Column(UUID(as_uuid=True), default=None)

    def __repr__(self):
        return f"{self.id} {self.email} {self.password_hash} {self.created_at} {self.location}"
