import logging
from typing import Optional, Tuple
import pyproj
from pyproj import CRS, Transformer
import shapely.ops
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)


def get_utm_epsg_for_latlon(lat: float, lon: float) -> int:
    """
    Determine the EPSG code for the appropriate UTM (Universal Transverse Mercator) zone
    given a latitude and longitude (in WGS84 degrees).
    
    Formula:
      utm_zone = int((lon + 180) / 6) + 1
      EPSG: 32601-32660 for Northern Hemisphere (lat >= 0)
      EPSG: 32701-32760 for Southern Hemisphere (lat < 0)
    """
    # Constrain lon to [-180, 180]
    lon = ((lon + 180) % 360) - 180
    utm_zone = int((lon + 180) / 6) + 1
    # Boundary guard: UTM zones are 1 to 60
    utm_zone = max(1, min(60, utm_zone))
    
    if lat >= 0:
        return 32600 + utm_zone
    else:
        return 32700 + utm_zone


class CRSTransformer:
    """
    Handles coordinate reference system detection, evaluation,
    and transformation from geographic (degrees) to metric projected coordinate systems.
    """

    @staticmethod
    def parse_crs(crs_input: Optional[any]) -> Optional[CRS]:
        """
        Parses various CRS representations into a pyproj.CRS instance.
        """
        if crs_input is None:
            return None
        try:
            if isinstance(crs_input, CRS):
                return crs_input
            return CRS.from_user_input(crs_input)
        except Exception as e:
            logger.warning(f"Could not parse CRS input '{crs_input}': {e}")
            return None

    @classmethod
    def transform_geometry_to_metric(
        cls,
        geom: BaseGeometry,
        source_crs: Optional[any] = None
    ) -> Tuple[BaseGeometry, str]:
        """
        Transforms a Shapely geometry into an appropriate projected metric CRS.
        
        If source CRS is geographic (degrees, e.g. EPSG:4326), finds the optimal UTM
        zone based on the geometry's centroid, transforms it, and returns the
        projected geometry in meters alongside the target CRS identifier.
        
        If source CRS is already a projected metric CRS, preserves it and returns
        the geometry in its native projected CRS.
        
        If source CRS is unspecified, assumes EPSG:4326 as standard geospatial default.
        """
        parsed_source = cls.parse_crs(source_crs)
        
        # If no CRS specified, default to WGS84 geographic (EPSG:4326)
        if parsed_source is None:
            logger.info("Source CRS not specified; defaulting to EPSG:4326")
            parsed_source = CRS.from_epsg(4326)
        
        # Check if already a projected coordinate system
        if parsed_source.is_projected:
            target_crs_str = parsed_source.to_string()
            # If it has an EPSG code, prefer it for readability
            epsg = parsed_source.to_epsg()
            if epsg:
                target_crs_str = f"EPSG:{epsg}"
            return geom, target_crs_str

        # If it is geographic (degrees like lat/lon):
        # We must select an appropriate projected CRS (e.g. UTM) based on geometry location
        centroid = geom.centroid
        lon, lat = centroid.x, centroid.y
        
        target_epsg = get_utm_epsg_for_latlon(lat, lon)
        target_crs = CRS.from_epsg(target_epsg)
        
        # Create transformer with always_xy=True to ensure (lon, lat) / (x, y) order
        transformer = Transformer.from_crs(parsed_source, target_crs, always_xy=True)
        
        # Transform Shapely geometry using vectorized coordinate transformation
        try:
            import numpy as np
            def _transform_coords(coords):
                transformed_x, transformed_y = transformer.transform(coords[:, 0], coords[:, 1])
                if coords.shape[1] > 2:
                    return np.column_stack((transformed_x, transformed_y, coords[:, 2]))
                return np.column_stack((transformed_x, transformed_y))

            projected_geom = shapely.transform(geom, _transform_coords)
        except Exception:
            projected_geom = shapely.ops.transform(transformer.transform, geom)
        
        return projected_geom, f"EPSG:{target_epsg}"
