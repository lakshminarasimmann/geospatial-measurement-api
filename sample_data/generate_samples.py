import os
import zipfile
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point

OUTPUT_DIR = Path(__file__).resolve().parent
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_sample_shapefile_zip():
    """
    Creates a zip archive containing an ESRI Shapefile with Polygon and LineString features in EPSG:4326.
    """
    # 1. Polygon shapefile (Agricultural field parcels in Bangalore, India: Lat ~12.97, Lon ~77.59)
    poly1 = Polygon([
        (77.5900, 12.9700),
        (77.5950, 12.9700),
        (77.5950, 12.9750),
        (77.5900, 12.9750),
        (77.5900, 12.9700)
    ])
    poly2 = Polygon([
        (77.5800, 12.9650),
        (77.5850, 12.9650),
        (77.5830, 12.9690),
        (77.5800, 12.9650)
    ])

    gdf = gpd.GeoDataFrame(
        {
            "parcel_id": ["P-101", "P-102"],
            "land_use": ["Agriculture", "Solar Farm"],
            "owner": ["Aereo Farms", "GreenEnergy Ltd"]
        },
        geometry=[poly1, poly2],
        crs="EPSG:4326"
    )

    temp_shp = OUTPUT_DIR / "temp_parcels"
    os.makedirs(temp_shp, exist_ok=True)
    shp_path = temp_shp / "parcels.shp"
    gdf.to_file(shp_path)

    # Zip the shapefile parts (.shp, .shx, .dbf, .prj, .cpg)
    zip_path = OUTPUT_DIR / "sample_parcels.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in temp_shp.iterdir():
            zf.write(file, arcname=file.name)
            os.remove(file)
    os.rmdir(temp_shp)
    print(f"Created {zip_path}")


def create_sample_linestring_shapefile_zip():
    """
    Creates a zip archive containing LineString features (roads/pipelines).
    """
    line1 = LineString([(77.5900, 12.9700), (77.5950, 12.9750), (77.6000, 12.9800)])
    line2 = LineString([(77.5800, 12.9650), (77.5820, 12.9700), (77.5850, 12.9750)])

    gdf = gpd.GeoDataFrame(
        {
            "infra_id": ["INFRA-01", "INFRA-02"],
            "type": ["Pipeline", "Access Road"]
        },
        geometry=[line1, line2],
        crs="EPSG:4326"
    )

    temp_shp = OUTPUT_DIR / "temp_pipelines"
    os.makedirs(temp_shp, exist_ok=True)
    shp_path = temp_shp / "pipelines.shp"
    gdf.to_file(shp_path)

    zip_path = OUTPUT_DIR / "sample_pipelines.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in temp_shp.iterdir():
            zf.write(file, arcname=file.name)
            os.remove(file)
    os.rmdir(temp_shp)
    print(f"Created {zip_path}")


def create_sample_kml_files():
    """
    Creates standard KML files with Polygon, LineString, and Point features.
    """
    # 1. Survey Polygon KML
    polygon_kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Survey Cadastral Parcel</name>
    <Placemark>
      <name>Survey Zone Alpha</name>
      <description>Mining lease boundary</description>
      <Polygon>
        <extrude>1</extrude>
        <altitudeMode>clampToGround</altitudeMode>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5900,12.9700,0
              77.5950,12.9700,0
              77.5950,12.9750,0
              77.5900,12.9750,0
              77.5900,12.9700,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
    (OUTPUT_DIR / "sample_polygon.kml").write_text(polygon_kml, encoding="utf-8")
    print("Created sample_polygon.kml")

    # 2. Transmission Line KML (LineString)
    line_kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Transmission Line Survey</name>
    <Placemark>
      <name>Line 400kV Corridor</name>
      <description>High voltage transmission line segment</description>
      <LineString>
        <coordinates>
          77.5900,12.9700,0
          77.5950,12.9730,0
          77.6000,12.9780,0
          77.6050,12.9800,0
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
    (OUTPUT_DIR / "sample_transmission_line.kml").write_text(line_kml, encoding="utf-8")
    print("Created sample_transmission_line.kml")

    # 3. Mixed Features KML (Polygon + LineString + Point)
    mixed_kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Site Infrastructure Survey</name>
    <Placemark>
      <name>Warehouse Boundary</name>
      <description>Logistics depot boundary</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5920,12.9710,0
              77.5940,12.9710,0
              77.5940,12.9730,0
              77.5920,12.9730,0
              77.5920,12.9710,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>Haul Road A</name>
      <description>Heavy vehicle haul road</description>
      <LineString>
        <coordinates>
          77.5910,12.9705,0
          77.5925,12.9715,0
          77.5945,12.9725,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Control Tower Point</name>
      <description>Ground control beacon GCP-01</description>
      <Point>
        <coordinates>
          77.5930,12.9720,0
        </coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""
    (OUTPUT_DIR / "sample_mixed_site.kml").write_text(mixed_kml, encoding="utf-8")
    print("Created sample_mixed_site.kml")


if __name__ == "__main__":
    create_sample_shapefile_zip()
    create_sample_linestring_shapefile_zip()
    create_sample_kml_files()
    print("All sample datasets successfully generated.")
