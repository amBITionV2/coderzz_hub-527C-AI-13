"""
Pydantic schemas for FloatChat API request/response models.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator, ConfigDict
from enum import Enum


class DataModeEnum(str, Enum):
    """Data mode enumeration."""
    REAL_TIME = "R"
    ADJUSTED = "A"
    DELAYED = "D"


class DirectionEnum(str, Enum):
    """Profile direction enumeration."""
    ASCENDING = "A"
    DESCENDING = "D"


class StatusEnum(str, Enum):
    """Float status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


# Measurement Schemas
class MeasurementBase(BaseModel):
    """Base measurement schema."""
    pressure: float = Field(..., description="Pressure in decibars")
    depth: Optional[float] = Field(None, description="Depth in meters")
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    salinity: Optional[float] = Field(None, description="Salinity in PSU")
    dissolved_oxygen: Optional[float] = Field(None, description="Dissolved oxygen in micromol/kg")
    ph: Optional[float] = Field(None, description="pH value")
    nitrate: Optional[float] = Field(None, description="Nitrate in micromol/kg")
    chlorophyll: Optional[float] = Field(None, description="Chlorophyll in mg/m3")
    measurement_order: int = Field(0, description="Order of measurement within profile")


class MeasurementCreate(MeasurementBase):
    """Schema for creating measurements."""
    pass


class MeasurementSchema(MeasurementBase):
    """Complete measurement schema with metadata."""
    id: int
    profile_id: int
    pressure_qc: Optional[str] = None
    temperature_qc: Optional[str] = None
    salinity_qc: Optional[str] = None
    temperature_adjusted: Optional[float] = None
    salinity_adjusted: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Profile Schemas
class ProfileBase(BaseModel):
    """Base profile schema."""
    cycle_number: int = Field(..., description="Profile cycle number")
    profile_id: str = Field(..., description="Unique profile identifier")
    timestamp: datetime = Field(..., description="Profile timestamp")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    direction: DirectionEnum = Field(DirectionEnum.ASCENDING, description="Profile direction")
    data_mode: DataModeEnum = Field(DataModeEnum.REAL_TIME, description="Data processing mode")


class ProfileCreate(ProfileBase):
    """Schema for creating profiles."""
    measurements: List[MeasurementCreate] = Field(default_factory=list, description="Profile measurements")


