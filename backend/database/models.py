from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    media_type: Mapped[str] = mapped_column(String(12), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    result_json: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")  # investigator's case notes
