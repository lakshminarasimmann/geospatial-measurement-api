from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"


def test_upload_shapefile_zip():
    zip_path = SAMPLE_DIR / "sample_parcels.zip"
    with open(zip_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_parcels.zip", f, "application/zip")}
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sample_parcels.zip"
    assert data["feature_count"] == 2
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # 1. Test GET /api/files/{id}/
    info_resp = client.get(f"/api/files/{file_id}/")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert info_data["id"] == file_id
    assert info_data["filename"] == "sample_parcels.zip"
    assert info_data["feature_count"] == 2
    assert info_data["status"] == "COMPLETED"

    # 2. Test GET /api/files/{id}/measurements/
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["id"] == file_id
    assert meas_data["total_features"] == 2
    assert meas_data["measured_features_count"] == 2
    assert meas_data["summary"]["total_area_sq_meters"] > 0
    assert len(meas_data["features"]) == 2
    assert meas_data["features"][0]["geometry_type"] == "Polygon"
    assert meas_data["features"][0]["measurements"]["area_sq_meters"] > 0


def test_upload_kml_file():
    kml_path = SAMPLE_DIR / "sample_mixed_site.kml"
    with open(kml_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_mixed_site.kml", f, "application/vnd.google-earth.kml+xml")}
        )

    assert response.status_code == 201
    data = response.json()
    file_id = data["id"]
    assert data["feature_count"] == 3
    assert data["status"] == "COMPLETED"

    # Test measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["total_features"] == 3

    # Check that Point is handled gracefully
    point_features = [f for f in meas_data["features"] if f["geometry_type"] == "Point"]
    assert len(point_features) == 1
    assert point_features[0]["measurement_applicable"] is False
    assert point_features[0]["measurements"] is None

    # Check that Polygon has area
    poly_features = [f for f in meas_data["features"] if f["geometry_type"] == "Polygon"]
    assert len(poly_features) == 1
    assert poly_features[0]["measurement_applicable"] is True
    assert poly_features[0]["measurements"]["area_sq_meters"] > 0

    # Check that LineString has length
    line_features = [f for f in meas_data["features"] if f["geometry_type"] == "LineString"]
    assert len(line_features) == 1
    assert line_features[0]["measurement_applicable"] is True
    assert line_features[0]["measurements"]["length_meters"] > 0


def test_measurement_filter_by_geometry_type():
    kml_path = SAMPLE_DIR / "sample_mixed_site.kml"
    with open(kml_path, "rb") as f:
        res = client.post("/api/files/", files={"file": ("sample_mixed_site.kml", f, "text/xml")})
    file_id = res.json()["id"]

    meas_resp = client.get(f"/api/files/{file_id}/measurements/?geometry_type=LineString")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["total_features"] == 1
    assert meas_data["features"][0]["geometry_type"] == "LineString"


def test_invalid_file_extension():
    response = client.post(
        "/api/files/",
        files={"file": ("test.pdf", b"fake pdf content", "application/pdf")}
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_file_not_found():
    response = client.get("/api/files/nonexistent_id_999/")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
