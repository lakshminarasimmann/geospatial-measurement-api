from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    id: str = Field(..., description="Unique identifier for uploaded file")
    filename: str = Field(..., description="Original filename")
    feature_count: int = Field(..., description="Number of geospatial features extracted")
    crs: Optional[str] = Field(None, description="Coordinate Reference System of the file")
    status: str = Field(..., description="Processing status (e.g., COMPLETED, FAILED)")
    message: Optional[str] = Field(None, description="Informational or status message")


class FileInfoResponse(BaseModel):
    id: str = Field(..., description="Unique identifier for uploaded file")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="Detected format: shapefile or kml")
    feature_count: int = Field(..., description="Number of geospatial features")
    crs: Optional[str] = Field(None, description="Source Coordinate Reference System")
    status: str = Field(..., description="Processing status: COMPLETED, FAILED")
    created_at: str = Field(..., description="Timestamp of upload")
    error_message: Optional[str] = Field(None, description="Error details if processing failed")


class FeatureDetail(BaseModel):
    feature_id: Union[int, str] = Field(..., description="Feature identifier or index")
    geometry_type: str = Field(..., description="Type of geometry (Polygon, LineString, Point, etc.)")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON representation of geometry")
    crs: Optional[str] = Field(None, description="Feature CRS")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Feature attributes and metadata")


class PolygonMeasurements(BaseModel):
    area_sq_meters: float = Field(..., description="Area in square meters (m²)")
    area_hectares: float = Field(..., description="Area in hectares (ha)")
    area_sq_km: float = Field(..., description="Area in square kilometers (km²)")
    area_acres: float = Field(..., description="Area in acres")
    perimeter_meters: float = Field(..., description="Perimeter in meters (m)")


class LineMeasurements(BaseModel):
    length_meters: float = Field(..., description="Length in meters (m)")
    length_km: float = Field(..., description="Length in kilometers (km)")


class FeatureMeasurement(BaseModel):
    feature_id: Union[int, str] = Field(..., description="Feature identifier/index")
    geometry_type: str = Field(..., description="Geometry type")
    measurement_applicable: bool = Field(..., description="Whether measurements apply to this geometry type")
    projected_crs_used: Optional[str] = Field(
        None, description="Projected CRS utilized to perform metric calculations (e.g. UTM zone)"
    )
    measurements: Optional[Union[PolygonMeasurements, LineMeasurements, Dict[str, Any]]] = Field(
        None, description="Calculated metric measurements"
    )
    notes: Optional[str] = Field(None, description="Notes on calculation or why measurements do not apply")


class MeasurementSummary(BaseModel):
    total_area_sq_meters: float = 0.0
    total_area_hectares: float = 0.0
    total_area_sq_km: float = 0.0
    total_area_acres: float = 0.0
    total_length_meters: float = 0.0
    total_length_km: float = 0.0
    geometry_distribution: Dict[str, int] = Field(default_factory=dict)


class MeasurementsResponse(BaseModel):
    id: str = Field(..., description="File ID")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    total_features: int = Field(..., description="Total features in file")
    measured_features_count: int = Field(..., description="Number of features successfully measured")
    summary: MeasurementSummary = Field(..., description="Aggregated summary of measurements")
    features: List[FeatureMeasurement] = Field(..., description="Per-feature measurements")


class FileListResponse(BaseModel):
    total: int
    files: List[FileInfoResponse]
