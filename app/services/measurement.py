import logging
from typing import Any, Dict, Optional, Tuple
from shapely.geometry.base import BaseGeometry
from shapely.geometry import (
    Polygon, MultiPolygon,
    LineString, MultiLineString,
    Point, MultiPoint,
    GeometryCollection
)
from app.services.crs_transformer import CRSTransformer
from app.models.schemas import (
    FeatureMeasurement,
    PolygonMeasurements,
    LineMeasurements
)

logger = logging.getLogger(__name__)


class MeasurementService:
    """
    Calculates geographic measurements (area, length) for geospatial features,
    handling projected transformations and non-measurable/unsupported geometry types gracefully.
    """

    @classmethod
    def calculate_feature_measurement(
        cls,
        feature_id: Any,
        geom: BaseGeometry,
        source_crs: Optional[str] = None
    ) -> FeatureMeasurement:
        """
        Calculates measurement for a single geometry feature.
        Ensures coordinates are projected to a metric system before calculation.
        """
        if geom is None or geom.is_empty:
            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type="Empty/None",
                measurement_applicable=False,
                notes="Geometry is empty or invalid"
            )

        geom_type = geom.geom_type

        # 1. Polygon / MultiPolygon
        if isinstance(geom, (Polygon, MultiPolygon)):
            try:
                projected_geom, proj_crs = CRSTransformer.transform_geometry_to_metric(
                    geom, source_crs=source_crs
                )
                area_m2 = float(projected_geom.area)
                perimeter_m = float(projected_geom.length)
                
                measurements = PolygonMeasurements(
                    area_sq_meters=round(area_m2, 4),
                    area_hectares=round(area_m2 / 10000.0, 6),
                    area_sq_km=round(area_m2 / 1000000.0, 6),
                    area_acres=round(area_m2 / 4046.8564224, 6),
                    perimeter_meters=round(perimeter_m, 4)
                )
                
                return FeatureMeasurement(
                    feature_id=feature_id,
                    geometry_type=geom_type,
                    measurement_applicable=True,
                    projected_crs_used=proj_crs,
                    measurements=measurements
                )
            except Exception as e:
                logger.error(f"Error calculating polygon measurement for feature {feature_id}: {e}")
                return FeatureMeasurement(
                    feature_id=feature_id,
                    geometry_type=geom_type,
                    measurement_applicable=False,
                    notes=f"Measurement calculation failed: {str(e)}"
                )

        # 2. LineString / MultiLineString
        elif isinstance(geom, (LineString, MultiLineString)):
            try:
                projected_geom, proj_crs = CRSTransformer.transform_geometry_to_metric(
                    geom, source_crs=source_crs
                )
                length_m = float(projected_geom.length)
                
                measurements = LineMeasurements(
                    length_meters=round(length_m, 4),
                    length_km=round(length_m / 1000.0, 6)
                )
                
                return FeatureMeasurement(
                    feature_id=feature_id,
                    geometry_type=geom_type,
                    measurement_applicable=True,
                    projected_crs_used=proj_crs,
                    measurements=measurements
                )
            except Exception as e:
                logger.error(f"Error calculating linestring measurement for feature {feature_id}: {e}")
                return FeatureMeasurement(
                    feature_id=feature_id,
                    geometry_type=geom_type,
                    measurement_applicable=False,
                    notes=f"Measurement calculation failed: {str(e)}"
                )

        # 3. Point / MultiPoint
        elif isinstance(geom, (Point, MultiPoint)):
            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type=geom_type,
                measurement_applicable=False,
                notes="Points are 0-dimensional geometries; area and length measurements are not applicable."
            )

        # 4. GeometryCollection or other unhandled types
        elif isinstance(geom, GeometryCollection):
            # Attempt compound extraction or graceful skip
            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type=geom_type,
                measurement_applicable=False,
                notes="GeometryCollection contains mixed geometry primitives; evaluate individual components."
            )

        # 5. Unsupported geometry types
        else:
            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type=geom_type,
                measurement_applicable=False,
                notes=f"Geometry type '{geom_type}' is not supported for measurement calculation."
            )
