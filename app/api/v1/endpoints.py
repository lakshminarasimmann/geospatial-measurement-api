import os
import uuid
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, status

from app.core.config import settings
from app.core.errors import (
    InvalidFileException,
    FileNotFoundInStorageException,
    FileProcessingException
)
from app.models.schemas import (
    FileUploadResponse,
    FileInfoResponse,
    MeasurementsResponse,
    MeasurementSummary,
    FeatureMeasurement,
    FileListResponse,
    FeatureDetail
)
from app.services.file_processor import FileProcessorService
from app.services.measurement import MeasurementService
from app.services.storage import storage, FileRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Geospatial Files"])


@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process geospatial file",
    description="Accepts a zipped Shapefile (.zip) or a KML (.kml) file, extracts features, detects CRS, and computes measurements."
)
async def upload_file(
    file: UploadFile = File(..., description="Geospatial file (.zip Shapefile or .kml)")
):
    original_filename = file.filename or "unknown"
    ext = Path(original_filename).suffix.lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Only .zip (Shapefile) and .kml are supported."
        )

    # Generate unique file identifier
    file_id = str(uuid.uuid4())[:8]
    saved_filename = f"{file_id}_{original_filename}"
    saved_filepath = settings.UPLOAD_DIR / saved_filename

    # Save uploaded file to disk
    try:
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES / (1024*1024):.0f}MB."
            )

        with open(saved_filepath, "wb") as f:
            f.write(content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file."
        )

    file_type = "shapefile" if ext == ".zip" else "kml"

    # Initialize file record
    record = FileRecord(
        file_id=file_id,
        filename=original_filename,
        file_type=file_type,
        stored_path=saved_filepath,
        status="PROCESSING"
    )
    storage.add_record(record)

    # Process file and calculate measurements
    try:
        extracted = FileProcessorService.process_file(saved_filepath, original_filename)
        
        # Calculate measurements for extracted features
        feature_measurements: List[FeatureMeasurement] = []
        summary = MeasurementSummary()
        measured_count = 0

        for feat_detail, raw_geom in zip(extracted.features, extracted.raw_geometries):
            measurement = MeasurementService.calculate_feature_measurement(
                feature_id=feat_detail.feature_id,
                geom=raw_geom,
                source_crs=extracted.crs
            )
            feature_measurements.append(measurement)

            # Update geometry distribution count
            geom_type = measurement.geometry_type
            summary.geometry_distribution[geom_type] = summary.geometry_distribution.get(geom_type, 0) + 1

            if measurement.measurement_applicable and measurement.measurements:
                measured_count += 1
                m = measurement.measurements
                if hasattr(m, "area_sq_meters"):
                    summary.total_area_sq_meters = round(summary.total_area_sq_meters + m.area_sq_meters, 4)
                    summary.total_area_hectares = round(summary.total_area_hectares + m.area_hectares, 6)
                    summary.total_area_sq_km = round(summary.total_area_sq_km + m.area_sq_km, 6)
                    summary.total_area_acres = round(summary.total_area_acres + m.area_acres, 6)
                if hasattr(m, "length_meters"):
                    summary.total_length_meters = round(summary.total_length_meters + m.length_meters, 4)
                    summary.total_length_km = round(summary.total_length_km + m.length_km, 6)

        measurements_resp = MeasurementsResponse(
            id=file_id,
            filename=original_filename,
            status="COMPLETED",
            total_features=extracted.feature_count,
            measured_features_count=measured_count,
            summary=summary,
            features=feature_measurements
        )

        # Update record with completion state
        storage.update_record(
            file_id=file_id,
            feature_count=extracted.feature_count,
            crs=extracted.crs,
            status="COMPLETED",
            measurements=measurements_resp,
            features=extracted.features
        )

        return FileUploadResponse(
            id=file_id,
            filename=original_filename,
            feature_count=extracted.feature_count,
            crs=extracted.crs,
            status="COMPLETED",
            message="File uploaded and processed successfully"
        )

    except InvalidFileException as e:
        storage.update_record(file_id=file_id, status="FAILED", error_message=str(e.message))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message))
    except FileProcessingException as e:
        storage.update_record(file_id=file_id, status="FAILED", error_message=str(e.message))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e.message))
    except Exception as e:
        logger.exception("Unexpected error processing geospatial file")
        storage.update_record(file_id=file_id, status="FAILED", error_message=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the file: {str(e)}"
        )


@router.get(
    "/{id}/",
    response_model=FileInfoResponse,
    summary="Get file information",
    description="Returns metadata and processing status for an uploaded file by ID."
)
async def get_file_info(id: str):
    try:
        record = storage.get_record(id)
        return record.to_info_response()
    except FileNotFoundInStorageException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' not found."
        )


@router.get(
    "/{id}/measurements/",
    response_model=MeasurementsResponse,
    summary="Get measurements for file features",
    description="Returns calculated metric measurements (area for polygons, length for linestrings, graceful handling for points)."
)
async def get_file_measurements(
    id: str,
    geometry_type: Optional[str] = Query(None, description="Optional filter by geometry type (e.g. Polygon, LineString, Point)")
):
    try:
        record = storage.get_record(id)
    except FileNotFoundInStorageException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' not found."
        )

    if record.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File processing status is '{record.status}'. Reason: {record.error_message or 'Still in progress'}"
        )

    if not record.measurements:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurements not found for this file."
        )

    # Optional geometry type filtering
    if geometry_type:
        filtered_features = [
            f for f in record.measurements.features
            if f.geometry_type.lower() == geometry_type.lower()
        ]
        return MeasurementsResponse(
            id=record.measurements.id,
            filename=record.measurements.filename,
            status=record.measurements.status,
            total_features=len(filtered_features),
            measured_features_count=sum(1 for f in filtered_features if f.measurement_applicable),
            summary=record.measurements.summary,
            features=filtered_features
        )

    return record.measurements


@router.get(
    "/{id}/features/",
    response_model=List[FeatureDetail],
    summary="Get raw feature attributes and geometries",
    description="Returns raw extracted features including GeoJSON geometry, properties, and CRS."
)
async def get_file_features(
    id: str,
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit")
):
    try:
        record = storage.get_record(id)
    except FileNotFoundInStorageException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' not found."
        )

    return record.features[skip:skip + limit]


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List all uploaded files",
    description="Returns a list of all processed geospatial files."
)
async def list_files():
    files = storage.list_records()
    return FileListResponse(total=len(files), files=files)


@router.delete(
    "/{id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Removes the file and its associated measurement cache."
)
async def delete_file(id: str):
    success = storage.delete_record(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' not found."
        )
    return None
