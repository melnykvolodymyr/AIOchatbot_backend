from sqlalchemy import Column, SmallInteger, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql.expression import text
from .base import db
import datetime


class Invitation(db.Model):
    __tablename__ = "invitations"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    from_id = Column(UUID(as_uuid=True), server_default=text("uuid_generate_v4()"))
    to_email = Column(String(20), default="")
    token = Column(UUID(as_uuid=True), server_default=text("uuid_generate_v4()"))
    status = Column(SmallInteger, default=1)
    expires_at = Column(TIMESTAMP(timezone=False), default=None)
