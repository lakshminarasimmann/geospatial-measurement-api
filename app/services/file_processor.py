import os
import shutil
import tempfile
import zipfile
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import geopandas as gpd
import pyogrio
from shapely.geometry import shape, mapping
from shapely.geometry.base import BaseGeometry
import xml.etree.ElementTree as ET

from app.core.errors import InvalidFileException, FileProcessingException
from app.models.schemas import FeatureDetail

logger = logging.getLogger(__name__)


class ExtractedGeodata:
    def __init__(
        self,
        features: List[FeatureDetail],
        raw_geometries: List[BaseGeometry],
        crs: Optional[str],
        file_type: str,
        feature_count: int
    ):
        self.features = features
        self.raw_geometries = raw_geometries
        self.crs = crs
        self.file_type = file_type
        self.feature_count = feature_count


class FileProcessorService:
    """
    Parses uploaded Shapefile (.zip) and KML (.kml) files,
    extracting geometry, attributes, CRS, and feature metadata.
    """

    @classmethod
    def process_file(cls, file_path: Path, original_filename: str) -> ExtractedGeodata:
        """
        Determines file format and delegates to appropriate parser.
        """
        ext = file_path.suffix.lower()
        if ext == ".zip":
            return cls.process_shapefile_zip(file_path)
        elif ext == ".kml":
            return cls.process_kml(file_path)
        else:
            raise InvalidFileException(f"Unsupported file format '{ext}'. Must be .zip or .kml.")

    @classmethod
    def process_shapefile_zip(cls, zip_path: Path) -> ExtractedGeodata:
        """
        Safely extracts zip archive and parses the ESRI Shapefile.
        """
        temp_dir = tempfile.mkdtemp(prefix="shp_")
        try:
            # 1. Safe extraction to prevent Zip Slip vulnerabilities
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    filename = os.path.basename(member)
                    # Skip directories or OS metadata files
                    if not filename or member.startswith('__MACOSX/'):
                        continue
                    # Ensure destination is within temp_dir
                    target_path = Path(temp_dir) / member
                    target_path.resolve().relative_to(Path(temp_dir).resolve())
                    zip_ref.extract(member, temp_dir)

            # 2. Locate .shp file
            shp_files = list(Path(temp_dir).rglob("*.shp"))
            if not shp_files:
                raise InvalidFileException(
                    "No .shp file found inside the uploaded ZIP archive. "
                    "Ensure the zip contains Shapefile components (.shp, .shx, .dbf)."
                )

            shp_file = shp_files[0]
            logger.info(f"Parsing shapefile from extracted path: {shp_file}")

            # 3. Read using GeoPandas / Pyogrio
            try:
                gdf = gpd.read_file(shp_file)
            except Exception as e:
                logger.error(f"Failed to read shapefile with geopandas: {e}")
                raise FileProcessingException(f"Failed to parse Shapefile: {str(e)}")

            crs_str = None
            if gdf.crs is not None:
                epsg = gdf.crs.to_epsg()
                crs_str = f"EPSG:{epsg}" if epsg else gdf.crs.to_string()

            features: List[FeatureDetail] = []
            raw_geometries: List[BaseGeometry] = []

            for idx, row in gdf.iterrows():
                geom: Optional[BaseGeometry] = row.geometry
                geom_type = geom.geom_type if geom is not None else "Unknown"
                
                # Filter out geometry column from attributes
                props = {k: cls._clean_property_value(v) for k, v in row.items() if k != "geometry"}
                
                # Extract GeoJSON geometry mapping
                geom_geojson = mapping(geom) if geom is not None else {}

                feature_detail = FeatureDetail(
                    feature_id=idx if not isinstance(idx, int) else int(idx),
                    geometry_type=geom_type,
                    geometry=geom_geojson,
                    crs=crs_str,
                    properties=props
                )
                features.append(feature_detail)
                raw_geometries.append(geom)

            return ExtractedGeodata(
                features=features,
                raw_geometries=raw_geometries,
                crs=crs_str,
                file_type="shapefile",
                feature_count=len(features)
            )

        finally:
            # Clean up extracted temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def process_kml(cls, kml_path: Path) -> ExtractedGeodata:
        """
        Parses KML file using pyogrio/geopandas, falling back to direct XML parsing if needed.
        KML coordinate reference system is canonically WGS84 (EPSG:4326).
        """
        default_crs = "EPSG:4326"
        
        # Method 1: Try reading all layers with pyogrio / geopandas
        try:
            layers = pyogrio.list_layers(kml_path)
            all_gdfs = []
            for layer_name in layers[:, 0]:
                try:
                    layer_gdf = gpd.read_file(kml_path, layer=layer_name)
                    if not layer_gdf.empty:
                        all_gdfs.append(layer_gdf)
                except Exception as layer_err:
                    logger.debug(f"Layer {layer_name} read skipped: {layer_err}")

            if all_gdfs:
                gdf = gpd.GeoDataFrame(pd_concat(all_gdfs, ignore_index=True))
                crs_str = default_crs
                if gdf.crs is not None:
                    epsg = gdf.crs.to_epsg()
                    crs_str = f"EPSG:{epsg}" if epsg else gdf.crs.to_string()

                features: List[FeatureDetail] = []
                raw_geometries: List[BaseGeometry] = []

                for idx, row in gdf.iterrows():
                    geom = row.geometry
                    geom_type = geom.geom_type if geom is not None else "Unknown"
                    props = {k: cls._clean_property_value(v) for k, v in row.items() if k != "geometry"}
                    geom_geojson = mapping(geom) if geom is not None else {}

                    feature_detail = FeatureDetail(
                        feature_id=int(idx),
                        geometry_type=geom_type,
                        geometry=geom_geojson,
                        crs=crs_str,
                        properties=props
                    )
                    features.append(feature_detail)
                    raw_geometries.append(geom)

                return ExtractedGeodata(
                    features=features,
                    raw_geometries=raw_geometries,
                    crs=crs_str,
                    file_type="kml",
                    feature_count=len(features)
                )
        except Exception as e:
            logger.warning(f"Pyogrio KML parser encountered issue: {e}. Attempting KML XML fallback parser.")

        # Method 2: Robust XML fallback parser for KML
        return cls._parse_kml_xml_fallback(kml_path, default_crs)

    @classmethod
    def _parse_kml_xml_fallback(cls, kml_path: Path, default_crs: str) -> ExtractedGeodata:
        """
        Direct KML XML parser extracting Placemarks with Point, LineString, and Polygon coordinates.
        """
        try:
            tree = ET.parse(kml_path)
            root = tree.getroot()
        except Exception as e:
            raise FileProcessingException(f"Invalid or corrupted KML XML file: {str(e)}")

        # Handle XML namespaces commonly used in KML (e.g. http://www.opengis.net/kml/2.2)
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        placemarks = root.findall(f".//{ns}Placemark")
        features: List[FeatureDetail] = []
        raw_geometries: List[BaseGeometry] = []

        for idx, pm in enumerate(placemarks):
            # Extract attributes/metadata
            props = {}
            name_elem = pm.find(f"{ns}name")
            desc_elem = pm.find(f"{ns}description")
            if name_elem is not None and name_elem.text:
                props["name"] = name_elem.text.strip()
            if desc_elem is not None and desc_elem.text:
                props["description"] = desc_elem.text.strip()

            # Check ExtendedData
            for data in pm.findall(f".//{ns}SimpleData"):
                data_name = data.get("name")
                if data_name and data.text:
                    props[data_name] = data.text.strip()
            for data in pm.findall(f".//{ns}Data"):
                data_name = data.get("name")
                val = data.find(f"{ns}value")
                if data_name and val is not None and val.text:
                    props[data_name] = val.text.strip()

            geom, geom_type = cls._extract_kml_geometry(pm, ns)
            geom_geojson = mapping(geom) if geom is not None else {}

            feature_detail = FeatureDetail(
                feature_id=idx,
                geometry_type=geom_type,
                geometry=geom_geojson,
                crs=default_crs,
                properties=props
            )
            features.append(feature_detail)
            raw_geometries.append(geom)

        return ExtractedGeodata(
            features=features,
            raw_geometries=raw_geometries,
            crs=default_crs,
            file_type="kml",
            feature_count=len(features)
        )

    @classmethod
    def _extract_kml_geometry(cls, pm: ET.Element, ns: str) -> Tuple[Optional[BaseGeometry], str]:
        """
        Extracts Polygon, LineString, or Point from a KML Placemark element.
        """
        from shapely.geometry import Point, LineString, Polygon

        # Polygon
        poly_elem = pm.find(f".//{ns}Polygon")
        if poly_elem is not None:
            coord_elem = poly_elem.find(f".//{ns}outerBoundaryIs//{ns}coordinates")
            if coord_elem is not None and coord_elem.text:
                coords = cls._parse_kml_coords(coord_elem.text)
                if len(coords) >= 3:
                    # Inner boundaries/holes if any
                    holes = []
                    for inner in poly_elem.findall(f".//{ns}innerBoundaryIs//{ns}coordinates"):
                        if inner.text:
                            inner_coords = cls._parse_kml_coords(inner.text)
                            if len(inner_coords) >= 3:
                                holes.append(inner_coords)
                    return Polygon(coords, holes), "Polygon"

        # LineString
        line_elem = pm.find(f".//{ns}LineString")
        if line_elem is not None:
            coord_elem = line_elem.find(f".//{ns}coordinates")
            if coord_elem is not None and coord_elem.text:
                coords = cls._parse_kml_coords(coord_elem.text)
                if len(coords) >= 2:
                    return LineString(coords), "LineString"

        # Point
        pt_elem = pm.find(f".//{ns}Point")
        if pt_elem is not None:
            coord_elem = pt_elem.find(f".//{ns}coordinates")
            if coord_elem is not None and coord_elem.text:
                coords = cls._parse_kml_coords(coord_elem.text)
                if coords:
                    return Point(coords[0]), "Point"

        return None, "Unknown"

    @staticmethod
    def _parse_kml_coords(coords_str: str) -> List[Tuple[float, float]]:
        """
        Parses KML coordinate string format: 'lon,lat,alt lon,lat,alt ...'
        """
        coords = []
        for token in coords_str.strip().split():
            parts = token.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coords.append((lon, lat))
                except ValueError:
                    continue
        return coords

    @staticmethod
    def _clean_property_value(val: Any) -> Any:
        """
        Converts non-serializable pandas/numpy types into native JSON types.
        """
        import numpy as np
        import pandas as pd

        if pd.isna(val):
            return None
        if isinstance(val, (np.integer, int)):
            return int(val)
        if isinstance(val, (np.floating, float)):
            return float(val)
        if isinstance(val, (np.bool_, bool)):
            return bool(val)
        return str(val)


def pd_concat(gdfs, ignore_index=True):
    import pandas as pd
    return pd.concat(gdfs, ignore_index=ignore_index)
