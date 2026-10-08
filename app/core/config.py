import os
from pathlib import Path
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "Geospatial File Measurement API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Upload storage directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    
    # Max file size: 50MB
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024
    
    # Supported file extensions
    ALLOWED_EXTENSIONS: set = {".zip", ".kml"}

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
