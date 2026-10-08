import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from app.core.config import settings
from app.core.errors import FileNotFoundInStorageException
from app.models.schemas import FileInfoResponse, MeasurementsResponse, FeatureDetail

logger = logging.getLogger(__name__)


class FileRecord:
    def __init__(
        self,
        file_id: str,
        filename: str,
        file_type: str,
        stored_path: Path,
        feature_count: int = 0,
        crs: Optional[str] = None,
        status: str = "PROCESSING",
        error_message: Optional[str] = None,
        created_at: Optional[str] = None,
        measurements: Optional[MeasurementsResponse] = None,
        features: Optional[List[FeatureDetail]] = None
    ):
        self.file_id = file_id
        self.filename = filename
        self.file_type = file_type
        self.stored_path = stored_path
        self.feature_count = feature_count
        self.crs = crs
        self.status = status
        self.error_message = error_message
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.measurements = measurements
        self.features = features or []

    def to_info_response(self) -> FileInfoResponse:
        return FileInfoResponse(
            id=self.file_id,
            filename=self.filename,
            file_type=self.file_type,
            feature_count=self.feature_count,
            crs=self.crs,
            status=self.status,
            created_at=self.created_at,
            error_message=self.error_message
        )


class StorageService:
    """
    Thread-safe storage manager for uploaded files, feature data, and calculated measurements.
    """
    def __init__(self):
        self._records: Dict[str, FileRecord] = {}
        self._lock = threading.Lock()

    def add_record(self, record: FileRecord) -> None:
        with self._lock:
            self._records[record.file_id] = record

    def get_record(self, file_id: str) -> FileRecord:
        with self._lock:
            if file_id not in self._records:
                raise FileNotFoundInStorageException(file_id)
            return self._records[file_id]

    def update_record(self, file_id: str, **kwargs) -> FileRecord:
        with self._lock:
            if file_id not in self._records:
                raise FileNotFoundInStorageException(file_id)
            record = self._records[file_id]
            for key, val in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, val)
            return record

    def list_records(self) -> List[FileInfoResponse]:
        with self._lock:
            return [rec.to_info_response() for rec in reversed(list(self._records.values()))]

    def delete_record(self, file_id: str) -> bool:
        with self._lock:
            if file_id in self._records:
                rec = self._records.pop(file_id)
                try:
                    if rec.stored_path.exists():
                        rec.stored_path.unlink()
                except Exception as e:
                    logger.warning(f"Error removing stored file {rec.stored_path}: {e}")
                return True
            return False


storage = StorageService()
