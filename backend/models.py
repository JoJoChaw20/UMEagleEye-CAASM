import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, MACADDR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Asset(Base):
    __tablename__ = "assets"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False, unique=True)
    mac_address: Mapped[str] = mapped_column(MACADDR, nullable=False, unique=True)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    hardware_vendor: Mapped[str] = mapped_column(String(100), nullable=False)
    os_info: Mapped[str] = mapped_column(String(255), nullable=False)
    last_boot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    criticality_score: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_scanned: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    outgoing_connections: Mapped[list["NetworkConnection"]] = relationship(
        back_populates="source_asset",
        foreign_keys="NetworkConnection.source_asset_id",
        cascade="all, delete-orphan",
    )
    incoming_connections: Mapped[list["NetworkConnection"]] = relationship(
        back_populates="target_asset",
        foreign_keys="NetworkConnection.target_asset_id",
        cascade="all, delete-orphan",
    )
    sboms: Mapped[list["Sbom"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class NetworkConnection(Base):
    __tablename__ = "network_connections"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=False
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=False
    )
    connection_method: Mapped[str] = mapped_column(String(100), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_asset: Mapped[Asset] = relationship(back_populates="outgoing_connections", foreign_keys=[source_asset_id])
    target_asset: Mapped[Asset] = relationship(back_populates="incoming_connections", foreign_keys=[target_asset_id])


class Sbom(Base):
    __tablename__ = "sboms"

    sbom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=False
    )
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="sboms")


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="events")
    advisories: Mapped[list["Advisory"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Advisory(Base):
    __tablename__ = "advisories"

    advisory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    event: Mapped[Event] = relationship(back_populates="advisories")


class PostureMetric(Base):
    __tablename__ = "posture_metrics"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_critical_assets: Mapped[int] = mapped_column(Integer, nullable=False)
    top_risks: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
