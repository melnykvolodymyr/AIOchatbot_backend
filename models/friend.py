from sqlalchemy import Column, SmallInteger
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text
from .base import db
import datetime


class Friend(db.Model):
    __tablename__ = "users_friends"

    id = Column(UUID(as_uuid=True), server_default=text("uuid_generate_v4()"))
    user_id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    friend_id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    status = Column(SmallInteger, default=1)
    created_at = Column(TIMESTAMP(timezone=False), default=datetime.datetime.now())
    updated_at = Column(TIMESTAMP(timezone=False), default=datetime.datetime.now())