class ProfileSchema(ProfileBase):
    """Complete profile schema with measurements."""
    id: int
    float_id: int
    position_qc: Optional[str] = None
    profile_qc: Optional[str] = None
    data_centre: Optional[str] = None
    dc_reference: Optional[str] = None
    measurements: List[MeasurementSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileSummary(BaseModel):
    """Simplified profile schema for summaries."""
    id: int
    cycle_number: int
    timestamp: datetime
    latitude: float
    longitude: float
    measurement_count: int = Field(0, description="Number of measurements in profile")

    model_config = ConfigDict(from_attributes=True)


# Float Schemas
class FloatBase(BaseModel):
    """Base float schema."""
    wmo_id: str = Field(..., description="WMO identifier")
    deployment_latitude: Optional[float] = Field(None, ge=-90, le=90, description="Deployment latitude")
    deployment_longitude: Optional[float] = Field(None, ge=-180, le=180, description="Deployment longitude")
    platform_type: Optional[str] = Field(None, description="Platform type")
    institution: Optional[str] = Field(None, description="Responsible institution")
    project_name: Optional[str] = Field(None, description="Project name")
    pi_name: Optional[str] = Field(None, description="Principal investigator")
    status: StatusEnum = Field(StatusEnum.ACTIVE, description="Float status")
    deployment_date: Optional[datetime] = Field(None, description="Deployment date")


class FloatCreate(FloatBase):
    """Schema for creating floats."""
    pass


class FloatDetailSchema(FloatBase):
    """Complete float schema with profiles."""
    id: int
    last_update: Optional[datetime] = None
    profiles: List[ProfileSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FloatSummarySchema(BaseModel):
    """Simplified float schema for map display."""
    id: int
    wmo_id: str
    latitude: Optional[float] = Field(None, description="Latest position latitude")
    longitude: Optional[float] = Field(None, description="Latest position longitude")
    status: StatusEnum
    last_update: Optional[datetime] = None
    profile_count: int = Field(0, description="Total number of profiles")
    latest_profile_date: Optional[datetime] = Field(None, description="Date of most recent profile")

    model_config = ConfigDict(from_attributes=True)


# AI Query Schemas
class AIQueryInput(BaseModel):
    """Schema for user AI queries."""
    question: str = Field(..., min_length=1, max_length=1000, description="User's oceanographic question")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the query")
    
    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()


class QueryParameters(BaseModel):
    """Schema for structured AI query parameters."""
    location: Optional[str] = Field(None, description="Geographic location or region")
    bbox: Optional[List[float]] = Field(None, description="Bounding box [min_lon, min_lat, max_lon, max_lat]")
    start_date: Optional[datetime] = Field(None, description="Start date for temporal filtering")
    end_date: Optional[datetime] = Field(None, description="End date for temporal filtering")
    variables: List[str] = Field(default_factory=list, description="Requested oceanographic variables")
    depth_range: Optional[List[float]] = Field(None, description="Depth range [min_depth, max_depth] in meters")
    general_search_term: Optional[str] = Field(None, description="General search term for text matching")
    
    @validator('bbox')
    def validate_bbox(cls, v):
        if v is not None:
            if len(v) != 4:
                raise ValueError('Bounding box must have exactly 4 coordinates')
            if not (-180 <= v[0] <= 180 and -180 <= v[2] <= 180):
                raise ValueError('Longitude values must be between -180 and 180')
            if not (-90 <= v[1] <= 90 and -90 <= v[3] <= 90):
                raise ValueError('Latitude values must be between -90 and 90')
            if v[0] >= v[2] or v[1] >= v[3]:
                raise ValueError('Invalid bounding box coordinates')
        return v
    
    @validator('depth_range')
    def validate_depth_range(cls, v):
        if v is not None:
            if len(v) != 2:
                raise ValueError('Depth range must have exactly 2 values')
            if v[0] < 0 or v[1] < 0:
                raise ValueError('Depth values must be non-negative')
            if v[0] >= v[1]:
                raise ValueError('Minimum depth must be less than maximum depth')
        return v


class AIQueryResponse(BaseModel):
    """Schema for AI query responses."""
    query: str = Field(..., description="Original user query")
    parameters: QueryParameters = Field(..., description="Extracted query parameters")
    floats: List[FloatSummarySchema] = Field(default_factory=list, description="Matching floats")
    insights: str = Field(..., description="AI-generated insights about the data")
    data_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics of the data")
    recommendations: List[str] = Field(default_factory=list, description="AI recommendations for further analysis")
    processing_time: float = Field(..., description="Query processing time in seconds")


# Health Check Schema
class HealthCheck(BaseModel):
    """Health check response schema."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    database: bool = Field(..., description="Database connectivity status")
    version: str = Field(..., description="Application version")


# Error Schemas
class ErrorDetail(BaseModel):
    """Error detail schema."""
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    field: Optional[str] = Field(None, description="Field that caused the error")


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error type")
    details: List[ErrorDetail] = Field(default_factory=list, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


# Pagination Schemas
class PaginationParams(BaseModel):
    """Pagination parameters schema."""
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(50, ge=1, le=1000, description="Page size")


class PaginatedResponse(BaseModel):
    """Paginated response schema."""
    items: List[Any] = Field(..., description="Items in current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    
    @validator('pages', pre=True, always=True)
    def calculate_pages(cls, v, values):
        total = values.get('total', 0)
        size = values.get('size', 1)
        return (total + size - 1) // size if total > 0 else 0
