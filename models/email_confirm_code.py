from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql.expression import text
import datetime

from .base import db


class EmailConfirmCode(db.Model):
    __tablename__ = "email_confirm_codes"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    pin_code = Column(String(8), default="", nullable=False)
    email = Column(String(40), default="", nullable=False)
    expires_at = Column(
        TIMESTAMP(timezone=False),
        default=datetime.datetime.now() + datetime.timedelta(hours=24),
        nullable=False,
    )
