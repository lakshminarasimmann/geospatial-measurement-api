import pytest
from shapely.geometry import Polygon, Point
from app.services.crs_transformer import CRSTransformer, get_utm_epsg_for_latlon


def test_utm_zone_calculation():
    # Bangalore (Lon 77.59, Lat 12.97) -> Zone 43 North -> EPSG:32643
    assert get_utm_epsg_for_latlon(12.97, 77.59) == 32643

    # London (Lon -0.12, Lat 51.50) -> Zone 30 North -> EPSG:32630
    assert get_utm_epsg_for_latlon(51.50, -0.12) == 32630

    # Sydney (Lon 151.2, Lat -33.86) -> Zone 56 South -> EPSG:32756
    assert get_utm_epsg_for_latlon(-33.86, 151.2) == 32756

    # Rio de Janeiro (Lon -43.17, Lat -22.90) -> Zone 23 South -> EPSG:32723
    assert get_utm_epsg_for_latlon(-22.90, -43.17) == 32723


def test_transform_geographic_polygon_to_metric():
    # Polygon in Bangalore in WGS84 degrees
    poly = Polygon([(77.590, 12.970), (77.595, 12.970), (77.595, 12.975), (77.590, 12.975)])
    
    projected_geom, epsg_code = CRSTransformer.transform_geometry_to_metric(poly, "EPSG:4326")
    
    assert epsg_code == "EPSG:32643"
    # In UTM meters, area should be roughly ~540m x ~550m = ~300,000 m²
    assert 250000 < projected_geom.area < 350000


def test_preserve_already_projected_crs():
    # Polygon already in a metric projected coordinate system (e.g. EPSG:3857)
    poly = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    projected_geom, crs_str = CRSTransformer.transform_geometry_to_metric(poly, "EPSG:3857")
    
    assert "3857" in crs_str
    assert projected_geom.area == 10000.0
