from pathlib import Path
import pytest
from app.services.file_processor import FileProcessorService
from app.core.errors import InvalidFileException

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def test_process_shapefile_zip():
    zip_path = SAMPLE_DIR / "sample_parcels.zip"
    extracted = FileProcessorService.process_file(zip_path, "sample_parcels.zip")

    assert extracted.file_type == "shapefile"
    assert extracted.feature_count == 2
    assert len(extracted.features) == 2
    assert extracted.features[0].geometry_type == "Polygon"
    assert "parcel_id" in extracted.features[0].properties


def test_process_linestring_shapefile_zip():
    zip_path = SAMPLE_DIR / "sample_pipelines.zip"
    extracted = FileProcessorService.process_file(zip_path, "sample_pipelines.zip")

    assert extracted.file_type == "shapefile"
    assert extracted.feature_count == 2
    assert extracted.features[0].geometry_type == "LineString"


def test_process_kml_polygon():
    kml_path = SAMPLE_DIR / "sample_polygon.kml"
    extracted = FileProcessorService.process_file(kml_path, "sample_polygon.kml")

    assert extracted.file_type == "kml"
    assert extracted.feature_count >= 1
    assert extracted.features[0].geometry_type == "Polygon"


def test_process_kml_mixed():
    kml_path = SAMPLE_DIR / "sample_mixed_site.kml"
    extracted = FileProcessorService.process_file(kml_path, "sample_mixed_site.kml")

    assert extracted.file_type == "kml"
    assert extracted.feature_count == 3
    geom_types = [f.geometry_type for f in extracted.features]
    assert "Polygon" in geom_types
    assert "LineString" in geom_types
    assert "Point" in geom_types


def test_unsupported_file_extension():
    fake_path = SAMPLE_DIR / "fake.txt"
    with pytest.raises(InvalidFileException):
        FileProcessorService.process_file(fake_path, "fake.txt")
