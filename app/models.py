from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now():
    return datetime.now(timezone.utc)


class ProtectedArea(Base):
    __tablename__ = "protected_area"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    wdpa_id: Mapped[int | None]
    geom = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    forest_2000_ha: Mapped[float | None] = mapped_column(Float)


class Team(Base):
    __tablename__ = "team"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class AppUser(Base):
    __tablename__ = "app_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))  # manager | field | analyst
    team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"))


class Case(Base):
    __tablename__ = "case"
    id: Mapped[int] = mapped_column(primary_key=True)
    protected_area_id: Mapped[int] = mapped_column(ForeignKey("protected_area.id"))
    geom = mapped_column(Geometry("GEOMETRY", srid=4326), nullable=True)
    area_ha: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(10))
    priority_code: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="detected", index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    protected_area: Mapped[ProtectedArea] = relationship()
    history: Mapped[list["CaseStatusLog"]] = relationship(
        back_populates="case", order_by="CaseStatusLog.id"
    )


class CaseStatusLog(Base):
    """Append-only. This table IS the M&E record: who, when, why."""

    __tablename__ = "case_status_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(20))  # None = case creation
    to_status: Mapped[str] = mapped_column(String(20))
    changed_by: Mapped[int] = mapped_column(ForeignKey("app_user.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reason: Mapped[str] = mapped_column(Text)

    case: Mapped[Case] = relationship(back_populates="history")
    user: Mapped[AppUser] = relationship()
