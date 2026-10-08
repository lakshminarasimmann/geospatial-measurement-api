import pytest
from shapely.geometry import Polygon, LineString, Point, GeometryCollection
from app.services.measurement import MeasurementService


def test_polygon_measurement():
    poly = Polygon([(77.590, 12.970), (77.595, 12.970), (77.595, 12.975), (77.590, 12.975)])
    meas = MeasurementService.calculate_feature_measurement(
        feature_id="poly_1",
        geom=poly,
        source_crs="EPSG:4326"
    )

    assert meas.measurement_applicable is True
    assert meas.geometry_type == "Polygon"
    assert meas.projected_crs_used == "EPSG:32643"
    assert meas.measurements.area_sq_meters > 0
    assert meas.measurements.area_hectares > 0
    assert meas.measurements.perimeter_meters > 0


def test_linestring_measurement():
    line = LineString([(77.590, 12.970), (77.595, 12.975)])
    meas = MeasurementService.calculate_feature_measurement(
        feature_id="line_1",
        geom=line,
        source_crs="EPSG:4326"
    )

    assert meas.measurement_applicable is True
    assert meas.geometry_type == "LineString"
    assert meas.measurements.length_meters > 0
    assert meas.measurements.length_km > 0


def test_point_measurement_graceful():
    pt = Point(77.590, 12.970)
    meas = MeasurementService.calculate_feature_measurement(
        feature_id="pt_1",
        geom=pt,
        source_crs="EPSG:4326"
    )

    assert meas.measurement_applicable is False
    assert meas.geometry_type == "Point"
    assert meas.measurements is None
    assert "Points are 0-dimensional" in meas.notes


def test_empty_geometry_graceful():
    empty_poly = Polygon()
    meas = MeasurementService.calculate_feature_measurement(
        feature_id="empty_1",
        geom=empty_poly,
        source_crs="EPSG:4326"
    )

    assert meas.measurement_applicable is False
    assert "empty" in meas.notes.lower()
