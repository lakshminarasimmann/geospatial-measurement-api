class GeospatialAPIException(Exception):
    """Base exception for Geospatial API."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidFileException(GeospatialAPIException):
    def __init__(self, message: str = "Invalid geospatial file format or structure"):
        super().__init__(message=message, status_code=400)


class FileNotFoundInStorageException(GeospatialAPIException):
    def __init__(self, file_id: str):
        super().__init__(message=f"File with ID '{file_id}' not found", status_code=404)


class FileProcessingException(GeospatialAPIException):
    def __init__(self, message: str = "Error occurred during file processing"):
        super().__init__(message=message, status_code=422)


class CRSTransformationException(GeospatialAPIException):
    def __init__(self, message: str = "Coordinate reference system transformation failed"):
        super().__init__(message=message, status_code=422)
