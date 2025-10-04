"""
SQLAlchemy ORM models for FloatChat oceanographic data.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
import uuid

from app.database import Base


class Float(Base):
    """
    Oceanographic float model representing Argo floats.
    """
    __tablename__ = "floats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wmo_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    
    # Optional deployment coordinates
    deployment_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    deployment_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Float metadata
    platform_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    institution: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    project_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    pi_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Status and timing
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, inactive, maintenance
    deployment_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_update: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profiles: Mapped[List["Profile"]] = relationship("Profile", back_populates="float", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Float(wmo_id='{self.wmo_id}', status='{self.status}')>"


class Profile(Base):
    """
    Profile model representing a single oceanographic profile from a float.
    """
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to float
    float_id: Mapped[int] = mapped_column(Integer, ForeignKey("floats.id"), nullable=False)
    
    # Profile identification
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    
    # Temporal information
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Spatial information
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    
    # PostGIS geometry column for efficient geospatial queries
    location: Mapped[str] = mapped_column(Geometry('POINT', srid=4326), nullable=False)
    
    # Profile metadata
    direction: Mapped[str] = mapped_column(String(1), default="A")  # A=Ascending, D=Descending
    data_mode: Mapped[str] = mapped_column(String(1), default="R")  # R=Real-time, A=Adjusted, D=Delayed
    
    # Quality control
    position_qc: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    profile_qc: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    
    # Data processing information
    data_centre: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    dc_reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    float: Mapped["Float"] = relationship("Float", back_populates="profiles")
    measurements: Mapped[List["Measurement"]] = relationship("Measurement", back_populates="profile", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Profile(profile_id='{self.profile_id}', timestamp='{self.timestamp}')>"


class Measurement(Base):
    """
    Measurement model representing individual oceanographic measurements within a profile.
    """
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to profile
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("profiles.id"), nullable=False)
    
    # Measurement depth/pressure
    pressure: Mapped[float] = mapped_column(Float, nullable=False)  # in decibars
    depth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in meters (calculated)
    
    # Core oceanographic variables
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in Celsius
    salinity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in PSU
    
    # Additional variables
    dissolved_oxygen: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in micromol/kg
    ph: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    nitrate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in micromol/kg
    chlorophyll: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in mg/m3
    
    # Quality control flags
    pressure_qc: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    temperature_qc: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    salinity_qc: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    
    # Adjusted values (for delayed mode data)
    temperature_adjusted: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salinity_adjusted: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Measurement order within profile
    measurement_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="measurements")

    def __repr__(self):
        return f"<Measurement(pressure={self.pressure}, temperature={self.temperature}, salinity={self.salinity})>"
